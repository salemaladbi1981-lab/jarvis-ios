import Foundation
import AVFoundation

/// Real streaming audio output: enqueue 24kHz mono PCM16 buffers to speaker.
final class AudioPlayback {
    private let engine = AVAudioEngine()
    private let player = AVAudioPlayerNode()
    private let format: AVAudioFormat
    private var ready = false
    private var pendingBuffers = 0
    /// يُستدعى عند انتهاء تشغيل كل الـ buffers فعلياً (playback drained).
    var onPlaybackFinished: (() -> Void)?

    init() {
        format = AVAudioFormat(commonFormat: .pcmFormatInt16,
                               sampleRate: 24000, channels: 1, interleaved: true)!
    }

    func start() throws {
        #if os(iOS)
        let session = AVAudioSession.sharedInstance()
        // .default mode (بدل .voiceChat) — يمنع خفض الـ speaker gain.
        try session.setCategory(.playAndRecord, mode: .default,
                                options: [.allowBluetooth, .defaultToSpeaker])
        try session.setActive(true, options: [])
        #endif
        if !ready {
            engine.attach(player)
            engine.connect(player, to: engine.mainMixerNode, format: format)
            ready = true
        }
        player.volume = 1.0
        engine.mainMixerNode.outputVolume = 1.0
        engine.prepare()
        try engine.start()
        player.play()
    }

    /// Enqueue raw PCM16 bytes (24kHz mono) for immediate playback.
    var hasPendingBuffers: Bool { pendingBuffers > 0 }

    func enqueue(pcm16: Data) {
        guard ready, let buffer = Self.toBuffer(pcm16, format: format) else { return }
        pendingBuffers += 1
        player.scheduleBuffer(buffer) { [weak self] in
            guard let self else { return }
            self.pendingBuffers -= 1
            if self.pendingBuffers == 0 {
                self.onPlaybackFinished?()
            }
        }
    }

    func stop() {
        player.stop()
        engine.stop()
        #if os(iOS)
        // deactivation هنا فقط (full stop) — وليس في mic.pause.
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        #endif
    }

    private static func toBuffer(_ data: Data, format: AVAudioFormat) -> AVAudioPCMBuffer? {
        let frames = AVAudioFrameCount(data.count / MemoryLayout<Int16>.size)
        guard frames > 0, let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frames) else { return nil }
        buffer.frameLength = frames
        data.withUnsafeBytes { raw in
            guard let base = raw.bindMemory(to: Int16.self).baseAddress,
                  let dst = buffer.int16ChannelData?[0] else { return }
            dst.update(from: base, count: Int(frames))
        }
        return buffer
    }
}
