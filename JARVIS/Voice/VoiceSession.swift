import Foundation
import Combine

/// Session state events that drive the seven UI states.
enum VoiceSessionEvent {
    case connecting
    case connected
    case listening
    case thinking
    case speaking
    case interrupted   // barge-in: Speaking → Listening
    case toolExecuting
    case awaitingApproval
    case error(String)
    case disconnected
}

/// Shared live-voice abstraction. Platform adapters (iOS/macOS) implement this.
protocol VoiceSession: AnyObject {
    var eventPublisher: PassthroughSubject<VoiceSessionEvent, Never> { get }
    func connect(baseURL: URL) async throws
    func disconnect()
    func startListening()
    func interrupt()          // barge-in
    func sendText(_ text: String)
}

/// Maps a live session event to the approved seven-state model.
enum JarvisStateMapper {
    static func state(for event: VoiceSessionEvent) -> JarvisState {
        switch event {
        case .connecting:      return .thinking
        case .connected:       return .idle
        case .listening:       return .listening
        case .thinking:        return .thinking
        case .speaking:        return .speaking
        case .interrupted:     return .listening
        case .toolExecuting:   return .executing
        case .awaitingApproval:return .approval
        case .error:           return .alert
        case .disconnected:    return .idle
        }
    }
}
