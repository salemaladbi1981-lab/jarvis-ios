import Foundation
import AVFoundation

/// Microphone permission + audio session configuration (platform-safe).
/// Does NOT hard-code a single audio route.
enum MicPermission: Equatable {
    case notDetermined
    case granted
    case denied
}

#if os(iOS)
import UIKit
#endif

enum AudioCapture {
    static func micPermission() -> MicPermission {
        switch AVCaptureDevice.authorizationStatus(for: .audio) {
        case .authorized: return .granted
        case .denied: return .denied
        case .restricted: return .denied
        case .notDetermined: return .notDetermined
        @unknown default: return .denied
        }
    }

    static func requestMic() async -> MicPermission {
        await withCheckedContinuation { cont in
            AVCaptureDevice.requestAccess(for: .audio) { granted in
                cont.resume(returning: granted ? .granted : .denied)
            }
        }
    }

    /// Configure the audio session for voice conversation.
    /// Respects current route (Bluetooth/headset) — never hard-codes one.
    static func configureVoiceSession() throws {
        #if os(iOS)
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord, mode: .voiceChat,
                                options: [.allowBluetoothHFP, .allowBluetoothA2DP, .defaultToSpeaker])
        try session.setActive(true, options: [])
        #else
        // macOS: mic/output selection handled by the system; no AVAudioSession.
        #endif
    }

    static func deactivate() {
        #if os(iOS)
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        #endif
    }
}
