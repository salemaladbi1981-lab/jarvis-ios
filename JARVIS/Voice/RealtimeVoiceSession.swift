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
        do {
            try mic.start()
            try playback.start()
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
            switch t {
            case "response.audio.delta":
                if let b64 = Self.jsonStringField(text, "delta") {
                    if let data = Data(base64Encoded: b64) { handleAudio(data) }
                }
                eventPublisher.send(.speaking)
            case "conversation.item.input_audio_transcription.completed":
                if let txt = Self.transcriptText(text) { onTranscript?(txt) }
            case "response.done":
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
        eventPublisher.send(.speaking)
    }

    private static func jsonStringField(_ text: String, _ key: String) -> String? {
        guard let data = text.data(using: .utf8),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return nil }
        return obj[key] as? String
    }

    private static func transcriptText(_ text: String) -> String? {
        guard let data = text.data(using: .utf8),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let item = obj["item"] as? [String: Any],
              let content = item["content"] as? [[String: Any]] else { return nil }
        for c in content where c["type"] as? String == "input_text" || c["type"] as? String == "text" {
            if let t = c["text"] as? String, !t.isEmpty { return t }
        }
        return nil
    }
}
