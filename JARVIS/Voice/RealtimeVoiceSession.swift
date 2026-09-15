import Foundation
import Combine

/// WebSocket-backed live voice session. Mic → backend proxy → OpenAI Realtime,
/// streamed audio out → playback. Holds no provider secrets.
final class RealtimeVoiceSession: NSObject, VoiceSession {
    static var backendBaseURL: String = "https://jarvis-api.qeyas.app"

    let eventPublisher = PassthroughSubject<VoiceSessionEvent, Never>()
    /// Final user transcript (e.g. "وش عندي اليوم؟") for local tool routing.
    var onTranscript: ((String) -> Void)?
    /// Tool-result text to speak back (calendar/reminders result).
    var onNeedSpokenResponse: (() -> Void)?

    private var ws: URLSessionWebSocketTask?
    private var session = URLSession(configuration: .default)
    private let mic = MicrophoneCapture()
    private let playback = AudioPlayback()
    private var micActive = false

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
        eventPublisher.send(.connected)
        receiveLoop()
    }

    func disconnect() {
        stopListening()
        ws?.cancel(with: .goingAway, reason: nil)
        ws = nil
        eventPublisher.send(.disconnected)
    }

    func startListening() {
        eventPublisher.send(.listening)
        mic.onPCM = { [weak self] data in self?.sendAudio(pcm16: data) }
        playback.onPlaybackFinished = { [weak self] in
            // لا نعيد الميكروفون إلا بعد انتهاء تشغيل الصوت فعلياً (لا echo).
            self?.resumeMic()
        }
        do {
            try mic.start()
            try playback.start()
            micActive = true
        } catch {
            eventPublisher.send(.error("mic_unavailable"))
        }
    }

    /// إيقاف الالتقاط أثناء رد النموذج (half-duplex) — يمنع echo/تداخل الـ turn.
    private func pauseMic() {
        guard micActive else { return }
        trace("pauseMic — mic.stop + commit")
        mic.stop()
        micActive = false
        // إغلاق الـ input buffer صراحة — لا مزيد من الـ audio يُعالج.
        commitInputBuffer()
    }

    private func commitInputBuffer() {
        let commit = #"{"type":"input_audio_buffer.commit"}"#
        ws?.send(.string(commit)) { _ in }
    }

    /// إعادة الاستماع بعد اكتمال الرد.
    private func resumeMic() {
        guard !micActive else { return }
        trace("resumeMic — mic.start")
        do {
            try mic.start()
            micActive = true
        } catch {
            eventPublisher.send(.error("mic_unavailable"))
        }
    }

    func stopListening() {
        mic.stop()
        playback.stop()
    }

    /// Barge-in: cancel in-flight assistant response, stop output, → Listening.
    func interrupt() {
        let cancel = #"{"type":"response.cancel"}"#
        ws?.send(.string(cancel)) { _ in }
        playback.stop()
        eventPublisher.send(.interrupted)
    }

    func sendText(_ text: String) {
        let item = #"{"type":"conversation.item.create","item":{"type":"message","role":"user","content":[{"type":"input_text","text":"\#(text)"}]}}"#
        ws?.send(.string(item)) { _ in }
        let resp = #"{"type":"response.create"}"#
        ws?.send(.string(resp)) { _ in }
        eventPublisher.send(.thinking)
    }

    func sendAudio(pcm16: Data) {
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
            case .failure:
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
            case "response.output_audio.delta":
                pauseMic()   // half-duplex: أوقف الالتقاط أثناء الرد
                if let b64 = Self.jsonStringField(text, "delta") {
                    if let data = Data(base64Encoded: b64) { playback.enqueue(pcm16: data) }
                }
                eventPublisher.send(.speaking)
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
                // لا نعيد الميكروفون إلا إذا انتهى الـ playback فعلياً
                // (وإلا نلتقط آخر صوت جارفس كـ echo → turn جديد).
                if !playback.hasPendingBuffers {
                    resumeMic()
                }
                eventPublisher.send(.connected)
            case "response.function_call_arguments.done":
                eventPublisher.send(.toolExecuting)
            case "error":
                eventPublisher.send(.error("realtime_error"))
            default: break
            }
        }
    }

    private func handleAudio(_ data: Data) {
        playback.enqueue(pcm16: data)
    }

    private static func jsonStringField(_ text: String, _ key: String) -> String? {
        guard let data = text.data(using: .utf8),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return nil }
        return obj[key] as? String
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
