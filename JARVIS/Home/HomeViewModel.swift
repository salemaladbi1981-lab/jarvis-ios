import SwiftUI
import Combine

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
                case .disconnected, .connected: self.isListening = false
                default: break
                }
            }
            .store(in: &cancellables)
        voiceSession.onTranscript = { [weak self] text in
            Task { await self?.routeVoiceTranscript(text) }
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
    }


    // MARK: Live voice (M3.5)
    func toggleVoice() {
        if isVoiceActive {
            voiceSession.stopListening()
            isVoiceActive = false
            isListening = false
            state = .idle
        } else {
            Task {
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

    /// Voice transcript (free text from speech) → local tool route → spoken result.
    func routeVoiceTranscript(_ text: String) async {
        let t = text.lowercased()
        if t.contains("تذكير") || t.contains("reminder") {
            await runReminders()
            speakResult()
        } else if t.contains("جدول") || t.contains("موعد") || t.contains("اليوم") || t.contains("بكرة") || t.contains("calendar") {
            await runCalendar(kind: "today")
            speakResult()
        } else {
            // غير موجه لأداة — دع النموذج الصوتي يرد مباشرة على النص.
            voiceSession.sendText(text)
        }
    }

    private func speakResult() {
        if let msg = calendarMessage {
            voiceSession.sendText(msg)
        }
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
        pendingApproval = nil
        state = .idle
    }
    func reject() {
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
