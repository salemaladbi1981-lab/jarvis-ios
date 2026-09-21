import Foundation
import AVFoundation

/// Audio chunk مع level محسوب مسبقاً (من PCM) — يُنشر عند بداية render.
private struct AudioChunk {
    let data: Data
    let level: Double
}

/// Shared full-duplex audio I/O: ONE AVAudioEngine + ONE AVAudioSession.
/// Voice-processing (.voiceChat) mode → native AEC (speaker echo removed from mic).
/// Continuous schedule-ahead playback + full runtime counters + serial queue (thread-safe).
final class VoiceAudioEngine {
    private let engine = AVAudioEngine()
    private let player = AVAudioPlayerNode()
    private let format: AVAudioFormat   // 24kHz mono PCM16
    private var started = false
    private var interrupted = false
    private var interruptionObserver: NSObjectProtocol?
    private var routeObserver: NSObjectProtocol?
    private var converter: AVAudioConverter?

    // Mic tap (AEC-applied via voice-processing session)
    var onPCM: ((Data) -> Void)?
    var onDiagnostics: ((String) -> Void)?
    var onPlaybackDrained: ((Int) -> Void)?   // يمرّر playbackGeneration (هوية دورة التشغيل)

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
    private var scheduledLevels: [Double] = []   // levels للمقاطع المجدولة (لترتيب الـ advance)
    private var hasDrained = false               // يمنع إشعار الاكتمال المزدوج
    private var playbackGeneration = 0           // يُبطل الدورة السابقة عند barge-in/رد جديد

    /// الجيل الحالي لدورة التشغيل (read-only، thread-safe) — تُربط به نتيجة الرد.
    var currentGeneration: Int {
        workQueue.sync { self.playbackGeneration }
    }

    /// مدة الصوت المشغّل فعلاً (مللي ثانية) من الـ buffers المكتملة (~100ms لكل buffer).
    /// تُستخدم في conversation.item.truncate لقطع الجزء غير المسموع عند المقاطعة.
    var playedDurationMs: Int {
        // 24kHz mono 16-bit = 48 بايت/ms؛ الـ buffer الافتراضي 4800 بايت ≈ 100ms.
        workQueue.sync { completedBuffers * (targetBufferBytes / 48) }
    }
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
        // NOTE: start() is invoked from a @MainActor view-model path on device.
        // Keep AVAudioSession activation off the main thread to avoid UI stalls/route churn.
        var sessionError: Error?
        let sem = DispatchSemaphore(value: 0)
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            do {
                try session.setCategory(.playAndRecord, mode: .voiceChat,
                                        options: [.allowBluetooth, .defaultToSpeaker])
                self?.onDiagnostics?("start: setCategory OK")
                try session.setActive(true, options: [])
                self?.onDiagnostics?("start: setActive OK")
            } catch {
                sessionError = error
            }
            sem.signal()
        }
        sem.wait()
        if let sessionError {
            onDiagnostics?("start FAILED at AVAudioSession activation: \(sessionError.localizedDescription)")
            throw sessionError
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
        registerSessionObservers()
        #endif
    }

    // MARK: - AVAudioSession interruption/route handling (iOS)
    // policy: transient/system overlay لا يوقف الصوت؛ interruption حقيقي يpause ثم resume آمن.
    // لا نلغي الرد ولا نمسح الـ playback إلا عند stop صريح.

    private func registerSessionObservers() {
        #if os(iOS)
        let nc = NotificationCenter.default
        interruptionObserver = nc.addObserver(forName: AVAudioSession.interruptionNotification, object: nil, queue: .main) { [weak self] note in
            self?.handleInterruption(note)
        }
        routeObserver = nc.addObserver(forName: AVAudioSession.routeChangeNotification, object: nil, queue: .main) { [weak self] note in
            self?.handleRouteChange(note)
        }
        #endif
    }

    private func handleInterruption(_ note: Notification) {
        #if os(iOS)
        guard let info = note.userInfo,
              let raw = info[AVAudioSessionInterruptionTypeKey] as? UInt,
              let type = AVAudioSession.InterruptionType(rawValue: raw) else { return }
        switch type {
        case .began:
            // Interruption حقيقي (مكالمة/سيري/صوت نظام) — الـ system أوقف الـ engine.
            // لا flush ولا cancel — نحفظ الـ playback ونعلّم الحالة فقط.
            onDiagnostics?("session interruption began (no flush — preserving playback)")
            workQueue.async { [weak self] in self?.interrupted = true }
        case .ended:
            onDiagnostics?("session interruption ended")
            let optsRaw = (info[AVAudioSessionInterruptionOptionKey] as? UInt) ?? 0
            if AVAudioSession.InterruptionOptions(rawValue: optsRaw).contains(.shouldResume) {
                resumeAfterInterruption()
            }
        @unknown default:
            break
        }
        #endif
    }

    private func handleRouteChange(_ note: Notification) {
        #if os(iOS)
        guard let info = note.userInfo,
              let raw = info[AVAudioSessionRouteChangeReasonKey] as? UInt,
              let reason = AVAudioSession.RouteChangeReason(rawValue: raw) else { return }
        onDiagnostics?("route change reason=\(reason.rawValue)")
        // لا نوقف الصوت عند route change عادي (نترك الـ engine يتعامل معه)
        #endif
    }

    private func resumeAfterInterruption() {
        #if os(iOS)
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self else { return }
            do {
                try AVAudioSession.sharedInstance().setActive(true, options: [])
            } catch {
                self.onDiagnostics?("resume setActive FAILED: \(error.localizedDescription)")
            }
            self.workQueue.async {
                self.interrupted = false
                if self.started && !self.engine.isRunning {
                    do { try self.engine.start() }
                    catch { self.onDiagnostics?("resume engine.start FAILED: \(error.localizedDescription)") }
                }
                self.player.play()
            }
        }
        #else
        workQueue.async { [weak self] in
            guard let self else { return }
            self.interrupted = false
            if self.started && !self.engine.isRunning {
                do { try self.engine.start() }
                catch { self.onDiagnostics?("resume engine.start FAILED: \(error.localizedDescription)") }
            }
            self.player.play()
        }
        #endif
    }

    // MARK: - Playback (continuous schedule-ahead, thread-safe)

    /// يُستدعى عند بداية رد جديد — يصفّر الـ counters ويبدأ وضع التدفق.
    func beginSpeaking() {
        workQueue.async { [weak self] in
            guard let self else { return }
            self.playbackGeneration += 1   // إبطال أي عمل قديم (رد سابق)
            // بدء رد جديد: أوقف أي ذيل سابق + صفّر الطابور (اتساق مع المقاطعة)
            self.player.stop()
            self.player.reset()
            self.pendingData.removeAll()
            self.scheduledBuffers = 0
            self.scheduledLevels.removeAll()
            self.hasDrained = false
            self.resetStats()
            self.isSpeaking = true
            self.player.play()
        }
    }

    /// Enqueue PCM16 (24kHz mono). Coalesces small deltas and schedules ahead.
    func enqueueAudio(_ data: Data) {
        guard !data.isEmpty else { return }
        // لا level هنا — الـ level يُنشر عند بداية render (ربط بموضع التشغيل)
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
            self.checkDrain()
            self.onDiagnostics?(self.statsSummary())
        }
    }

    /// Barge-in: مسح فوري لكل الـ audio المعلق + إيقاف الرد القديم.
    func flush() {
        workQueue.async { [weak self] in
            guard let self else { return }
            self.playbackGeneration += 1   // إبطال الدورة السابقة (stale callbacks/levels)
            self.player.stop()
            self.player.reset()
            self.pendingData.removeAll()
            self.scheduledBuffers = 0
            self.scheduledLevels.removeAll()
            self.hasDrained = false
            self.isSpeaking = false
            self.onOutputLevel?(0)   // تصفير فوري للمستوى عند الإلغاء
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
            guard let chunk = nextBuffer(forceTail: forceTail) else { break }
            guard let buffer = Self.toBuffer(chunk.data, format: format) else {
                converterErrors += 1
                continue
            }
            scheduledBytes += chunk.data.count
            scheduledBuffers += 1
            let gen = playbackGeneration
            if scheduledBuffers == 1 {
                // أول مقطع يبدأ التشغيل الآن → انشر level فوراً
                self.onOutputLevel?(chunk.level)
            } else {
                self.scheduledLevels.append(chunk.level)
            }
            // .dataPlayedBack: إثبات انتهاء تشغيل الـ buffer (وليس لنشر المستوى أثناء المقطع).
            player.scheduleBuffer(buffer, completionCallbackType: .dataPlayedBack) { [weak self] _ in
                guard let self else { return }
                self.workQueue.async {
                    guard gen == self.playbackGeneration else { return }  // عمل قديم ملغى
                    self.completedBuffers += 1
                    self.scheduledBuffers -= 1
                    // advance: انشر level الـ المقطع التالي (يبدأ تشغيله الآن)
                    if !self.scheduledLevels.isEmpty {
                        self.onOutputLevel?(self.scheduledLevels.removeFirst())
                    } else if self.pendingData.isEmpty && self.scheduledBuffers == 0 && self.isSpeaking {
                        // فراغ الصوت أثناء استمرار التوليد → تصفير المستوى (لا drain)
                        self.onOutputLevel?(0)
                    }
                    if self.scheduledBuffers == 0 && self.isSpeaking {
                        // نفدت كل الـ buffers المجدولة والرد ما زال يتدفق → underrun/gap
                        self.underruns += 1
                    }
                    // حرر slot → املأه من الـ queue فوراً (no gap)
                    self.pump()
                    self.checkDrain()
                }
            }
            if forceTail { break }   // forceTail يفلش tail واحد فقط
        }
    }

    /// شرط انتهاء التشغيل (مرة واحدة): انتهى التوليد + الذيل مُصرَّف + لا بيانات منتظرة
    /// + لا مقاطع قيد التشغيل → إشعار اكتمال واحد + تصفير المستوى.
    private func checkDrain() {
        guard !hasDrained,
              !isSpeaking,
              pendingData.isEmpty,
              scheduledBuffers == 0 else { return }
        hasDrained = true
        scheduledLevels.removeAll()
        onOutputLevel?(0)
        onPlaybackDrained?(playbackGeneration)   // هوية الدورة التي اكتمل تشغيلها
    }

    /// يأخذ buffer واحد: ~100ms عادي، أو كل الـ tail في forceTail. MUST run inside workQueue.
    private func nextBuffer(forceTail: Bool) -> AudioChunk? {
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
        guard !collected.isEmpty else { return nil }
        return AudioChunk(data: collected, level: Self.rmsLevel(collected) ?? 0)
    }

    func stop() {
        workQueue.async { [weak self] in
            guard let self else { return }
            self.playbackGeneration += 1   // إبطال الدورة
            self.scheduledLevels.removeAll()
            self.hasDrained = true    // منع onPlaybackDrained من الدورة الموقوفة
            self.pendingData.removeAll()
            self.scheduledBuffers = 0
            self.onOutputLevel?(0)   // تصفير المستوى عند التوقف
        }
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        started = false
        #if os(iOS)
        DispatchQueue.global(qos: .utility).async { [weak self] in
            do {
                try AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
                self?.onDiagnostics?("stop: setActive(false) OK")
            } catch {
                self?.onDiagnostics?("stop: setActive(false) FAILED: \(error.localizedDescription)")
            }
        }
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
