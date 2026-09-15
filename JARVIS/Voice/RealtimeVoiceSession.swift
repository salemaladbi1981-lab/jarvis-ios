import Foundation
import Combine

/// WebSocket-backed live voice session. Connects to the trusted control plane
/// (which proxies to OpenAI Realtime), never holding provider secrets itself.
final class RealtimeVoiceSession: NSObject, VoiceSession {
    let eventPublisher = PassthroughSubject<VoiceSessionEvent, Never>()
    private var ws: URLSessionWebSocketTask?
    private var session = URLSession(configuration: .default)

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
        ws?.cancel(with: .goingAway, reason: nil)
        ws = nil
        eventPublisher.send(.disconnected)
    }

    func startListening() {
        eventPublisher.send(.listening)
        // Mic capture feeds PCM16 chunks via sendAudio (platform adapter).
    }

    /// Barge-in: cancel the in-flight assistant response, stop output, → Listening.
    func interrupt() {
        let cancel = #"{"type":"response.cancel"}"#
        ws?.send(.string(cancel)) { _ in }
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
        // base64 PCM16 → input_audio_buffer.append
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
                case .string(let text):
                    self.handleServer(text)
                case .data(let data):
                    self.handleAudio(data)
                @unknown default: break
                }
                self.receiveLoop()
            case .failure:
                self.eventPublisher.send(.disconnected)
            }
        }
    }

    private func handleServer(_ text: String) {
        // Minimal parsing: response.audio.delta → speaking, response.done → idle,
        // function_call_arguments.done → executing / approval.
        if text.contains("response.audio.delta") { eventPublisher.send(.speaking) }
        else if text.contains("response.done") { eventPublisher.send(.connected) }
        else if text.contains("response.audio_transcript.done") { eventPublisher.send(.connected) }
        else if text.contains("function_call") { eventPublisher.send(.toolExecuting) }
    }

    private func handleAudio(_ data: Data) {
        // Platform adapter enqueues decoded audio for playback.
        eventPublisher.send(.speaking)
    }
}
