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
    // Follow the negotiated server policy rather than requesting a second reply.
    private var serverCreatesResponses = false
    private var responseRequestPending = false
    private var responseDeferred = false
    private var guardState = SessionGuardState()   // حراسة الجلسة/الرد/الاتصال
    private var startAttemptID = 0
    private var pcmAppendCount = 0
    private var bargeStartTime: TimeInterval = 0
    /// هوية item الصوت الحالي (للـ conversation.item.truncate عند المقاطعة).
    private var currentOutputItemID: String?
    private var currentContentIndex = 0
    /// تنفيذ تسلسلي واحد لحالة الجلسة وحراسة أحداثها.
    private let stateQueue = DispatchQueue(label: "jarvis.session.state")

    func connect(baseURL: URL) async throws {
        eventPublisher.send(.connecting)
        guard var comps = URLComponents(url: baseURL, resolvingAgainstBaseURL: false) else {
            throw URLError(.badURL)
        }
        comps.scheme = comps.scheme == "https" ? "wss" : "ws"
        comps.path = "/realtime"
        guard let url = comps.url else { throw URLError(.badURL) }
        let token = JarvisConfig.injectedSessionToken ?? KeychainStore.load() ?? ""
        guard !token.isEmpty else { throw JarvisAPIError.authentication }
        var request = URLRequest(url: url)
        request.setValue(token, forHTTPHeaderField: "X-Jarvis-Session")
        request.setValue("PERSONAL", forHTTPHeaderField: "X-Jarvis-Workspace")
        // بدء اتصال جديد → جيل جديد يربط به الـ receiveLoop
        let gen = stateQueue.sync {
            self.serverCreatesResponses = false
            self.responseRequestPending = false
            self.responseDeferred = false
            return self.guardState.beginConnection()
        }
        stateQueue.sync {
            self.ws = self.session.webSocketTask(with: request)
            self.ws?.resume()
        }
        trace("WS resume → \(url) (handshake pending — NOT connected yet)")
        receiveLoop(gen: gen)
    }

    func disconnect() {
        stateQueue.sync {
            self.guardState.onStop()   // يبطل الجلسة/الرد + دورة الاتصال معاً
            self.isSpeaking = false
            self.responseRequestPending = false
            self.responseDeferred = false
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
                    self.isSpeaking = false
                    self.eventPublisher.send(.listening)
                    self.resumeDeferredResponse()
                case .failed:
                    self.trace("playback drained — اكتمل التشغيل (failed)")
                    self.isSpeaking = false
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
            self.responseRequestPending = false
            self.responseDeferred = false
        }
        audio.stop()   // يوقف المحرك + يصفّر المستوى + يبطل generation
        let socket = stateQueue.sync { let socket = self.ws; self.ws = nil; return socket }
        socket?.cancel(with: .goingAway, reason: nil)
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

    /// المقاطعة اليدوية (زر المايك) — الإلغاء الفوري الوحيد أثناء الكلام.
    /// كلام الغرفة/الخلفية لا يستدعي هذا أبداً (لا مقاطعة تلقائية من speech_started).
    func interrupt() {
        bargeStartTime = Date().timeIntervalSinceReferenceDate
        stateQueue.sync {
            self.guardState.onBarge()
            self.isSpeaking = false
            self.responseRequestPending = false
            self.responseDeferred = false
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

    /// Ask Realtime for the assistant response after transcript routing.
    /// Server VAD uses create_response=false so native device tools can consume
    /// Calendar/Reminder turns without a duplicate AI response.
    func requestResponse() {
        stateQueue.async { [weak self] in self?.requestResponseOnStateQueue() }
    }

    private func requestResponseOnStateQueue() {
        guard guardState.isSessionReady else {
            trace("response.create skipped — session not ready")
            return
        }
        guard !serverCreatesResponses else {
            trace("response.create skipped — server automatic response enabled")
            return
        }
        guard !responseRequestPending else {
            trace("response.create skipped — request already pending")
            return
        }
        guard guardState.currentResponseID == nil, !isSpeaking else {
            responseDeferred = true
            trace("response.create deferred until current playback completes")
            return
        }
        responseRequestPending = true
        let resp = #"{"type":"response.create"}"#
        ws?.send(.string(resp)) { [weak self] error in
            guard let self, let error else { return }
            self.stateQueue.async {
                self.responseRequestPending = false
                self.trace("response.create send failed: \(type(of: error))")
            }
        }
        eventPublisher.send(.thinking)
        trace("response.create sent after transcript routing")
    }

    private func resumeDeferredResponse() {
        guard responseDeferred else { return }
        responseDeferred = false
        requestResponseOnStateQueue()
    }

    private func updateResponsePolicy(_ text: String) {
        guard let data = text.data(using: .utf8),
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let configuration = object["session"] as? [String: Any] else { return }
        let audio = configuration["audio"] as? [String: Any]
        let input = audio?["input"] as? [String: Any]
        let detection = (input?["turn_detection"] as? [String: Any])
            ?? (configuration["turn_detection"] as? [String: Any])
        if let automatic = detection?["create_response"] as? Bool {
            serverCreatesResponses = automatic
            trace("negotiated create_response=\(automatic)")
        }
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
                    self.guardState.onStop()
                    self.isSpeaking = false
            self.responseRequestPending = false
            self.responseDeferred = false
                    self.ws?.cancel(with: .goingAway, reason: nil)
                    self.ws = nil
                    self.audio.stop()
                    self.eventPublisher.send(.error("connection_lost"))
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
                updateResponsePolicy(text)
                // handshake نجح والجلسة جاهزة → نبقى في وضع الاستماع (المايك مفتوح بانتظار المستخدم).
                // كان .connected → idle يُطفئ مؤشر المايك بعد جزء من الثانية من فتحه.
                eventPublisher.send(.listening)
            case "session.updated":
                trace("session.updated received")
                updateResponsePolicy(text)
            case "response.created":
                responseRequestPending = false
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
                let responseAlreadyHasAudio = guardState.currentResponseHasAudio
                guard guardState.onDelta(text) else {
                    trace("delta ignored (لا جلسة نشطة أو رد مطابق)")
                    break
                }
                if !responseAlreadyHasAudio {
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
                    // لا مقاطعة تلقائية أثناء الكلام — كلام الغرفة/الخلفية لا يُلغي الرد.
                    // المقاطعة يدوية فقط عبر interrupt() (زر المايك).
                    trace("speech_started while speaking → ignored (manual interruption only)")
                } else {
                    // VAD is an observation, never permission to discard playback.
                    eventPublisher.send(.listening)
                    trace("VAD — Listening (playback preserved)")
                }
            case "input_audio_buffer.speech_stopped":
                trace("VAD speech_stopped payload: \(text)")
                // لا مقاطعة تلقائية — الحدث يُسجَّل فقط (الكلام انتهى).
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
                    // Generation ended; the speaker may still have queued audio.
                    // Only the matching local drain callback clears isSpeaking.
                    audio.flushTail()   // يفلش tail + يطبع PLAYBACK counters
                    trace("response.done cycle=\(cycle) — flushTail (انتظار اكتمال التشغيل المحلي)")
                case .publishImmediately(let completion):
                    // رد بلا صوت (لا delta): انشر النتيجة فوراً — لا انتظار drain ولا تأثير لإشعار قديم.
                    isSpeaking = false
                    trace("response.done — لا صوت، نشر فوري")
                    emitCompletion(completion)
                    resumeDeferredResponse()
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
                let code = SessionEventParser.nested(text, "error", "code") ?? "unknown"
                trace("realtime error code=\(code)")
                if code == "conversation_already_has_active_response"
                    || code == "response_cancel_not_active" {
                    // These races do not invalidate the live session or microphone.
                    responseRequestPending = false
                    trace("recoverable response race — keeping voice session open")
                    break
                }
                eventPublisher.send(.error("realtime_error"))
            default: break
            }
        }
    }

    private func handleAudio(_ data: Data) {
        audio.enqueueAudio(data)
    }

}
