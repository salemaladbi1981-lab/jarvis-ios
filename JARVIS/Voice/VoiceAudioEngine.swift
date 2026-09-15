import Foundation
import AVFoundation

/// Shared full-duplex audio I/O: ONE AVAudioEngine + ONE AVAudioSession.
/// Voice-processing (.voiceChat) mode → native AEC (speaker echo removed from mic).
/// Coalescing playback buffer (jitter/underrun fix). flush() for barge-in.
final class VoiceAudioEngine {
    private let engine = AVAudioEngine()
    private let player = AVAudioPlayerNode()
    private let format: AVAudioFormat   // 24kHz mono PCM16
    private var started = false
    private var converter: AVAudioConverter?

    // Mic tap (AEC-applied via voice-processing session)
    var onPCM: ((Data) -> Void)?
    var onDiagnostics: ((String) -> Void)?

    // Playback coalescing
    private var queue: [Data] = []
    private var isPlaying = false
    private let targetBufferBytes = 24000 * 2 / 10   // ~100ms @24kHz 16-bit mono
    var onPlaybackDrained: (() -> Void)?
    var onUnderrun: ((Int) -> Void)?                 // gap frames measured

    init() {
        format = AVAudioFormat(commonFormat: .pcmFormatInt16,
                               sampleRate: 24000, channels: 1, interleaved: true)!
    }

    func start() throws {
        guard !started else { return }
        #if os(iOS)
        let session = AVAudioSession.sharedInstance()
        // Voice-processing mode (AEC عبر VPIO داخل AVAudioEngine).
        try session.setCategory(.playAndRecord, mode: .voiceChat,
                                options: [.allowBluetooth, .defaultToSpeaker])
        try session.setActive(true, options: [])
        #endif

        // Output graph
        engine.attach(player)
        engine.connect(player, to: engine.mainMixerNode, format: format)
        player.volume = 1.0
        engine.mainMixerNode.outputVolume = 1.0

        // AEC: فعّل voice processing على الـ I/O node قبل start (Apple official path)
        try engine.inputNode.setVoiceProcessingEnabled(true)

        // Input tap (AEC-applied)
        let input = engine.inputNode
        let hwFormat = input.outputFormat(forBus: 0)
        converter = AVAudioConverter(from: hwFormat, to: format)!
        input.installTap(onBus: 0, bufferSize: 2048, format: hwFormat) { [weak self] buffer, _ in
            guard let self, let conv = self.converter else { return }
            if let data = self.convert(buffer, using: conv) {
                self.onPCM?(data)
            }
        }

        engine.prepare()
        try engine.start()
        player.play()
        started = true

        #if os(iOS)
        let vpEnabled = engine.inputNode.isVoiceProcessingEnabled
        let vpBypassed = engine.inputNode.isVoiceProcessingBypassed
        let route = session.currentRoute.outputs.first?.portType.rawValue ?? "?"
        let sessionMode = session.mode.rawValue
        onDiagnostics?("AEC vpEnabled=\(vpEnabled) vpBypassed=\(vpBypassed) mode=\(sessionMode) route=\(route) hwRate=\(Int(hwFormat.sampleRate))")
        #endif
    }

    /// Enqueue PCM16 (24kHz mono). Coalesces small deltas into ~100ms buffers.
    func enqueueAudio(_ data: Data) {
        queue.append(data)
        drainQueue(force: false)
    }

    /// يُستدعى عند نهاية الرد — يفلش tail buffer المتبقي (<100ms) فوراً.
    func flushTail() {
        drainQueue(force: true)
    }

    private func drainQueue(force: Bool) {
        guard !isPlaying, !queue.isEmpty else { return }
        var collected = Data()
        while !queue.isEmpty && (force || collected.count < targetBufferBytes) {
            collected.append(queue.removeFirst())
        }
        guard !collected.isEmpty, let buffer = Self.toBuffer(collected, format: format) else {
            isPlaying = false
            return
        }
        isPlaying = true
        player.scheduleBuffer(buffer) { [weak self] in
            guard let self else { return }
            self.isPlaying = false
            self.drainQueue(force: false)
            if self.queue.isEmpty {
                self.onPlaybackDrained?()
            }
        }
    }

    /// Barge-in: مسح فوري لكل الـ audio المعلق + إيقاف الرد القديم.
    func flush() {
        player.stop()
        player.reset()
        queue.removeAll()
        isPlaying = false
        player.play()
    }

    func stop() {
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        started = false
        #if os(iOS)
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        #endif
    }

    // MARK: - PCM conversion

    private func convert(_ buffer: AVAudioPCMBuffer, using conv: AVAudioConverter) -> Data? {
        let ratio = format.sampleRate / buffer.format.sampleRate
        let capacity = AVAudioFrameCount(Double(buffer.frameLength) * ratio) + 32
        guard let out = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: capacity) else { return nil }
        var fed = false
        var error: NSError?
        let status = conv.convert(to: out, error: &error) { _, outStatus in
            if fed { outStatus.pointee = .noDataNow; return nil }
            fed = true
            outStatus.pointee = .haveData
            return buffer
        }
        guard status != .error, error == nil, let channelData = out.int16ChannelData else { return nil }
        let frames = Int(out.frameLength)
        let bytes = UnsafeBufferPointer(start: channelData[0], count: frames)
        return Data(bytes: bytes.baseAddress!, count: frames * MemoryLayout<Int16>.size)
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
