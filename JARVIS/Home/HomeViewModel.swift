import SwiftUI
import Combine
#if canImport(UIKit)
import UIKit
#endif
#if canImport(AlarmKit)
import AlarmKit
#endif


/// Spoken-safe Arabic phrasing for every grounded device reply.
/// A bare "٢:٠٠ م" was read aloud as "2 AM" for a 14:00 event, so a time is now
/// stated three ways at once: hour in Arabic words, the part of day in words, and
/// the 24-hour clock in digits. Nothing here is for on-screen display.
private enum JarvisSpokenTime {
    private static let hourWords = ["", "واحد", "اثنين", "ثلاثة", "أربعة", "خمسة", "ستة",
                                    "سبعة", "ثمانية", "تسعة", "عشرة", "إحدى عشر", "اثنا عشر"]

    private static func partOfDay(_ hour24: Int) -> String {
        switch hour24 {
        case 0..<5:   return "بعد منتصف الليل"
        case 5..<12:  return "الصبح"
        case 12..<17: return "بعد الظهر"
        default:      return "المساء"
        }
    }

    private static func minuteWords(_ m: Int) -> String {
        guard m > 0 else { return "" }
        if m == 15 { return " والربع" }
        if m == 30 { return " والنص" }
        let ones = ["", "دقيقة واحدة", "دقيقتين", "ثلاث دقائق", "أربع دقائق", "خمس دقائق",
                    "ست دقائق", "سبع دقائق", "ثمان دقائق", "تسع دقائق"]
        let teens = ["عشر دقائق", "إحدى عشرة دقيقة", "اثنتي عشرة دقيقة", "ثلاث عشرة دقيقة",
                     "أربع عشرة دقيقة", "خمس عشرة دقيقة", "ست عشرة دقيقة", "سبع عشرة دقيقة",
                     "ثمان عشرة دقيقة", "تسع عشرة دقيقة"]
        let tens = ["", "عشر دقائق", "عشرين دقيقة", "ثلاثين دقيقة", "أربعين دقيقة", "خمسين دقيقة"]
        let unit = ["", "واحدة", "اثنتين", "ثلاث", "أربع", "خمس", "ست", "سبع", "ثمان", "تسع"]
        if m < 10 { return " و\(ones[m])" }
        if m < 20 { return " و\(teens[m - 10])" }
        let t = m / 10, u = m % 10
        if u == 0 { return " و\(tens[t])" }
        return " و\(unit[u]) و\(tens[t])"
    }

    /// e.g. "الساعة اثنين بعد الظهر (14:00)"
    static func phrase(_ date: Date, calendar: Calendar = .current) -> String {
        let h24 = calendar.component(.hour, from: date)
        let minute = calendar.component(.minute, from: date)
        let h12 = h24 % 12 == 0 ? 12 : h24 % 12
        let digits = String(format: "%02d:%02d", h24, minute)
        return "الساعة \(hourWords[h12])\(minuteWords(minute)) \(partOfDay(h24)) (\(digits))"
    }

    /// Arabic count phrase, e.g. "موعد واحد" / "موعدين" / "ثلاثة مواعيد".
    static func count(_ n: Int, one: String, two: String, many: String) -> String {
        let words = ["", "", "", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة", "عشرة"]
        if n == 1 { return one }
        if n == 2 { return two }
        if n <= 10 { return "\(words[n]) \(many)" }
        return "\(n) \(many)"
    }
}

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

            return "تم ضبط المنبه والتحقق منه في النظام على \(JarvisSpokenTime.phrase(date))"
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
        if Self.isAlarmRequest(t) {
            if let fireDate = Self.parseAlarmDate(t) {
                Self.diagRoute("alarm", text)
                await runAlarm(at: fireDate, userRequest: text)
                return
            }
            // Alarm intent with a time we could not read: answer from the device instead of
            // letting the model invent a reason (it claimed it lacked permission).
            Self.diagRoute("alarm-time-unclear", text)
            let ask = "ما فهمت الوقت، قلّه مرة ثانية"
            calendarMessage = ask
            state = .alert
            Self.diagGrounded("alarm-time-unclear", request: text, result: ask)
            voiceSession.sendGroundedDeviceResult(userRequest: text, result: ask)
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
        let shown = Array(events.prefix(5))
        let head = JarvisSpokenTime.count(shown.count, one: "موعد واحد", two: "موعدين", many: "مواعيد")
        if let only = shown.first, shown.count == 1 {
            return "\(dayLabel) عندك \(head): \(JarvisSpokenTime.phrase(only.start))، عنوانه: \(only.title)"
        }
        let lines = shown.map { "- \(JarvisSpokenTime.phrase($0.start))، عنوانه: \($0.title)" }
        return "\(dayLabel) عندك \(head):\n" + lines.joined(separator: "\n")
    }

    private static func formatReminders(_ reminders: [JarvisReminderItem]) -> String {
        guard !reminders.isEmpty else { return "لا توجد تذكيرات قادمة" }
        let shown = Array(reminders.prefix(5))
        let head = JarvisSpokenTime.count(shown.count, one: "تذكير واحد", two: "تذكيرين", many: "تذكيرات")
        if let only = shown.first, shown.count == 1 {
            return "عندك \(head): \(only.title)"
        }
        return "عندك \(head):\n" + shown.map { "- \($0.title)" }.joined(separator: "\n")
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
        let day = DateFormatter()
        day.locale = Locale(identifier: "ar_QA")
        day.dateFormat = "EEEE"
        let shown = Array(meetings.prefix(5))
        let head = JarvisSpokenTime.count(shown.count, one: "اجتماع واحد", two: "اجتماعين", many: "اجتماعات")
        let lines = shown.map {
            "- \(day.string(from: $0.start)) \(JarvisSpokenTime.phrase($0.start))، عنوانه: \($0.title)، عبر \($0.provider.displayName)"
        }
        if shown.count == 1, let only = lines.first {
            return "عندك \(head): " + only.dropFirst(2)
        }
        return "عندك \(head):\n" + lines.joined(separator: "\n")
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

    /// Spoken Arabic time for an alarm. Device evidence: "بعد دقيقتين" and
    /// "على ٤:٥٦ pm" both returned nil, the request fell through to the model, and it
    /// invented an excuse about permissions. The parser now covers the dual form, spelled
    /// numbers, fractions of an hour, Arabic-Indic digits, HH:MM and the meridiem words.
    static func parseAlarmDate(_ raw: String, now: Date = Date()) -> Date? {
        let t = normalizedDigits(raw)
        if let offset = relativeOffset(in: t) { return now.addingTimeInterval(offset) }
        return clockDate(in: t, now: now)
    }

    /// Arabic-Indic digits → ASCII, and tatweel/diacritics dropped.
    private static func normalizedDigits(_ raw: String) -> String {
        let eastern = ["٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
                       "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9"]
        var t = raw.lowercased()
        for (a, b) in eastern { t = t.replacingOccurrences(of: a, with: b) }
        return t.replacingOccurrences(of: "ـ", with: "")
    }

    /// Spelled numbers that can precede دقائق/ساعات. Longest first so "خمسة عشر" wins.
    private static let spelledNumbers: [(String, Int)] = [
        ("خمسة عشر", 15), ("خمس عشرة", 15), ("عشرين", 20), ("عشرة", 10), ("عشر", 10),
        ("تسعة", 9), ("تسع", 9), ("ثمانية", 8), ("ثماني", 8), ("ثمان", 8),
        ("سبعة", 7), ("سبع", 7), ("ستة", 6), ("ست", 6), ("خمسة", 5), ("خمس", 5),
        ("أربعة", 4), ("اربعة", 4), ("أربع", 4), ("اربع", 4),
        ("ثلاثة", 3), ("ثلاث", 3), ("اثنتين", 2), ("اثنين", 2), ("ثنتين", 2),
    ]

    private static func firstInt(_ text: String, pattern: String) -> Int? {
        guard let r = text.range(of: pattern, options: .regularExpression) else { return nil }
        return String(text[r]).split(whereSeparator: { !$0.isNumber }).compactMap { Int($0) }.first
    }

    /// "بعد دقيقتين" · "بعد خمس دقايق" · "ربع ساعة" · "ساعة ونص" · "بعد 10 دقائق"
    private static func relativeOffset(in t: String) -> TimeInterval? {
        let minuteWord = "(?:دقيقة|دقيقه|دقايق|دقائق)"
        let hourWord = "(?:ساعة|ساعه|ساعات)"

        // fractions and compounds first — "ساعة ونص" must not read as a bare hour
        if t.range(of: "(?:ساعة|ساعه)\\s*و\\s*(?:نص|نصف)", options: .regularExpression) != nil { return 5400 }
        if t.range(of: "(?:ربع)\\s*(?:ساعة|ساعه)", options: .regularExpression) != nil { return 900 }
        if t.range(of: "(?:نص|نصف)\\s*(?:ساعة|ساعه)", options: .regularExpression) != nil { return 1800 }
        if t.range(of: "(?:ثلث)\\s*(?:ساعة|ساعه)", options: .regularExpression) != nil { return 1200 }

        // dual: two minutes / two hours, written as one word
        if t.contains("دقيقتين") || t.contains("دقيقتان") { return 120 }
        if t.contains("ساعتين") || t.contains("ساعتان") { return 7200 }

        // digits + unit
        if let n = firstInt(t, pattern: "\\d{1,3}\\s*" + minuteWord), n > 0 { return Double(n * 60) }
        if let n = firstInt(t, pattern: "\\d{1,2}\\s*" + hourWord), n > 0 { return Double(n * 3600) }

        // spelled number + unit
        for (word, value) in spelledNumbers {
            if t.range(of: word + "\\s*" + minuteWord, options: .regularExpression) != nil { return Double(value * 60) }
            if t.range(of: word + "\\s*" + hourWord, options: .regularExpression) != nil { return Double(value * 3600) }
        }

        // bare single unit, only with a "بعد" so a clock time is never swallowed
        if t.range(of: "بعد\\s*" + minuteWord, options: .regularExpression) != nil { return 60 }
        if t.range(of: "بعد\\s*" + hourWord, options: .regularExpression) != nil { return 3600 }
        return nil
    }

    /// "الساعة 7" · "على 4:56 pm" · "الساعة ٨ ونص مساءً" · "الفجر" markers.
    private static func clockDate(in t: String, now: Date) -> Date? {
        var hour: Int
        var minute = 0

        if let r = t.range(of: "\\d{1,2}\\s*[:.]\\s*\\d{2}", options: .regularExpression) {
            let nums = String(t[r]).split(whereSeparator: { !$0.isNumber }).compactMap { Int($0) }
            guard let h = nums.first, nums.count > 1 else { return nil }
            hour = h
            minute = nums[1]
        } else if let h = firstInt(t, pattern: "(?:الساعة|الساعه|ساعة|ساعه|على|عند)\\s*\\d{1,2}") {
            hour = h
        } else {
            return nil
        }
        guard (0...23).contains(hour), (0...59).contains(minute) else { return nil }

        if t.range(of: "(?:ونص|و نص|ونصف|و نصف)", options: .regularExpression) != nil, minute == 0 { minute = 30 }
        if t.range(of: "(?:وربع|و ربع)", options: .regularExpression) != nil, minute == 0 { minute = 15 }

        let pmWords = ["مساء", "مساءً", "مساءا", "بالليل", "الليل", "العصر", "المغرب", "العشاء", "الظهر", "بعد الظهر"]
        let amWords = ["صباح", "صباحاً", "صباحا", "الصبح", "الفجر"]
        let isPM = t.contains("pm") || t.contains("p.m")
            || t.range(of: "\\d\\s*م(?:\\b|$)", options: .regularExpression) != nil
            || pmWords.contains { t.contains($0) }
        let isAM = t.contains("am") || t.contains("a.m")
            || t.range(of: "\\d\\s*ص(?:\\b|$)", options: .regularExpression) != nil
            || amWords.contains { t.contains($0) }
        if isPM, hour < 12 { hour += 12 }
        if isAM, hour == 12 { hour = 0 }

        var c = Calendar.current.dateComponents([.year, .month, .day], from: now)
        c.hour = hour
        c.minute = minute
        c.second = 0
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
