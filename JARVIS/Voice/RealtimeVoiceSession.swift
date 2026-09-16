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
    private let audio = VoiceAudioEngine()
    private var isSpeaking = false

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
        audio.onPCM = { [weak self] data in self?.sendAudio(pcm16: data) }
        audio.onDiagnostics = { [weak self] msg in self?.trace("AEC diag: \(msg)") }
        do {
            try audio.start()
        } catch {
            eventPublisher.send(.error("mic_unavailable"))
        }
    }

    func stopListening() {
        audio.stop()
    }

    /// Barge-in: إلغاء الرد الجاري + مسح الـ playback (الـ mic يبقى شغّالاً).
    private func bargeIn() {
        trace("bargeIn — response.cancel + flush playback")
        let cancel = #"{"type":"response.cancel"}"#
        ws?.send(.string(cancel)) { _ in }
        audio.flush()
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
                if !isSpeaking {
                    isSpeaking = true
                    audio.beginSpeaking()   // يصفّر الـ counters ويبدأ التدفق
                }
                if let b64 = Self.jsonStringField(text, "delta") {
                    if let data = Data(base64Encoded: b64) { audio.enqueueAudio(data) }
                }
                eventPublisher.send(.speaking)
            case "input_audio_buffer.speech_started":
                // لا bargeIn تلقائي هنا — الـ echo (بدون AEC عبر inputNode) يسبب
                // false speech_started كان يقطع رد جارفس نفسه. الـ model native
                // interrupt_response هو المسؤول عن barge-in الحقيقي.
                trace("VAD speech_started payload: \(text)")
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
                trace("response.done — flushTail called")
                eventPublisher.send(.connected)
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
