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

    // Dependencies
    private let smartHome: SmartHomeProvider
    private let security: SecurityProvider
    private let media: MediaProvider
    private let voice: VoiceProvider
    private var approval: ApprovalPolicyEvaluator?
    private(set) var registry: AgentRegistry?

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
