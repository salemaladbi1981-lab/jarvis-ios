import Foundation
import AVFoundation

/// Shared full-duplex audio I/O: ONE AVAudioEngine + ONE AVAudioSession.
/// Voice-processing (.voiceChat) mode → native AEC (speaker echo removed from mic).
/// Continuous schedule-ahead playback + full runtime counters + serial queue (thread-safe).
final class VoiceAudioEngine {
    private let engine = AVAudioEngine()
    private let player = AVAudioPlayerNode()
    private let format: AVAudioFormat   // 24kHz mono PCM16
    private var started = false
    private var converter: AVAudioConverter?

    // Mic tap (AEC-applied via voice-processing session)
    var onPCM: ((Data) -> Void)?
    var onDiagnostics: ((String) -> Void)?
    var onPlaybackDrained: (() -> Void)?

    // V1 Visual: read-only RMS level hooks (normalized 0..1).
    // لا تغيّر أي سلوك — تُحسب من الـ PCM المتدفق وتُنشر للـ Visual layer فقط.
    var onMicLevel: ((Double) -> Void)?
    var onOutputLevel: ((Double) -> Void)?

    // Mic capture counters (post-engine-startup evidence)
    private(set) var pcmCallbacks = 0
    private(set) var pcmBytesTotal = 0

    // Serial queue: يحمي pendingData + counters من data race
    // (enqueue من WebSocket thread، completion من audio thread).
    private let workQueue = DispatchQueue(label: "jarvis.audio.playback")

    // Playback: coalescing + schedule-ahead (continuous, no serial gap)
    private var pendingData: [Data] = []
    private var scheduledBuffers = 0
    private let targetBufferBytes = 4800        // ~100ms @24kHz 16-bit mono
    private let maxScheduledAhead = 3           // keep up to 3 buffers queued in the player
    private var isSpeaking = false              // response audio still streaming

    // Runtime counters (PROVEN, not assumed)
    private(set) var receivedBytes = 0
    private(set) var scheduledBytes = 0
    private(set) var completedBuffers = 0
    private(set) var peakQueueDepth = 0
    private(set) var underruns = 0
    private(set) var tailBytesFlushed = 0
    private(set) var converterErrors = 0
    private(set) var scheduleErrors = 0

    init() {
        format = AVAudioFormat(commonFormat: .pcmFormatInt16,
                               sampleRate: 24000, channels: 1, interleaved: true)!
    }

    func start() throws {
        guard !started else { return }
        #if os(iOS)
        let session = AVAudioSession.sharedInstance()
        // Voice-processing mode (AEC عبر VPIO داخل AVAudioEngine).
        do {
            try session.setCategory(.playAndRecord, mode: .voiceChat,
                                    options: [.allowBluetooth, .defaultToSpeaker])
            onDiagnostics?("start: setCategory OK")
        } catch {
            onDiagnostics?("start FAILED at setCategory: \(error.localizedDescription)")
            throw error
        }
        do {
            try session.setActive(true, options: [])
            onDiagnostics?("start: setActive OK")
        } catch {
            onDiagnostics?("start FAILED at setActive: \(error.localizedDescription)")
            throw error
        }
        #endif

        // Output graph
        engine.attach(player)
        engine.connect(player, to: engine.mainMixerNode, format: format)
        player.volume = 1.0
        engine.mainMixerNode.outputVolume = 1.0

        // AEC: فعّل voice processing على الـ I/O node قبل start (Apple official path)
        do {
            try engine.inputNode.setVoiceProcessingEnabled(true)
            onDiagnostics?("start: setVoiceProcessingEnabled OK")
        } catch {
            onDiagnostics?("start FAILED at setVoiceProcessingEnabled: \(error.localizedDescription)")
            throw error
        }

        // Input tap (AEC-applied)
        let input = engine.inputNode
        let hwFormat = input.outputFormat(forBus: 0)
        converter = AVAudioConverter(from: hwFormat, to: format)!
        input.installTap(onBus: 0, bufferSize: 2048, format: hwFormat) { [weak self] buffer, _ in
            guard let self, let conv = self.converter else { return }
            if let data = self.convert(buffer, using: conv) {
                self.pcmCallbacks += 1
                self.pcmBytesTotal += data.count
                if self.pcmCallbacks == 1 {
                    self.onDiagnostics?("MIC firstPCM frames=\(buffer.frameLength) bytes=\(data.count)")
                }
                self.onPCM?(data)
                if let level = Self.rmsLevel(data) { self.onMicLevel?(level) }
            }
        }
        onDiagnostics?("start: installTap OK hwRate=\(Int(hwFormat.sampleRate)) ch=\(hwFormat.channelCount)")

        engine.prepare()
        do {
            try engine.start()
        } catch {
            onDiagnostics?("start FAILED at engine.start: \(error.localizedDescription)")
            throw error
        }
        player.play()
        started = true
        onDiagnostics?("start: engine started OK")

        #if os(iOS)
        let vpEnabled = engine.inputNode.isVoiceProcessingEnabled
        let vpBypassed = engine.inputNode.isVoiceProcessingBypassed
        let route = session.currentRoute.outputs.first?.portType.rawValue ?? "?"
        let sessionMode = session.mode.rawValue
        onDiagnostics?("AEC vpEnabled=\(vpEnabled) vpBypassed=\(vpBypassed) mode=\(sessionMode) route=\(route) hwRate=\(Int(hwFormat.sampleRate))")
        #endif
    }

    // MARK: - Playback (continuous schedule-ahead, thread-safe)

    /// يُستدعى عند بداية رد جديد — يصفّر الـ counters ويبدأ وضع التدفق.
    func beginSpeaking() {
        workQueue.async { [weak self] in
            self?.resetStats()
            self?.isSpeaking = true
        }
    }

    /// Enqueue PCM16 (24kHz mono). Coalesces small deltas and schedules ahead.
    func enqueueAudio(_ data: Data) {
        guard !data.isEmpty else { return }
        // read-only level (خارج workQueue، لا يؤثر على توقيت الـ scheduling)
        if let level = Self.rmsLevel(data) { onOutputLevel?(level) }
        workQueue.async { [weak self] in
            guard let self else { return }
            self.receivedBytes += data.count
            self.pendingData.append(data)
            self.peakQueueDepth = max(self.peakQueueDepth, self.pendingData.count)
            self.pump()
        }
    }

    /// يُستدعى عند نهاية الرد — يفلش tail buffer (<100ms) فوراً ويطبع الـ counters.
    func flushTail() {
        workQueue.async { [weak self] in
            guard let self else { return }
            self.isSpeaking = false
            self.pump(forceTail: true)
            self.onDiagnostics?(self.statsSummary())
        }
    }

    /// Barge-in: مسح فوري لكل الـ audio المعلق + إيقاف الرد القديم.
    func flush() {
        workQueue.async { [weak self] in
            guard let self else { return }
            self.player.stop()
            self.player.reset()
            self.pendingData.removeAll()
            self.scheduledBuffers = 0
            self.isSpeaking = false
            self.player.play()
        }
    }

    private func statsSummary() -> String {
        "PLAYBACK received=\(receivedBytes) scheduled=\(scheduledBytes) completedBuf=\(completedBuffers) peakQueue=\(peakQueueDepth) underruns=\(underruns) tail=\(tailBytesFlushed) convErr=\(converterErrors) schedErr=\(scheduleErrors) remainingQueue=\(pendingData.count) remainingScheduled=\(scheduledBuffers)"
    }

    private func resetStats() {
        receivedBytes = 0; scheduledBytes = 0; completedBuffers = 0
        peakQueueDepth = 0; underruns = 0; tailBytesFlushed = 0
        converterErrors = 0; scheduleErrors = 0
    }

    /// جدولة مستمرة: يحافظ على maxScheduledAhead buffers مجدولة في الـ player.
    /// MUST run inside workQueue.
    private func pump(forceTail: Bool = false) {
        while scheduledBuffers < maxScheduledAhead {
            guard let data = nextBuffer(forceTail: forceTail) else { break }
            guard let buffer = Self.toBuffer(data, format: format) else {
                converterErrors += 1
                continue
            }
            scheduledBytes += data.count
            scheduledBuffers += 1
            player.scheduleBuffer(buffer) { [weak self] in
                guard let self else { return }
                self.workQueue.async {
                    self.completedBuffers += 1
                    self.scheduledBuffers -= 1
                    if self.scheduledBuffers == 0 && self.isSpeaking {
                        // نفدت كل الـ buffers المجدولة والرد ما زال يتدفق → underrun/gap
                        self.underruns += 1
                    }
                    // حرر slot → املأه من الـ queue فوراً (no gap)
                    self.pump()
                    if self.pendingData.isEmpty && self.scheduledBuffers == 0 && !self.isSpeaking {
                        self.onPlaybackDrained?()
                    }
                }
            }
            if forceTail { break }   // forceTail يفلش tail واحد فقط
        }
    }

    /// يأخذ buffer واحد: ~100ms عادي، أو كل الـ tail في forceTail. MUST run inside workQueue.
    private func nextBuffer(forceTail: Bool) -> Data? {
        guard !pendingData.isEmpty else { return nil }
        var collected = Data()
        if forceTail {
            while !pendingData.isEmpty { collected.append(pendingData.removeFirst()) }
            tailBytesFlushed += collected.count
        } else {
            while !pendingData.isEmpty && collected.count < targetBufferBytes {
                collected.append(pendingData.removeFirst())
            }
        }
        return collected.isEmpty ? nil : collected
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

    /// Normalized RMS (0..1) من PCM16 — read-only، لا يمس الـ data.
    static func rmsLevel(_ data: Data) -> Double? {
        let count = data.count / MemoryLayout<Int16>.size
        guard count > 0 else { return nil }
        var sum = 0.0
        data.withUnsafeBytes { raw in
            guard let base = raw.bindMemory(to: Int16.self).baseAddress else { return }
            for i in 0..<count {
                let v = Double(base[i]) / 32768.0
                sum += v * v
            }
        }
        return (sum / Double(count)).squareRoot()
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
