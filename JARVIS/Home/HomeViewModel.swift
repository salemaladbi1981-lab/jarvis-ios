import SwiftUI
import Combine
#if canImport(UIKit)
import UIKit
#endif

/// ViewModel bridging views → provider abstractions + registry policy.
/// Views never construct domain mock data directly.
@MainActor
final class HomeViewModel: ObservableObject {
    // State + group
    @Published var state: JarvisState = .idle
    @Published var activeGroup: String = "core"
    @Published var pendingApproval: String?

    // Provider-supplied data
    @Published private(set) var homeDevices: [SmartDevice] = []
    @Published private(set) var securityStatus: SecurityStatus?
    @Published private(set) var mediaTrack: MediaTrack?
    @Published private(set) var isListening = false
    @Published var calendarMessage: String?
    private var isVoiceStarting = false

    // V1 Visual: audio level (read-only) + agent orbit activity
    @Published var successPulse: Bool = false
    // V1: مستوى الصوت معزول في model خفيف — لا يُعيد بناء HomeView كامل
    let levels = VisualLevelModel()
    // FPS metric (read-only, غير UI state — لا re-render). يُقرأ من Xcode console/Instruments فقط.
    var frameTimeMs: Double = 0
    let orbit = AgentOrbitModel()
    // هل سبق هذا الاتصال ردٌ صوتي؟ (لتمييز .connected عند إعادة الاتصال)
    private var hasSpokenSinceConnect = false

    // Dependencies
    private let smartHome: SmartHomeProvider
    private let security: SecurityProvider
    private let media: MediaProvider
    private let voice: VoiceProvider
    private var approval: ApprovalPolicyEvaluator?
    private(set) var registry: AgentRegistry?
    private let calendarTools = CalendarTools(useMock: false)
    private let calendarProvider = AppleEventKitProvider()
    private let voiceSession = RealtimeVoiceSession()
    private var cancellables = Set<AnyCancellable>()
    private var isVoiceActive = false
    private var errorRecoveryTask: Task<Void, Never>?

    // V1.1 write tools (minimal coupling)
    private let eventWriter = AppleEventKitWriter()
    private var pendingWrite: PendingWrite?

    private enum PendingWrite {
        case createReminder(title: String)
        case createEvent(title: String, start: Date, end: Date)
        case updateReminder(id: String, title: String)
        case updateEvent(id: String, title: String)
        case completeReminder(id: String)
        case deleteReminder(id: String)
        case deleteEvent(id: String)
    }

    init(
        smartHome: SmartHomeProvider? = nil,
        security: SecurityProvider? = nil,
        media: MediaProvider? = nil,
        voice: VoiceProvider = MockVoiceProvider()
    ) {
        let demoRuntime = ProcessInfo.processInfo.arguments.contains("-demo")

        if let smartHome {
            self.smartHome = smartHome
        } else {
            self.smartHome = demoRuntime ? MockSmartHomeProvider() : UnavailableSmartHomeProvider()
        }

        if let security {
            self.security = security
        } else {
            self.security = demoRuntime ? MockSecurityProvider() : UnavailableSecurityProvider()
        }

        if let media {
            self.media = media
        } else {
            self.media = demoRuntime ? MockMediaProvider() : UnavailableMediaProvider()
        }

        self.voice = voice
        bindVoice()
    }

    private func bindVoice() {
        voiceSession.eventPublisher
            .receive(on: RunLoop.main)
            .sink { [weak self] event in
                guard let self else { return }
                self.state = JarvisStateMapper.state(for: event)
                switch event {
                case .listening:
                    self.isListening = true
                    // بداية دور جديد = نهاية الرد السابق → نرجع الـ orbit للحياد.
                    self.orbit.items.forEach { self.orbit.deactivate($0.id) }
                case .speaking:
                    // سجّل أن رداً صوتياً بدأ — حتى لا نمسح الـ agent عند .connected دون رد سابق.
                    self.hasSpokenSinceConnect = true
                case .disconnected:
                    // Transport/session is gone: clear local voice state immediately so the next
                    // mic tap performs a fresh connect instead of trying to stop a dead session.
                    self.isVoiceActive = false
                    self.isListening = false
                    self.voiceSession.stopListening()
                    // response.done / session ready → success + deactivate agents
                    self.orbit.items.forEach { self.orbit.deactivate($0.id) }
                    self.successPulse = true
                    self.hasSpokenSinceConnect = false
                case .connected:
                    self.isListening = false
                    // لا نمسح الـ active agent عند إعادة الاتصال إلا إذا سبقه رد صوتي فعلي.
                    if self.hasSpokenSinceConnect {
                        self.orbit.items.forEach { self.orbit.deactivate($0.id) }
                        self.hasSpokenSinceConnect = false
                    }
                    self.successPulse = true
                case .toolExecuting:
                    // Runtime agent events drive the orbit; never fake core_home here.
                    break
                case .interrupted:
                    // barge-in: transition سريع — يبقى agent إن وُجد
                    break
                case .error(let code):
                    // سجّل رمز الخطأ قبل أي تعيين للحالة — لا حالة حمراء عالقة على خطأ عابر.
                    print("[JARVIS-VOICE] error code: \(code)")
                    self.state = .alert
                    self.scheduleErrorRecovery()
                default: break
                }
            }
            .store(in: &cancellables)
        voiceSession.onTranscript = { [weak self] text in
            Task { await self?.routeVoiceTranscript(text) }
        }
        // V1 Visual: audio level forwarding (read-only)
        voiceSession.onMicLevel = { [weak self] level in
            // مستوى الصوت يأتي من الـ audio thread — نوصله إلى main حتى تُلاحظه SwiftUI (redraw).
            Task { @MainActor in self?.levels.setMicLevel(level) }
        }
        voiceSession.onOutputLevel = { [weak self] level in
            Task { @MainActor in self?.levels.setOutputLevel(level) }
        }
        // Real agent runtime events from backend drive the active orbit.
        voiceSession.onAgentRuntime = { [weak self] phase, agentID, fromAgentID in
            Task { @MainActor in
                guard let self,
                      let registry = self.registry,
                      let agent = registry.agents.first(where: { $0.id == agentID }) else { return }

                switch phase {
                case "handoff":
                    if agentID == "core_coordinator" {
                        // Return-to-coordinator handoff — لا نفعّل المنسق فوراً؛
                        // يبقى الـ specialist ظاهراً حتى نهاية الرد الصوتي.
                        break
                    }
                    if let fromAgentID,
                       let from = registry.agents.first(where: { $0.id == fromAgentID }) {
                        self.orbit.activate(from.id, name: from.name, group: from.group)
                        self.orbit.activate(agent.id, name: agent.name, group: agent.group)
                        self.orbit.handoff(from: from.id, to: agent.id)
                    } else {
                        self.orbit.activate(agent.id, name: agent.name, group: agent.group)
                    }
                case "started", "finished":
                    self.orbit.activate(agent.id, name: agent.name, group: agent.group)
                default:
                    break
                }
            }
        }

        // Playback handoff: فتح الفيديو في تطبيق YouTube الرسمي (من أداة youtube_play).
        voiceSession.onPlaybackHandoff = { [weak self] url, title in
            Task { @MainActor in
                guard let u = URL(string: url) else { return }
                #if canImport(UIKit)
                UIApplication.shared.open(u)
                #endif
            }
        }
        // Navigation handoff: فتح تطبيق الخرائط (Google Maps) على الوجهة (من أداة maps_navigate).
        voiceSession.onNavigationHandoff = { [weak self] url in
            Task { @MainActor in
                guard let u = URL(string: url) else { return }
                #if canImport(UIKit)
                UIApplication.shared.open(u)
                #endif
            }
        }
    }

    func load() async {
        registry = try? AgentRegistry.load()
        if let r = registry { approval = ApprovalPolicyEvaluator(registry: r) }

        if smartHome is UnavailableSmartHomeProvider {
            homeDevices = []
        } else {
            homeDevices = await smartHome.readDevices()
        }

        if security is UnavailableSecurityProvider {
            securityStatus = nil
        } else {
            securityStatus = await security.status()
        }

        if media is UnavailableMediaProvider {
            mediaTrack = nil
        } else {
            mediaTrack = await media.nowPlaying()
        }

        applyLaunchArguments()
    }

    /// Read launch arguments for deterministic screenshots:
    ///   -group core|system|content, -state idle|listening|...|approval
    private func applyLaunchArguments() {
        let args = ProcessInfo.processInfo.arguments
        if let gi = args.firstIndex(of: "-group"), gi + 1 < args.count {
            activeGroup = args[gi + 1]
        }
        if let si = args.firstIndex(of: "-state"), si + 1 < args.count {
            if let st = JarvisState(rawValue: args[si + 1]) {
                state = st
                if st == .approval {
                    requestAction(agentID: "core_home", action: "unlock-door")
                }
            }
        }
        // V1 Visual Prototype — orbit demo (Physical Visual Review فقط، لا timers وهمية)
        if let oi = args.firstIndex(of: "-orbit"), oi + 1 < args.count {
            switch args[oi + 1] {
            case "single":
                orbit.activate("core_home", name: "البيت", group: "core")
            case "handoff":
                orbit.activate("core_home", name: "البيت", group: "core")
                orbit.activate("core_writer", name: "الكاتب", group: "core")
                orbit.handoff(from: "core_home", to: "core_writer")
            case "multi":
                orbit.activate("core_home", name: "البيت", group: "core")
                orbit.activate("core_writer", name: "الكاتب", group: "core")
                orbit.activate("sys_builder", name: "البناء", group: "system")
            default: break
            }
        }
    }


    // MARK: Live voice (M3.5)
    func toggleVoice() {
        if isVoiceActive {
            if state == .speaking {
                // المقاطعة اليدوية أثناء الكلام (زر المايك) — إلغاء الرد فقط.
                // لا مقاطعة تلقائية من كلام الغرفة/الخلفية. الحالة تنتقل تلقائياً عبر
                // حدث .interrupted → JarvisStateMapper → .listening (لا حالة وهمية هنا).
                voiceSession.interrupt()
            } else {
                voiceSession.stopListening()
                isVoiceActive = false
                isListening = false
                state = .idle
            }
        } else if !isVoiceStarting {
            // منع re-entry: لا Task مكرر حتى تكتمل دورة البدء (كان يسبب multiple audio.start())
            isVoiceStarting = true
            Task {
                defer { isVoiceStarting = false }
                // 1) mic permission أولاً (كان مفقوداً — يمنع input صامت/فشل)
                let mic = AudioCapture.micPermission()
                if mic == .notDetermined {
                    let r = await AudioCapture.requestMic()
                    guard r == .granted else {
                        state = .alert
                        calendarMessage = "صلاحية الميكروفون مرفوضة — فعّلها من إعدادات النظام"
                        return
                    }
                } else if mic == .denied {
                    state = .alert
                    calendarMessage = "صلاحية الميكروفون مرفوضة — فعّلها من إعدادات النظام"
                    return
                }
                // 2) connect + start
                do {
                    guard let url = URL(string: RealtimeVoiceSession.backendBaseURL) else {
                        state = .alert; calendarMessage = "عنوان الخادم غير صالح"; return
                    }
                    try await voiceSession.connect(baseURL: url)
                    voiceSession.startListening()
                    isVoiceActive = true
                    isListening = true
                } catch {
                    state = .alert
                    calendarMessage = "تعذّر الاتصال بالخادم الصوتي"
                }
            }
        }
    }

    /// App Intent / App Shortcut (استدعاء من قفل الشاشة أو استئناف التطبيق):
    /// يستهلك الطلب مرة واحدة ولا يسمح لطلب Start جديد بإيقاف جلسة صوت قائمة.
    func handleAppIntentStart() {
        #if os(iOS)
        guard AppBridge.pendingStartVoice else { return }
        AppBridge.pendingStartVoice = false
        guard !isVoiceActive, !isVoiceStarting else { return }
        toggleVoice()
        #endif
    }

    /// إعادة تعيين الجلسة عند الخروج للخلفية — حتى يعمل المايك من أول ضغطة عند العودة
    /// (بدل ما يظن أن الجلسة ما زالت نشطة ويحاول stop بدل connect).
    func handleAppBackgrounded() {
        if isVoiceActive {
            voiceSession.disconnect()
            isVoiceActive = false
            isListening = false
            state = .idle
        }
    }

    /// Voice transcript → local tool route → spoken result.
    /// V1.1: إضافة إنشاء تذكير (بتأكيد) + أسئلة شخصية تعتمد على الذاكرة.
    func routeVoiceTranscript(_ text: String) async {
        let t = text.lowercased()
        // OBSERVATION MODE ONLY: log the router's decision without acting on it.
        let routedAgentID = AgentRouter.route(text)
        #if DEBUG
        print("[JARVIS-ROUTER] agent=\(routedAgentID) request=\(text)")
        #endif
        // أسئلة البريد يعالجها الـ backend LLM عبر function calling — لا نعترضها محلياً
        // (يمنع «وش أهم إيميلاتي اليوم؟» من الوصول لمسار التقويم بسبب كلمة «اليوم»)
        if Self.isEmailQuestion(t) { return }
        // 1) إنشاء تذكير (يتطلب تأكيد)
        if let reminderTitle = Self.parseCreateReminder(t) {
            requestReminderCreate(title: reminderTitle)
            return
        }
        // 2) قراءة التذكيرات (أداة محلية) — تُعرض على الشاشة فقط، لا sendText (لا رد منافس)
        if t.contains("تذكير") || t.contains("reminder") {
            await runReminders()
            return
        }
        // 3) قراءة التقويم (أداة محلية) — تُعرض على الشاشة فقط، لا sendText
        if t.contains("جدول") || t.contains("موعد") || t.contains("اليوم") || t.contains("بكرة") || t.contains("calendar") {
            await runCalendar(kind: "today")
            return
        }
        // 4) الذاكرة الشخصية — الدماغ الوحيد = backend (memory_tools عبر function calling).
        //    لا مسار محلي (MemoryStore.seeded) ولا sendText — يمنع الرد المزدوج/القفز.
        // 5) محادثة مباشرة — النموذج (الدماغ الواحد) رد بالفعل من الصوت.
    }

    // MARK: Quick commands (typed routing — no fragile text matching)
    func handleQuickCommand(_ cmd: QuickCommand) async {
        switch cmd {
        case .calendar:
            await runCalendar(kind: "today")
        case .reminders:
            await runReminders()
        case .tomorrow, .focus, .doorCamera, .calmMedia:
            // لا مسار تنفيذ حقيقي بعد — اعرض الحالة الصادقة، ولا تشغّل صوت/استماع.
            state = .alert
            calendarMessage = "\(cmd.label)\nالحالة: \(cmd.capabilityStatus.rawValue) — \(cmd.unavailableReason)"
        }
    }

    private func runCalendar(kind: String) async {
        state = .executing
        // OS permission flow: عند notDetermined اطلب الصلاحية فعليًا
        var access = await calendarProvider.eventAccess()
        if access == .notDetermined {
            access = await calendarProvider.requestEvents()
        }
        guard access == .authorized else {
            state = .alert
            calendarMessage = access == .denied
                ? "صلاحية التقويم مرفوضة — فعّلها من إعدادات النظام"
                : "التقويم غير متاح"
            return
        }
        let result = await calendarTools.today()
        state = .idle
        if result.ok {
            calendarMessage = Self.formatEvents(result.events)
        } else {
            state = .alert
            calendarMessage = "التقويم غير متاح"
        }
    }

    private func runReminders() async {
        state = .executing
        var access = await calendarProvider.reminderAccess()
        if access == .notDetermined {
            access = await calendarProvider.requestReminders()
        }
        guard access == .authorized else {
            state = .alert
            switch access {
            case .denied:
                calendarMessage = "صلاحية التذكيرات مرفوضة — فعّلها من إعدادات النظام"
            case .restricted:
                calendarMessage = "الوصول إلى التذكيرات مقيد"
            default:
                calendarMessage = "التذكيرات غير متاحة — حالة: " + AppleEventKitProvider.accessDebugString(.reminder)
            }
            return
        }
        let result = await calendarTools.upcomingReminders()
        state = .idle
        if result.ok {
            calendarMessage = Self.formatReminders(result.reminders)
        } else {
            state = .alert
            if result.error == "permission_denied" {
                calendarMessage = "صلاحية التذكيرات مرفوضة — فعّلها من إعدادات النظام"
            } else {
                let diag = result.debugReason.map { " (" + $0 + ")" } ?? ""
                calendarMessage = "التذكيرات غير متاحة" + diag
            }
        }
    }

    func requestReminderCreate(title: String) {
        pendingWrite = .createReminder(title: title)
        pendingApproval = "إنشاء تذكير: \(title)"
        state = .approval
    }

    func requestEventCreate(title: String, start: Date, end: Date) {
        pendingWrite = .createEvent(title: title, start: start, end: end)
        pendingApproval = "إنشاء موعد: \(title)"
        state = .approval
    }

    func approvePendingWrite() async {
        guard let pendingWrite else { return }
        self.pendingWrite = nil
        pendingApproval = nil
        state = .executing
        let result: WriteResult
        switch pendingWrite {
        case .createReminder(let title):
            result = await eventWriter.createReminder(title: title)
        case .createEvent(let title, let start, let end):
            result = await eventWriter.createEvent(title: title, start: start, end: end)
        case .updateReminder(let id, let title):
            result = await eventWriter.updateReminder(id: id, title: title)
        case .updateEvent(let id, let title):
            result = await eventWriter.updateEvent(id: id, title: title)
        case .completeReminder(let id):
            result = await eventWriter.completeReminder(id: id)
        case .deleteReminder(let id):
            result = await eventWriter.deleteReminder(id: id)
        case .deleteEvent(let id):
            result = await eventWriter.deleteEvent(id: id)
        }
        if result.ok {
            state = .idle
            calendarMessage = "تم التنفيذ"
        } else {
            state = .alert
            calendarMessage = result.error ?? "تعذّر التنفيذ"
        }
    }

    func cancelPendingWrite() {
        pendingWrite = nil
        pendingApproval = nil
        state = .idle
    }

    private func scheduleErrorRecovery() {
        errorRecoveryTask?.cancel()
        errorRecoveryTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            guard !Task.isCancelled else { return }
            await MainActor.run {
                guard let self, self.state == .alert else { return }
                self.state = .idle
            }
        }
    }

    private static func isEmailQuestion(_ t: String) -> Bool {
        let mailWords = ["ايميل", "إيميل", "بريد", "email", "mail", "inbox"]
        return mailWords.contains { t.contains($0) }
    }

    private static func parseCreateReminder(_ t: String) -> String? {
        let prefixes = ["ذكرني ", "ذكّرني ", "remind me "]
        for prefix in prefixes where t.hasPrefix(prefix) {
            let title = String(t.dropFirst(prefix.count)).trimmingCharacters(in: .whitespacesAndNewlines)
            if !title.isEmpty { return title }
        }
        return nil
    }

    static func formatEvents(_ events: [CalendarEventItem]) -> String {
        guard !events.isEmpty else { return "ما عندك مواعيد اليوم" }
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "ar_QA")
        formatter.dateFormat = "HH:mm"
        return events.map { event in
            if event.allDay { return "• \(event.title) — طوال اليوم" }
            return "• \(formatter.string(from: event.start)) — \(event.title)"
        }.joined(separator: "\n")
    }

    static func formatReminders(_ reminders: [ReminderItem]) -> String {
        guard !reminders.isEmpty else { return "ما عندك تذكيرات قادمة" }
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "ar_QA")
        formatter.dateStyle = .short
        formatter.timeStyle = .short
        return reminders.map { reminder in
            let due = reminder.due.map { " — \(formatter.string(from: $0))" } ?? ""
            return "• \(reminder.title)\(due)"
        }.joined(separator: "\n")
    }

    // MARK: Agent approval path
    func requestAction(agentID: String, action: String) {
        guard let approval else {
            pendingApproval = nil
            state = .alert
            return
        }
        let decision = approval.decision(agentID: agentID, action: action)
        switch decision {
        case .allow:
            pendingApproval = nil
            state = .executing
        case .requireApproval:
            pendingApproval = "\(agentID): \(action)"
            state = .approval
        case .deny:
            pendingApproval = nil
            state = .alert
        }
    }

    func approve() {
        guard pendingApproval != nil else { return }
        pendingApproval = nil
        state = .executing
    }

    func cancelApproval() {
        pendingApproval = nil
        state = .idle
    }
}
