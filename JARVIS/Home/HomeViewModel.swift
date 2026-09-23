import SwiftUI
import Combine
#if canImport(UIKit)
import UIKit
#endif
#if canImport(AlarmKit)
import AlarmKit
#endif


#if canImport(AlarmKit)
@available(iOS 26.0, *)
private struct JarvisAlarmMetadata: AlarmMetadata {}

@available(iOS 26.0, *)
enum JarvisAlarmScheduler {
    static func schedule(at date: Date) async -> String {
        do {
            let manager = AlarmManager.shared
            var authorization = manager.authorizationState
            if authorization == .notDetermined {
                authorization = try await manager.requestAuthorization()
            }
            guard authorization == .authorized else {
                return "صلاحية المنبه غير مفعلة — فعّل Alarm access لجارفس من الإعدادات"
            }

            let stop = AlarmButton(text: "إيقاف", textColor: .white, systemImageName: "stop.circle")
            let alert = AlarmPresentation.Alert(title: "تذكير من جارفس", stopButton: stop)
            let presentation = AlarmPresentation(alert: alert)
            let attributes = AlarmAttributes<JarvisAlarmMetadata>(
                presentation: presentation,
                tintColor: .yellow
            )
            let configuration = AlarmManager.AlarmConfiguration<JarvisAlarmMetadata>.alarm(
                schedule: .fixed(date),
                attributes: attributes
            )
            let id = UUID()
            _ = try await manager.schedule(id: id, configuration: configuration)
            print("[JARVIS-DIAG][alarm] schedule returned id=\(id) requested=\(date)")
            for a in try manager.alarms {
                print("[JARVIS-DIAG][alarm] AlarmManager.alarms id=\(a.id) state=\(String(describing: a.state))")
            }
            // Never claim success until AlarmKit itself reports the same alarm as scheduled.
            let scheduled = try manager.alarms.first { $0.id == id && $0.state == .scheduled }
            guard scheduled != nil else { return "تعذر التحقق من المنبه — لم يتم اعتماده في النظام" }

            let f = DateFormatter()
            f.locale = Locale(identifier: "ar_QA")
            f.timeZone = .current
            f.dateFormat = "h:mm a"
            return "تم ضبط المنبه والتحقق منه في النظام على \(f.string(from: date))"
        } catch {
            return "تعذر ضبط المنبه: \(error.localizedDescription)"
        }
    }
}
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
    @Published private(set) var meetingTargets: [MeetingLaunchTarget] = []
    @Published private(set) var meetingAccessState: CalendarPermissionState = .notDetermined
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

    /// App Intent / App Shortcut (استدعاء من قفل الشاشة): يبدأ الصوت إن كانت هناك علامة معلّقة.
    func handleAppIntentStart() {
        #if os(iOS)
        guard AppBridge.consumePendingStartVoice() else { return }
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

    // MARK: Evidence logging (diagnostic only — no behaviour change)

    /// Which local route/tool claimed a transcript.
    private static func diagRoute(_ route: String, _ text: String) {
        print("[JARVIS-DIAG][route] route=\(route) transcript=\(text)")
    }

    /// The exact grounded payload handed to Realtime, in full.
    private static func diagGrounded(_ site: String, request: String, result: String) {
        print("[JARVIS-DIAG][grounded] site=\(site) request=\(request)")
        print("[JARVIS-DIAG][grounded] site=\(site) result=\(result)")
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
        if Self.isEmailQuestion(t) {
            Self.diagRoute("backend-email", text)
            voiceSession.requestResponse()
            return
        }

        // Agent inventory is authoritative on-device from the bundled registry.
        // This bypasses stale backend/model memory for questions such as
        // "هل عندي وكيل اسمه معمار؟" / "من هو المدرب؟".
        if Self.isAgentInventoryQuestion(t) {
            Self.diagRoute("agent-inventory", text)
            let grounded = groundedAgentInventoryAnswer(for: t)
            calendarMessage = grounded
            Self.diagGrounded("agent-inventory", request: text, result: grounded)
            voiceSession.sendGroundedDeviceResult(userRequest: text, result: grounded)
            return
        }

        // Meeting discovery is authoritative on-device from EventKit. This avoids a stale
        // backend claiming it has no meeting access while Calendar access is already granted.
        if Self.isMeetingQuestion(t) {
            Self.diagRoute("meetings", text)
            await runMeetings(userRequest: text)
            return
        }
        // المنبه: AlarmKit على الجهاز — لا نعتمد على النموذج أو السيرفر.
        if Self.isAlarmRequest(t), let fireDate = Self.parseAlarmDate(t) {
            Self.diagRoute("alarm", text)
            await runAlarm(at: fireDate, userRequest: text)
            return
        }

        // 1) إنشاء تذكير (يتطلب تأكيد)
        if let reminderTitle = Self.parseCreateReminder(t) {
            Self.diagRoute("reminder-create", text)
            requestReminderCreate(title: reminderTitle)
            return
        }
        // 2) قراءة التذكيرات (أداة محلية) — تُعرض على الشاشة فقط، لا sendText (لا رد منافس)
        if t.contains("تذكير") || t.contains("reminder") {
            Self.diagRoute("reminders-read", text)
            await runReminders()
            return
        }
        // 3) قراءة التقويم (أداة محلية) — تُعرض على الشاشة فقط، لا sendText
        if t.contains("جدول") || t.contains("موعد") || t.contains("مواعيد") || t.contains("اليوم") || t.contains("بكرة") || t.contains("غد") || t.contains("تقويم") || t.contains("كلندر") || t.contains("calendar") || t.contains("tomorrow") {
            let wantsTomorrow = t.contains("بكرة") || t.contains("غد") || t.contains("tomorrow")
            Self.diagRoute(wantsTomorrow ? "calendar-tomorrow" : "calendar-today", text)
            await runCalendar(kind: wantsTomorrow ? "tomorrow" : "today")
            return
        }
        // 4) الذاكرة الشخصية — الدماغ الوحيد = backend (memory_tools عبر function calling).
        //    لا مسار محلي (MemoryStore.seeded) ولا sendText — يمنع الرد المزدوج/القفز.
        // 5) محادثة مباشرة/أدوات backend — بعد أن أخذت أدوات الجهاز أول حق في التوجيه.
        Self.diagRoute("backend-conversation", text)
        voiceSession.requestResponse()
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
        let isTomorrow = kind == "tomorrow"
        let result = isTomorrow ? await calendarTools.events(dayOffset: 1) : await calendarTools.today()
        state = .idle
        if result.ok {
            let grounded = Self.formatEvents(result.events, dayLabel: isTomorrow ? "بكرة" : "اليوم")
            calendarMessage = grounded
            Self.diagGrounded(isTomorrow ? "calendar-tomorrow" : "calendar-today",
                              request: isTomorrow ? "calendar tomorrow" : "calendar today", result: grounded)
            voiceSession.sendGroundedDeviceResult(userRequest: isTomorrow ? "calendar tomorrow" : "calendar today", result: grounded)
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
            let grounded = Self.formatReminders(result.reminders)
            calendarMessage = grounded
            Self.diagGrounded("reminders", request: "upcoming reminders", result: grounded)
            voiceSession.sendGroundedDeviceResult(userRequest: "upcoming reminders", result: grounded)
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

    private static func formatEvents(_ events: [JarvisCalendarEvent], dayLabel: String = "اليوم") -> String {
        guard !events.isEmpty else { return "لا توجد مواعيد \(dayLabel)" }
        let f = DateFormatter()
        f.locale = Locale(identifier: "ar_QA")
        f.dateFormat = "h:mm a"
        return events.prefix(5).map { "\(f.string(from: $0.start)) — \($0.title)" }.joined(separator: "\n")
    }

    private static func formatReminders(_ reminders: [JarvisReminderItem]) -> String {
        guard !reminders.isEmpty else { return "لا توجد تذكيرات قادمة" }
        return reminders.prefix(5).map { "• \($0.title)" }.joined(separator: "\n")
    }

    // MARK: V1.1 — write confirmation (minimal coupling)

    private static func isEmailQuestion(_ t: String) -> Bool {
        ["إيميل", "ايميل", "بريد", "email", "mail", "inbox"].contains { t.contains($0) }
    }

    private static func isAgentInventoryQuestion(_ t: String) -> Bool {
        let markers = ["وكيل", "وكلاء", "ايجنت", "إيجنت", "agent", "agents", "معمار", "المدرب"]
        return markers.contains { t.contains($0) }
    }

    private static func isMeetingQuestion(_ t: String) -> Bool {
        let markers = ["اجتماع", "اجتماعات", "meeting", "meetings", "zoom", "teams", "meet.google", "webex", "facetime"]
        return markers.contains { t.contains($0) }
    }

    func refreshMeetings(requestPermissionIfNeeded: Bool = false) async {
        state = .executing
        var access = calendarProvider.eventAccess()
        if access == .notDetermined && requestPermissionIfNeeded {
            access = await calendarProvider.requestEvents()
        }
        meetingAccessState = access

        guard access == .authorized else {
            meetingTargets = []
            state = access == .denied ? .alert : .idle
            calendarMessage = access == .denied
                ? "صلاحية التقويم مرفوضة — فعّلها من إعدادات النظام"
                : "اضغط تحديث الاجتماعات للسماح بقراءة تقويم الجهاز"
            return
        }

        do {
            meetingTargets = try await calendarProvider.upcomingMeetingTargets()
            state = .idle
            calendarMessage = Self.formatMeetings(meetingTargets)
        } catch {
            meetingTargets = []
            state = .alert
            calendarMessage = "تعذر قراءة الاجتماعات من تقويم الجهاز"
        }
    }

    /// Last-mile handoff for an explicit meeting button tap. EventKit is re-read
    /// immediately before returning the URL; no permission request or auto-join occurs here.
    func meetingHandoffURL(for target: MeetingLaunchTarget) -> URL? {
        calendarProvider.handoffURL(for: target, userInitiated: true)
    }

    private func runMeetings(userRequest: String) async {
        await refreshMeetings(requestPermissionIfNeeded: true)
        let grounded = Self.formatMeetings(meetingTargets)
        if meetingAccessState == .authorized {
            Self.diagGrounded("meetings", request: userRequest, result: grounded)
            voiceSession.sendGroundedDeviceResult(userRequest: userRequest, result: grounded)
        } else if let calendarMessage {
            Self.diagGrounded("meetings-unauthorized", request: userRequest, result: calendarMessage)
            voiceSession.sendGroundedDeviceResult(userRequest: userRequest, result: calendarMessage)
        }
    }

    private static func formatMeetings(_ meetings: [MeetingLaunchTarget]) -> String {
        guard !meetings.isEmpty else {
            return "ما لقيت اجتماعات قادمة بروابط مدعومة في تقويم الجهاز"
        }
        let f = DateFormatter()
        f.locale = Locale(identifier: "ar_QA")
        f.dateFormat = "EEE h:mm a"
        return meetings.prefix(5).map {
            "\(f.string(from: $0.start)) — \($0.title) — \($0.provider.displayName)"
        }.joined(separator: "\n")
    }

    private func groundedAgentInventoryAnswer(for query: String) -> String {
        guard let registry else {
            return "تعذر تحميل سجل الوكلاء على الجهاز"
        }

        let normalized = query
            .lowercased()
            .replacingOccurrences(of: "_", with: " ")
            .replacingOccurrences(of: "-", with: " ")

        let matches = registry.agents.filter { agent in
            let fields = [
                agent.id,
                agent.name,
                agent.role,
                agent.capabilities.joined(separator: " ")
            ]
            .joined(separator: " ")
            .lowercased()
            .replacingOccurrences(of: "_", with: " ")
            .replacingOccurrences(of: "-", with: " ")

            if normalized.contains(agent.name.lowercased()) { return true }
            return normalized
                .split(separator: " ")
                .map(String.init)
                .filter { $0.count >= 3 }
                .contains { fields.contains($0) }
        }

        guard !matches.isEmpty else {
            return "ما لقيت وكيل مطابق في سجل جارفس الرسمي على الجهاز"
        }

        return matches.prefix(5).map { agent in
            "\(agent.name) — \(agent.role) [\(agent.id)]"
        }.joined(separator: "\n")
    }

    private static func isAlarmRequest(_ t: String) -> Bool {
        t.contains("منبه") || t.contains("المنبه") || t.contains("alarm") || t.contains("صحني") || t.contains("صحّني")
    }

    private static func parseAlarmDate(_ raw: String, now: Date = Date()) -> Date? {
        let eastern = ["٠":"0","١":"1","٢":"2","٣":"3","٤":"4","٥":"5","٦":"6","٧":"7","٨":"8","٩":"9"]
        var t = raw
        for (a,b) in eastern { t = t.replacingOccurrences(of: a, with: b) }
        if let r = t.range(of: #"بعد\s+(\d+)\s*(دقيقة|دقايق|دقائق)"#, options: .regularExpression) {
            let x = String(t[r]).split(separator: " ").compactMap { Int($0) }.first ?? 0
            return x > 0 ? now.addingTimeInterval(Double(x * 60)) : nil
        }
        if let r = t.range(of: #"بعد\s+(\d+)\s*(ساعة|ساعه|ساعات)"#, options: .regularExpression) {
            let x = String(t[r]).split(separator: " ").compactMap { Int($0) }.first ?? 0
            return x > 0 ? now.addingTimeInterval(Double(x * 3600)) : nil
        }
        guard let r = t.range(of: #"(?:الساعة|الساعه|ساعة|ساعه)\s*(\d{1,2})(?::(\d{1,2}))?"#, options: .regularExpression) else { return nil }
        let nums = String(t[r]).split(whereSeparator: { !$0.isNumber }).compactMap { Int($0) }
        guard var hour = nums.first, (0...23).contains(hour) else { return nil }
        let minute = nums.count > 1 ? nums[1] : 0
        if (t.contains("مساء") || t.contains("بالليل")) && hour < 12 { hour += 12 }
        if t.contains("صباح") && hour == 12 { hour = 0 }
        var c = Calendar.current.dateComponents([.year,.month,.day], from: now)
        c.hour = hour; c.minute = minute; c.second = 0
        guard var d = Calendar.current.date(from: c) else { return nil }
        if d <= now { d = Calendar.current.date(byAdding: .day, value: 1, to: d) ?? d }
        return d
    }

    private func runAlarm(at date: Date, userRequest: String) async {
        state = .executing
        #if canImport(AlarmKit)
        if #available(iOS 26.0, *) {
            let result = await JarvisAlarmScheduler.schedule(at: date)
            calendarMessage = result
            state = result.hasPrefix("تم") ? .idle : .alert
            Self.diagGrounded("alarm", request: userRequest, result: result)
            voiceSession.sendGroundedDeviceResult(userRequest: userRequest, result: result)
            return
        }
        #endif
        state = .alert
        calendarMessage = "المنبه يتطلب iOS 26 أو أحدث"
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

    /// استرداد من خطأ عابر: بعد فترة قصيرة تعود الحالة إلى الخمول إن لم يأتِ حدث جديد.
    private func scheduleErrorRecovery() {
        errorRecoveryTask?.cancel()
        errorRecoveryTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 5_000_000_000)
            guard let self, !Task.isCancelled else { return }
            if self.state == .alert {
                self.state = .idle
                self.calendarMessage = nil
            }
        }
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
