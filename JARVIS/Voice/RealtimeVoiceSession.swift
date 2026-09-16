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

    private var ws: URLSessionWebSocketTask?
    private var session = URLSession(configuration: .default)
    private let audio = VoiceAudioEngine()
    private var isSpeaking = false
    private var guardState = SessionGuardState()   // حراسة الجلسة/الرد/الاتصال
    private var startAttemptID = 0
    private var pcmAppendCount = 0
    private var bargeStartTime: TimeInterval = 0
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
        trace("BARGE speech_started → response.cancel + flush")
        let cancel = #"{"type":"response.cancel"}"#
        ws?.send(.string(cancel)) { _ in }
        audio.flush()
        let latency = Int((Date().timeIntervalSinceReferenceDate - bargeStartTime) * 1000)
        trace("BARGE playback stopped (latency=\(latency)ms)")
        eventPublisher.send(.interrupted)
    }

    func interrupt() {
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
                if guardState.onResponseCreated(text) {
                    trace("response.created id=\(guardState.currentResponseID ?? "?")")
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
                bargeStartTime = Date().timeIntervalSinceReferenceDate
                if isSpeaking {
                    isSpeaking = false
                    bargeIn()   // response.cancel + flush
                } else {
                    audio.flush()
                    eventPublisher.send(.listening)   // انتقال الواجهة إلى Listening
                    trace("BARGE — flush tail → Listening")
                }
            case "input_audio_buffer.speech_stopped":
                trace("VAD speech_stopped payload: \(text)")
            case "conversation.item.input_audio_transcription.completed":
                // نص المستخدم فقط — للتوجيه (tool routing). لا نوجّه نص الرد.
                if let txt = SessionEventParser.transcript(text) {
                    trace("user_transcript: \(txt)")
                    onTranscript?(txt)
                }
            case "response.output_audio_transcript.done":
                // نص رد جارفس — لا يُعاد توجيهه (يمنع الـ loop).
                break
            case "response.done":
                // هوية دورة التشغيل من المحرك (وليست هوية الرد الحالي عند وصول الـ callback).
                let cycle = audio.currentGeneration
                // حراسة إلزامية: الهوية في response.id — يرفض عند nil أو عدم تطابق
                guard guardState.onDone(text, cycle: cycle) else {
                    trace("response.done ignored (لا رد مطابق نشط)")
                    break
                }
                isSpeaking = false
                audio.flushTail()   // يفلش tail + يطبع PLAYBACK counters
                trace("response.done cycle=\(cycle) — flushTail (انتظار اكتمال التشغيل المحلي)")
                // النتيجة تُرسل عند onPlaybackDrained المطابق لنفس الدورة (failed لا يتحول success)
            case "response.function_call_arguments.done":
                eventPublisher.send(.toolExecuting)
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
