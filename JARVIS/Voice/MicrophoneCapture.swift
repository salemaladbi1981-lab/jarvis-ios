import Foundation
import AVFoundation

/// Real microphone capture: AVAudioEngine input tap → 24kHz mono PCM16.
/// Streams raw PCM16 to a callback (for realtime transport). No fake waveform.
final class MicrophoneCapture {
    private let engine = AVAudioEngine()
    private let targetFormat: AVAudioFormat
    var onPCM: ((Data) -> Void)?

    init() {
        targetFormat = AVAudioFormat(commonFormat: .pcmFormatInt16,
                                     sampleRate: 24000, channels: 1, interleaved: true)!
    }

    var isRunning: Bool { engine.isRunning }

    func start() throws {
        #if os(iOS)
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord, mode: .default,
                                options: [.allowBluetooth, .defaultToSpeaker])
        try session.setActive(true, options: [])
        #endif

        let input = engine.inputNode
        let hwFormat = input.outputFormat(forBus: 0)
        // تحديث converter إلى hw format الفعلي
        let conv = AVAudioConverter(from: hwFormat, to: targetFormat)!
        input.installTap(onBus: 0, bufferSize: 2048, format: hwFormat) { [weak self] buffer, _ in
            guard let self else { return }
            guard let converted = self.convert(buffer, using: conv) else { return }
            self.onPCM?(converted)
        }
        engine.prepare()
        try engine.start()
    }

    func stop() {
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        #if os(iOS)
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        #endif
    }

    private func convert(_ buffer: AVAudioPCMBuffer, using conv: AVAudioConverter) -> Data? {
        let ratio = targetFormat.sampleRate / buffer.format.sampleRate
        let capacity = AVAudioFrameCount(Double(buffer.frameLength) * ratio) + 32
        guard let out = AVAudioPCMBuffer(pcmFormat: targetFormat, frameCapacity: capacity) else { return nil }
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
}
