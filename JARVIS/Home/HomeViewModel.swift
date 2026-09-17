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

    // V1.1 Memory + write tools (minimal coupling)
    private var memory: MemoryStore?
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
        smartHome: SmartHomeProvider = MockSmartHomeProvider(),
        security: SecurityProvider = MockSecurityProvider(),
        media: MediaProvider = MockMediaProvider(),
        voice: VoiceProvider = MockVoiceProvider()
    ) {
        self.smartHome = smartHome
        self.security = security
        self.media = media
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
                case .listening: self.isListening = true
                case .disconnected, .connected:
                    self.isListening = false
                    // response.done / session ready → success + deactivate agents
                    self.orbit.items.forEach { self.orbit.deactivate($0.id) }
                    self.successPulse = true
                case .toolExecuting:
                    // agent نشط حقيقي أثناء tool execution (core_home للـ prototype)
                    self.orbit.activate("core_home", name: "البيت", group: "core")
                case .interrupted:
                    // barge-in: transition سريع — يبقى agent إن وُجد
                    break
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
        homeDevices = await smartHome.readDevices()
        securityStatus = await security.status()
        mediaTrack = await media.nowPlaying()
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
            voiceSession.stopListening()
            isVoiceActive = false
            isListening = false
            state = .idle
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

    /// App Intent / App Shortcut (استدعاء من قفل الشاشة): يبدأ الصوت إن كانت هناك علامة معلّقة.
    func handleAppIntentStart() {
        #if os(iOS)
        guard AppBridge.pendingStartVoice else { return }
        AppBridge.pendingStartVoice = false
        toggleVoice()
        #endif
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
        // 2) قراءة التذكيرات
        if t.contains("تذكير") || t.contains("reminder") {
            await runReminders()
            speakResult()
            return
        }
        // 3) قراءة التقويم
        if t.contains("جدول") || t.contains("موعد") || t.contains("اليوم") || t.contains("بكرة") || t.contains("calendar") {
            await runCalendar(kind: "today")
            speakResult()
            return
        }
        // 4) سؤال شخصي يعتمد على الذاكرة
        if let answer = memoryAnswer(for: t) {
            speak(answer)
            return
        }
        // 5) محادثة مباشرة — النموذج رد بالفعل من الصوت، لا نعيد إرسال النص
    }

    private func speakResult() {
        if let msg = calendarMessage {
            voiceSession.sendText(msg)
        }
    }

    private func speak(_ msg: String) {
        voiceSession.sendText(msg)
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

    private static func formatEvents(_ events: [JarvisCalendarEvent]) -> String {
        guard !events.isEmpty else { return "لا توجد مواعيد اليوم" }
        let f = DateFormatter()
        f.locale = Locale(identifier: "ar_QA")
        f.dateFormat = "h:mm a"
        return events.prefix(5).map { "\(f.string(from: $0.start)) — \($0.title)" }.joined(separator: "\n")
    }

    private static func formatReminders(_ reminders: [JarvisReminderItem]) -> String {
        guard !reminders.isEmpty else { return "لا توجد تذكيرات قادمة" }
        return reminders.prefix(5).map { "• \($0.title)" }.joined(separator: "\n")
    }

    // MARK: V1.1 — Memory + write confirmation (minimal coupling)

    private func ensureMemory() -> MemoryStore {
        if let m = memory { return m }
        let m = MemoryStore.seeded()
        memory = m
        return m
    }

    private static func isEmailQuestion(_ t: String) -> Bool {
        ["إيميل", "ايميل", "بريد", "email", "mail", "inbox"].contains { t.contains($0) }
    }

    private static func parseCreateReminder(_ t: String) -> String? {
        let markers = ["ذكرني", "ذكّرني", "remind me"]
        for m in markers {
            guard let r = t.range(of: m) else { continue }
            var title = String(t[r.upperBound...]).trimmingCharacters(in: .whitespacesAndNewlines)
            if title.hasPrefix("بـ") { title = String(title.dropFirst(2)) }
            else if title.hasPrefix("ب") { title = String(title.dropFirst(1)) }
            title = title.trimmingCharacters(in: .whitespacesAndNewlines)
            if !title.isEmpty { return title }
        }
        return nil
    }

    private func memoryAnswer(for t: String) -> String? {
        let mem = ensureMemory()
        let identity = ["من أنا", "وش اسمي", "من سالم", "عرفني"]
        let project = ["مشروع", "مشاريع", "شغال"]
        let decision = ["قرار", "قررنا", "نسخة", "مجمّد", "مجمد", "اعتماد"]

        var query = ""
        var scope = MemoryScope.current
        if identity.contains(where: { t.contains($0) }) {
            query = "اسم سالم هوية"
        } else if project.contains(where: { t.contains($0) }) {
            query = "مشروع"
        } else if decision.contains(where: { t.contains($0) }) {
            query = "قرار نسخة"
        } else if t.contains("قبل") || t.contains("سابق") || t.contains("تاريخ") || t.contains("قديم") {
            query = t; scope = .historical
        } else {
            return nil
        }

        let items = MemoryRetrieval.retrieve(from: mem.allItems(), query: query, scope: scope, limit: 3)
        guard !items.isEmpty else { return nil }
        return items.map { $0.content }.joined(separator: "\n")
    }

    private func requestReminderCreate(title: String) {
        pendingWrite = .createReminder(title: title)
        pendingApproval = "إنشاء تذكير: \(title)"
        state = .approval
    }

    private func executeWrite(_ w: PendingWrite) async {
        state = .executing
        let result: ToolWriteResult
        switch w {
        case .createReminder(let title):
            result = eventWriter.createReminder(title: title, due: nil)
        case .createEvent(let title, let start, let end):
            result = eventWriter.createEvent(title: title, start: start, end: end)
        case .updateReminder(let id, let title):
            result = eventWriter.updateReminder(id: id, title: title, due: nil)
        case .updateEvent(let id, let title):
            result = eventWriter.updateEvent(id: id, title: title, start: nil, end: nil)
        case .completeReminder(let id):
            result = eventWriter.completeReminder(id: id)
        case .deleteReminder(let id):
            result = eventWriter.deleteReminder(id: id)
        case .deleteEvent(let id):
            result = eventWriter.deleteEvent(id: id)
        }
        if result.ok {
            state = .idle
            calendarMessage = "تم التنفيذ بنجاح"
        } else {
            state = .alert
            calendarMessage = "تعذّر التنفيذ: \(result.error ?? "خطأ غير معروف")"
        }
    }

    // MARK: Agents
    func agents(in group: String) -> [Agent] {
        registry?.agents(in: group) ?? []
    }
    var allGroups: [String] {
        registry?.allGroupKeys ?? ["core", "system", "content"]
    }

    // MARK: Status
    var statusText: String {
        switch state {
        case .idle, .listening: return "أنا أستمع إليك…"
        case .thinking:  return "أفكّر…"
        case .speaking:  return "جارفس يتحدّث"
        case .executing: return "جارٍ التنفيذ…"
        case .alert:     return "تنبيه"
        case .approval:  return "بانتظار موافقتك"
        }
    }

    // MARK: Approval flow (registry-driven)
    func requestAction(agentID: String, action: String) {
        guard let approval else {
            state = .approval   // fail-safe without registry
            pendingApproval = action
            return
        }
        if approval.requiresApproval(agentID: agentID, action: action) {
            state = .approval
            pendingApproval = displayName(action)
        } else {
            state = .executing   // safe action proceeds (mock)
        }
    }

    func approve() {
        if let w = pendingWrite {
            pendingWrite = nil
            pendingApproval = nil
            Task { await executeWrite(w) }
        } else {
            pendingApproval = nil
            state = .idle
        }
    }
    func reject() {
        pendingWrite = nil
        pendingApproval = nil
        state = .idle
    }

    private func displayName(_ action: String) -> String {
        switch action {
        case "unlock-door": return "فتح باب المنزل"
        case "open-gate": return "فتح البوابة"
        case "disable-camera": return "تعطيل الكاميرا"
        case "disable-alarm": return "تعطيل الإنذار"
        default: return action
        }
    }

    // MARK: Demo interactions (P2.2 mock only)
    func cycleState() {
        let all: [JarvisState] = [.idle, .listening, .thinking, .speaking, .executing, .alert, .approval]
        let idx = all.firstIndex(of: state) ?? 0
        let next = all[(idx + 1) % all.count]
        state = next
        if next == .approval {
            // demonstrate a sensitive action requiring approval
            requestAction(agentID: "core_home", action: "unlock-door")
        }
    }

    func nextGroup() {
        let keys = allGroups
        let idx = keys.firstIndex(of: activeGroup) ?? 0
        activeGroup = keys[(idx + 1) % keys.count]
    }
    func prevGroup() {
        let keys = allGroups
        let idx = keys.firstIndex(of: activeGroup) ?? 0
        activeGroup = keys[(idx - 1 + keys.count) % keys.count]
    }
}
