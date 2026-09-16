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
    private var guardState = SessionGuardState()   // حراسة الجلسة/الرد (currentResponseID + isSessionReady + pendingStatus)
    private var startAttemptID = 0
    private var pcmAppendCount = 0
    private var bargeStartTime: TimeInterval = 0

    func connect(baseURL: URL) async throws {
        eventPublisher.send(.connecting)
        guard var comps = URLComponents(url: baseURL, resolvingAgainstBaseURL: false) else {
            eventPublisher.send(.error("invalid_url")); return
        }
        comps.scheme = comps.scheme == "https" ? "wss" : "ws"
        comps.path = "/realtime"
        guard let url = comps.url else { eventPublisher.send(.error("invalid_url")); return }
        ws = session.webSocketTask(with: url)
        ws?.resume()
        trace("WS resume → \(url) (handshake pending — NOT connected yet)")
        receiveLoop()
    }

    func disconnect() {
        guardState.onStop()
        isSpeaking = false
        stopListening()
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
        audio.onPlaybackDrained = { [weak self] in
            guard let self else { return }
            self.trace("playback drained — اكتمل التشغيل المحلي")
            let status = self.guardState.pendingStatus
            self.guardState.pendingStatus = nil
            if status == "failed" {
                self.eventPublisher.send(.error("realtime_error"))
            } else {
                self.eventPublisher.send(.connected)
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
        guardState.onStop()   // إبطال الجلسة + الرد (منع أحداث الدورة الموقوفة)
        isSpeaking = false
        audio.stop()   // يوقف المحرك + يصفّر المستوى + يبطل generation
    }

    /// Barge-in: إلغاء الرد الجاري + مسح الـ playback (الـ mic يبقى شغّالاً).
    /// الـ flush يمسح الـ playback queue فقط — لا يمسح الـ mic input،
    /// فلا تضيع أول كلمة من كلام المستخدم.
    private func bargeIn() {
        guardState.onBarge()   // إبطال الرد فقط (الجلسة تبقى نشطة للـ listening)
        isSpeaking = false
        trace("BARGE speech_started → response.cancel + flush")
        let cancel = #"{"type":"response.cancel"}"#
        ws?.send(.string(cancel)) { _ in }
        audio.flush()
        let latency = Int((Date().timeIntervalSinceReferenceDate - bargeStartTime) * 1000)
        trace("BARGE playback stopped (latency=\(latency)ms)")
        eventPublisher.send(.interrupted)
    }

    func interrupt() {
        guardState.onBarge()
        isSpeaking = false
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
        // Gate: لا PCM قبل نجاح handshake/session.created
        guard guardState.isSessionReady else { return }
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

    private func receiveLoop() {
        ws?.receive { [weak self] result in
            guard let self else { return }
            switch result {
            case .success(let message):
                switch message {
                case .string(let text): self.handleServer(text)
                case .data(let data): self.handleAudio(data)
                @unknown default: break
                }
                self.receiveLoop()
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

    private func handleServer(_ text: String) {
        // Parse minimal JSON: extract type + transcript text.
        if let t = SessionEventParser.field(text, "type") {
            if t != "response.output_audio.delta" {
                trace("recv \(t)")
            }
            switch t {
            case "session.created":
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
                bargeStartTime = Date().timeIntervalSinceReferenceDate
                guardState.onBarge()   // إبطال الرد قبل التفرع (يشمل الفترة قبل أول delta)
                if isSpeaking {
                    // barge-in: كلام مستخدم أثناء كلام جارفس (AEC يمنع echo).
                    isSpeaking = false
                    bargeIn()   // response.cancel + flush
                } else {
                    // صوت متبقٍ بعد انتهاء التوليد (response.done) — إيقاف فوري للذيل
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
                // حراسة إلزامية: الهوية في response.id — يرفض عند nil أو عدم تطابق
                guard guardState.onDone(text) else {
                    trace("response.done ignored (لا رد مطابق نشط)")
                    break
                }
                let status = guardState.pendingStatus ?? "completed"
                isSpeaking = false
                audio.flushTail()   // يفلش tail + يطبع PLAYBACK counters
                trace("response.done status=\(status) — flushTail (انتظار اكتمال التشغيل المحلي)")
                // النتيجة تُرسل عند onPlaybackDrained (failed لا يتحول إلى success)
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
