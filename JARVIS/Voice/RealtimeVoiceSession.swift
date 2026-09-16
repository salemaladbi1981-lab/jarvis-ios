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
    private var startAttemptID = 0
    private var pcmAppendCount = 0
    private var isSessionReady = false
    private var currentResponseID: String? = nil   // هوية الرد الحالي (لمنع stale deltas)
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
            self.eventPublisher.send(.connected)
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
        audio.stop()
    }

    /// Barge-in: إلغاء الرد الجاري + مسح الـ playback (الـ mic يبقى شغّالاً).
    /// الـ flush يمسح الـ playback queue فقط — لا يمسح الـ mic input،
    /// فلا تضيع أول كلمة من كلام المستخدم.
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
        guard isSessionReady else { return }
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
        if let t = Self.jsonStringField(text, "type") {
            if t != "response.output_audio.delta" {
                trace("recv \(t)")
            }
            switch t {
            case "session.created":
                trace("session.created received")
                isSessionReady = true
                eventPublisher.send(.connected)   // الآن فقط بعد نجاح handshake
            case "session.updated":
                trace("session.updated received")
            case "response.created":
                currentResponseID = Self.jsonNestedString(text, "response", "id")
                trace("response.created id=\(currentResponseID ?? "?")")
            case "response.output_audio.delta":
                if !isSpeaking {
                    isSpeaking = true
                    audio.beginSpeaking()   // يصفّر الـ counters ويبدأ التدفق
                }
                // هوية الرد: تجاهل delta من رد قديم (ملغى) حتى لو وصل بعد بدء رد جديد
                if let rid = Self.jsonStringField(text, "response_id"),
                   let cur = currentResponseID, rid != cur {
                    trace("stale delta ignored (response_id \(rid) != \(cur))")
                    break
                }
                if let b64 = Self.jsonStringField(text, "delta") {
                    if let data = Data(base64Encoded: b64) { audio.enqueueAudio(data) }
                }
                eventPublisher.send(.speaking)
            case "input_audio_buffer.speech_started":
                trace("VAD speech_started payload: \(text)")
                bargeStartTime = Date().timeIntervalSinceReferenceDate
                if isSpeaking {
                    // barge-in: كلام مستخدم أثناء كلام جارفس (AEC يمنع echo).
                    isSpeaking = false
                    bargeIn()   // response.cancel + flush
                } else {
                    // صوت متبقٍ بعد انتهاء التوليد (response.done) — إيقاف فوري للذيل
                    audio.flush()
                    trace("BARGE — flush tail (صوت متبقٍ بعد انتهاء التوليد)")
                }
            case "input_audio_buffer.speech_stopped":
                trace("VAD speech_stopped payload: \(text)")
            case "conversation.item.input_audio_transcription.completed":
                // نص المستخدم فقط — للتوجيه (tool routing). لا نوجّه نص الرد.
                if let txt = Self.transcriptText(text) {
                    trace("user_transcript: \(txt)")
                    onTranscript?(txt)
                }
            case "response.output_audio_transcript.done":
                // نص رد جارفس — لا يُعاد توجيهه (يمنع الـ loop).
                break
            case "response.done":
                isSpeaking = false
                audio.flushTail()   // يفلش tail + يطبع PLAYBACK counters
                trace("response.done — flushTail called (انتظار اكتمال التشغيل المحلي)")
                // لا .connected هنا — يُرسل عند onPlaybackDrained (اكتمال التشغيل الفعلي)
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

    private static func jsonStringField(_ text: String, _ key: String) -> String? {
        guard let data = text.data(using: .utf8),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return nil }
        return obj[key] as? String
    }

    /// استخراج حقل nested (مثل response.id من response.created).
    private static func jsonNestedString(_ text: String, _ key: String, _ subKey: String) -> String? {
        guard let data = text.data(using: .utf8),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let nested = obj[key] as? [String: Any] else { return nil }
        return nested[subKey] as? String
    }

    private static func transcriptText(_ text: String) -> String? {
        guard let data = text.data(using: .utf8),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return nil }
        // GA: transcript field مباشر
        if let t = obj["transcript"] as? String, !t.isEmpty { return t }
        // fallback: item.content
        if let item = obj["item"] as? [String: Any],
           let content = item["content"] as? [[String: Any]] {
            for c in content where c["type"] as? String == "input_text" || c["type"] as? String == "text" {
                if let t = c["text"] as? String, !t.isEmpty { return t }
            }
        }
        return nil
    }
}
