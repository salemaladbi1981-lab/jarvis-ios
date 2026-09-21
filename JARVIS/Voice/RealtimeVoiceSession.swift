import Foundation
import Combine

/// WebSocket-backed live voice session. Mic → backend proxy → OpenAI Realtime,
/// streamed audio out → playback. Holds no provider secrets.
final class RealtimeVoiceSession: NSObject, VoiceSession {
    static var backendBaseURL: String = "https://jarvis-api.qeyas.app"

    let eventPublisher = PassthroughSubject<VoiceSessionEvent, Never>()
    /// Final user transcript (e.g. "وش عندي اليوم؟") for local tool routing.
    var onTranscript: ((String) -> Void)?
    // V1 Visual: read-only level forwarding (من VoiceAudioEngine hooks)
    var onMicLevel: ((Double) -> Void)?
    var onOutputLevel: ((Double) -> Void)?
    /// Tool-result text to speak back (calendar/reminders result).
    var onNeedSpokenResponse: (() -> Void)?
    /// Playback handoff: يفتح فيديو في تطبيق YouTube الرسمي (url, title) من السيرفر.
    var onPlaybackHandoff: ((String, String) -> Void)?
    /// Navigation handoff: يفتح تطبيق الخرائط (Google Maps) على وجهة (url).
    var onNavigationHandoff: ((String) -> Void)?
    /// Agent runtime lifecycle from backend: phase, agent_id, from_agent.
    var onAgentRuntime: ((String, String, String?) -> Void)?

    private var ws: URLSessionWebSocketTask?
    private var session = URLSession(configuration: .default)
    private let audio = VoiceAudioEngine()
    private var isSpeaking = false
    private var guardState = SessionGuardState()   // حراسة الجلسة/الرد/الاتصال
    private var startAttemptID = 0
    private var pcmAppendCount = 0
    private var bargeStartTime: TimeInterval = 0
    /// Voice barge-in confirmation: semantic VAD must remain active briefly before
    /// cancelling playback. This restores natural interruption while filtering clicks/echo.
    private var pendingBargeWorkItem: DispatchWorkItem?
    private let bargeConfirmDelay: TimeInterval = 0.22
    /// هوية item الصوت الحالي (للـ conversation.item.truncate عند المقاطعة).
    private var currentOutputItemID: String?
    private var currentContentIndex = 0
    /// تنفيذ تسلسلي واحد لحالة الجلسة وحراسة أحداثها.
    private let stateQueue = DispatchQueue(label: "jarvis.session.state")

    func connect(baseURL: URL) async throws {
        eventPublisher.send(.connecting)
        guard var comps = URLComponents(url: baseURL, resolvingAgainstBaseURL: false) else {
            eventPublisher.send(.error("invalid_url")); return
        }
        comps.scheme = comps.scheme == "https" ? "wss" : "ws"
        comps.path = "/realtime"
        guard let url = comps.url else { eventPublisher.send(.error("invalid_url")); return }
        // بدء اتصال جديد → جيل جديد يربط به الـ receiveLoop
        let gen = stateQueue.sync { self.guardState.beginConnection() }
        stateQueue.sync {
            self.ws = self.session.webSocketTask(with: url)
            self.ws?.resume()
        }
        trace("WS resume → \(url) (handshake pending — NOT connected yet)")
        receiveLoop(gen: gen)
    }

    func disconnect() {
        stateQueue.sync {
            self.guardState.onStop()   // يبطل الجلسة/الرد + دورة الاتصال معاً
            self.isSpeaking = false
        }
        audio.stop()
        ws?.cancel(with: .goingAway, reason: nil)
        ws = nil
        eventPublisher.send(.disconnected)
    }

    func startListening() {
        startAttemptID += 1
        let attempt = startAttemptID
        eventPublisher.send(.listening)
        trace("startListening attempt #\(attempt) — voiceState=listening")
        audio.onPCM = { [weak self] data in self?.sendAudio(pcm16: data) }
        audio.onDiagnostics = { [weak self] msg in self?.trace("AEC diag: \(msg)") }
        audio.onMicLevel = { [weak self] level in self?.onMicLevel?(level) }
        audio.onOutputLevel = { [weak self] level in self?.onOutputLevel?(level) }
        audio.onPlaybackDrained = { [weak self] cycle in
            guard let self else { return }
            // إشعار انتهاء التشغيل: يطابق هوية دورة التشغيل قبل استهلاك النتيجة.
            self.stateQueue.async {
                switch self.guardState.consumeCompletion(cycle: cycle) {
                case .none:
                    self.trace("playback drained — لا اكتمال مطابق (إشعار قديم cycle=\(cycle))")
                case .success:
                    self.trace("playback drained — اكتمل التشغيل المحلي")
                    self.eventPublisher.send(.connected)
                case .failed:
                    self.trace("playback drained — اكتمل التشغيل (failed)")
                    self.eventPublisher.send(.error("realtime_error"))
                }
            }
        }
        do {
            try audio.start()
            trace("startListening #\(attempt): audio.start OK")
        } catch {
            trace("startListening #\(attempt) FAILED: \(error.localizedDescription)")
            eventPublisher.send(.error("mic_unavailable"))
        }
    }

    func stopListening() {
        stateQueue.sync {
            self.guardState.onStop()   // إبطال الجلسة + الرد (منع أحداث الدورة الموقوفة)
            self.isSpeaking = false
        }
        audio.stop()   // يوقف المحرك + يصفّر المستوى + يبطل generation
    }

    /// Barge-in: إلغاء الرد الجاري + مسح الـ playback (الـ mic يبقى شغّالاً).
    /// (لا يغيّر الحالة — المتصلون يبطلون الرد عبر onBarge قبل النداء).
    private func bargeIn() {
        trace("BARGE manual interrupt → response.cancel + truncate + flush")
        let cancel = #"{"type":"response.cancel"}"#
        ws?.send(.string(cancel)) { _ in }
        // قطع الجزء غير المسموع من item الصوت الحالي (item_id + content_index + مدة الصوت المشغّل فعلاً)
        if let itemID = currentOutputItemID {
            let playedMs = audio.playedDurationMs
            let truncate = #"{"type":"conversation.item.truncate","item_id":"\#(itemID)","content_index":\#(currentContentIndex),"audio_end_ms":\#(playedMs)}"#
            ws?.send(.string(truncate)) { _ in }
            trace("BARGE truncate item_id=\(itemID) content_index=\(currentContentIndex) audio_end_ms=\(playedMs)")
        }
        audio.flush()
        let latency = Int((Date().timeIntervalSinceReferenceDate - bargeStartTime) * 1000)
        trace("BARGE playback stopped (latency=\(latency)ms)")
        eventPublisher.send(.interrupted)
    }

    private func scheduleConfirmedVoiceBargeIn() {
        pendingBargeWorkItem?.cancel()
        let work = DispatchWorkItem { [weak self] in
            guard let self else { return }
            self.stateQueue.async {
                guard self.isSpeaking else { return }
                self.trace("BARGE confirmed voice interruption")
                self.bargeStartTime = Date().timeIntervalSinceReferenceDate
                self.guardState.onBarge()
                self.isSpeaking = false
                self.bargeIn()
            }
        }
        pendingBargeWorkItem = work
        DispatchQueue.global(qos: .userInitiated).asyncAfter(deadline: .now() + bargeConfirmDelay, execute: work)
    }

    private func cancelPendingVoiceBargeIn() {
        pendingBargeWorkItem?.cancel()
        pendingBargeWorkItem = nil
    }

    /// Manual mic-button interruption remains immediate; spoken interruption is confirmed
    /// separately through semantic VAD to avoid room-noise false positives.
    func interrupt() {
        bargeStartTime = Date().timeIntervalSinceReferenceDate
        stateQueue.sync {
            self.guardState.onBarge()
            self.isSpeaking = false
        }
        bargeIn()
    }

    func sendText(_ text: String) {
        let item = #"{"type":"conversation.item.create","item":{"type":"message","role":"user","content":[{"type":"input_text","text":"\#(text)"}]}}"#
        ws?.send(.string(item)) { _ in }
        let resp = #"{"type":"response.create"}"#
        ws?.send(.string(resp)) { _ in }
        eventPublisher.send(.thinking)
    }

    /// Replace any speculative model answer with authoritative on-device data
    /// (e.g. EventKit calendar/reminders), then ask Realtime to speak only from that result.
    func sendGroundedDeviceResult(userRequest: String, result: String) {
        let payload = "Authoritative device result for my previous request. Use ONLY this result; do not claim lack of access and do not invent anything. Request: \(userRequest)\nResult: \(result)"
        let escaped = payload
            .replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "\"", with: "\\\"")
            .replacingOccurrences(of: "\n", with: "\\n")

        stateQueue.sync {
            if self.guardState.currentResponseID != nil || self.isSpeaking {
                self.guardState.onBarge()
                self.isSpeaking = false
                let cancel = #"{"type":"response.cancel"}"#
                self.ws?.send(.string(cancel)) { _ in }
                self.audio.flush()
            }
        }

        let item = #"{"type":"conversation.item.create","item":{"type":"message","role":"user","content":[{"type":"input_text","text":"\#(escaped)"}]}}"#
        ws?.send(.string(item)) { _ in }
        ws?.send(.string(#"{"type":"response.create"}"#)) { _ in }
        eventPublisher.send(.thinking)
        trace("device grounding injected")
    }

    func sendAudio(pcm16: Data) {
        // Gate: لا PCM قبل نجاح handshake/session.created (تحت التسلسل نفسه)
        let ready = stateQueue.sync { self.guardState.isSessionReady }
        guard ready else { return }
        pcmAppendCount += 1
        if pcmAppendCount == 1 {
            trace("PCM append #1 bytes=\(pcm16.count)")
        }
        let b64 = pcm16.base64EncodedString()
        let msg = #"{"type":"input_audio_buffer.append","audio":"\#(b64)"}"#
        ws?.send(.string(msg)) { _ in }
    }

    private func trace(_ msg: String) {
        let ts = Date().timeIntervalSinceReferenceDate
        print("[JARVIS-TRACE] \(String(format: "%.3f", ts)) \(msg)")
    }

    private func receiveLoop(gen: Int) {
        ws?.receive { [weak self] result in
            guard let self else { return }
            self.stateQueue.async {
                // حراسة: callback من اتصال قديم لا يُعالج ولا يُستأنف
                guard self.guardState.isValidConnection(gen) else {
                    self.trace("receiveLoop تجاهل — اتصال قديم (gen=\(gen))")
                    return
                }
                switch result {
                case .success(let message):
                    switch message {
                    case .string(let text): self.handleServer(text)
                    case .data(let data): self.handleAudio(data)
                    @unknown default: break
                    }
                    self.receiveLoop(gen: gen)
                case .failure(let error):
                    self.trace("WS receive FAILED: \(error.localizedDescription)")
                    if let nserr = error as NSError? {
                        let reason = nserr.userInfo["NSURLErrorWebSocketHandshakeFailureReason"] ?? "?"
                        self.trace("WS handshake failure: code=\(nserr.code) reason=\(reason)")
                    }
                    self.eventPublisher.send(.disconnected)
                }
            }
        }
    }

    private func emitCompletion(_ completion: PlaybackCompletion) {
        switch completion {
        case .none:
            break
        case .success:
            eventPublisher.send(.connected)
        case .failed:
            eventPublisher.send(.error("realtime_error"))
        }
    }

    private func handleServer(_ text: String) {
        if let t = SessionEventParser.field(text, "type") {
            if t != "response.output_audio.delta" {
                trace("recv \(t)")
            }
            switch t {
            case "session.created":
                // حدث بدء الجلسة — لا يشترط isSessionReady؛ الـ receiveLoop يتحقق من جيل الاتصال.
                trace("session.created received")
                guardState.sessionCreated()
                eventPublisher.send(.connected)   // الآن فقط بعد نجاح handshake
            case "session.updated":
                trace("session.updated received")
            case "response.created":
                currentOutputItemID = nil   // رد جديد — لا item صوتي بعد
                currentContentIndex = 0
                if guardState.onResponseCreated(text) {
                    trace("response.created id=\(guardState.currentResponseID ?? "?")")
                    eventPublisher.send(.thinking)   // V1 Visual: model بدأ يولد الرد
                } else {
                    trace("response.created ignored (لا جلسة نشطة)")
                }
            case "response.output_audio.delta":
                // حراسة الجلسة + هوية الرد أولاً (قبل أي تغيير isSpeaking/beginSpeaking/حدث)
                guard guardState.onDelta(text) else {
                    trace("delta ignored (لا جلسة نشطة أو رد مطابق)")
                    break
                }
                if !isSpeaking {
                    isSpeaking = true
                    audio.beginSpeaking()   // يصفّر الـ counters ويبدأ التدفق
                }
                if let b64 = SessionEventParser.field(text, "delta") {
                    if let data = Data(base64Encoded: b64) { audio.enqueueAudio(data) }
                }
                eventPublisher.send(.speaking)
            case "input_audio_buffer.speech_started":
                trace("VAD speech_started payload: \(text)")
                // حراسة: حدث متأخر بعد الإيقاف يجب ألا يعيد .listening أو يفلش دورة موقوفة
                guard guardState.onSpeechStarted() else {
                    trace("speech_started ignored (الجلسة موقوفة)")
                    break
                }
                if isSpeaking {
                    trace("speech_started while speaking → confirm voice barge-in")
                    scheduleConfirmedVoiceBargeIn()
                } else {
                    audio.flush()
                    eventPublisher.send(.listening)   // انتقال الواجهة إلى Listening
                    trace("VAD — flush tail → Listening")
                }
            case "input_audio_buffer.speech_stopped":
                trace("VAD speech_stopped payload: \(text)")
                // Short speech/noise before the confirmation window must not cancel JARVIS.
                cancelPendingVoiceBargeIn()
            case "conversation.item.input_audio_transcription.completed":
                // نص المستخدم فقط — للتوجيه (tool routing). لا نوجّه نص الرد.
                if let txt = SessionEventParser.transcript(text) {
                    trace("user_transcript: \(txt)")
                    onTranscript?(txt)
                }
            case "response.output_audio_transcript.done":
                // نص رد جارفس — لا يُعاد توجيهه (يمنع الـ loop).
                break
            case "response.output_item.done":
                // تتبع هوية item الصوت الحالي للـ conversation.item.truncate عند المقاطعة.
                if let iid = SessionEventParser.nested(text, "item", "id") {
                    currentOutputItemID = iid
                }
                if let ci = SessionEventParser.fieldInt(text, "content_index") {
                    currentContentIndex = ci
                }
                break
            case "response.done":
                // الرد انتهى.
                // هوية دورة التشغيل من المحرك (وليست هوية الرد الحالي عند وصول الـ callback).
                let cycle = audio.currentGeneration
                // قرار الإنهاء حسب وجود صوت للرد (stale/بصوت/بلا صوت).
                switch guardState.resolveDone(text, cycle: cycle) {
                case .ignore:
                    trace("response.done ignored (لا رد مطابق نشط)")
                case .waitForDrain:
                    isSpeaking = false
                    audio.flushTail()   // يفلش tail + يطبع PLAYBACK counters
                    trace("response.done cycle=\(cycle) — flushTail (انتظار اكتمال التشغيل المحلي)")
                case .publishImmediately(let completion):
                    // رد بلا صوت (لا delta): انشر النتيجة فوراً — لا انتظار drain ولا تأثير لإشعار قديم.
                    isSpeaking = false
                    trace("response.done — لا صوت، نشر فوري")
                    emitCompletion(completion)
                }
            case "response.function_call_arguments.done":
                eventPublisher.send(.toolExecuting)
            case "agent_runtime":
                let phase = SessionEventParser.field(text, "phase") ?? ""
                let agentID = SessionEventParser.field(text, "agent_id") ?? ""
                let fromAgent = SessionEventParser.field(text, "from_agent")
                guard !phase.isEmpty, !agentID.isEmpty else {
                    trace("agent_runtime missing phase/agent_id")
                    break
                }
                trace("agent_runtime phase=\(phase) agent=\(agentID) from=\(fromAgent ?? "-")")
                onAgentRuntime?(phase, agentID, fromAgent)
            case "playback_handoff":
                // فتح الفيديو في تطبيق YouTube الرسمي (من أداة youtube_play).
                let url = SessionEventParser.field(text, "play_url") ?? ""
                let title = SessionEventParser.field(text, "title") ?? ""
                guard !url.isEmpty else {
                    trace("playback_handoff بلا play_url — تجاهل")
                    break
                }
                trace("playback_handoff -> \(url)")
                onPlaybackHandoff?(url, title)
            case "navigation_handoff":
                // فتح تطبيق الخرائط (Google Maps) على الوجهة (من أداة maps_navigate).
                let navUrl = SessionEventParser.field(text, "maps_url") ?? ""
                guard !navUrl.isEmpty else {
                    trace("navigation_handoff بلا maps_url — تجاهل")
                    break
                }
                trace("navigation_handoff -> \(navUrl)")
                onNavigationHandoff?(navUrl)
            case "error":
                // تسجيل الـ error code/message كاملاً (كان مخفياً).
                trace("recv error payload: \(text)")
                eventPublisher.send(.error("realtime_error"))
            default: break
            }
        }
    }

    private func handleAudio(_ data: Data) {
        audio.enqueueAudio(data)
    }

}
