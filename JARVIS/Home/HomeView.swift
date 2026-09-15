import SwiftUI

/// P2.2 native iOS Home — approved hierarchy, provider-driven data,
/// registry-driven approval, generated design tokens.
struct HomeView: View {
    @StateObject private var vm = HomeViewModel()
    @State private var selectedTab = "home"

    private let suggestions = [
        "وش عندي في الجدول؟",
        "فعّل وضع التركيز",
        "ورّني كاميرا الباب",
        "شغّل شي هادي",
        "بطلع بكرة؟",
    ]

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: JarvisSpacing.lg) {
                    HeaderView()

                    hero

                    titleAndGreeting

                    WaveformView(state: vm.state)

                    statusLine

                    SmartHomeCard(devices: vm.homeDevices)
                        .onTapGesture { vm.requestAction(agentID: "core_home", action: "read-temperature") }

                    SecurityCard(status: vm.securityStatus ?? SecurityStatus(systemsNormal: true, doorsLocked: true, camerasActive: true))
                        .onTapGesture { vm.requestAction(agentID: "core_home", action: "unlock-door") }

                    MediaCard(track: vm.mediaTrack ?? MediaTrack(title: "Blinding Lights", artist: "The Weeknd", current: "2:06", duration: "3:20"))

                    QuickSuggestions(suggestions: suggestions)

                    VoiceInputBar(isListening: vm.isListening) { vm.cycleState() }

                    if let approval = vm.pendingApproval {
                        approvalCard(approval)
                    }
                }
                .padding(JarvisSpacing.lg)
            }

            BottomNavBar(selected: $selectedTab)
        }
        .background(
            LinearGradient(colors: [JarvisColor.bg_0, JarvisColor.bg_1], startPoint: .top, endPoint: .bottom)
                .ignoresSafeArea()
        )
        .task { await vm.load() }
    }

    private var hero: some View {
        ZStack {
            JarvisCoreView(state: vm.state, size: 250)
            JarvisOrbitView(
                agents: vm.agents(in: vm.activeGroup),
                coreSize: 250,
                activeAgentID: vm.state == .executing ? vm.agents(in: vm.activeGroup).first?.id : nil
            )
        }
        .frame(maxWidth: .infinity)
        .frame(height: 320)
        .id(vm.activeGroup)
        .transition(.opacity)
        .animation(.easeInOut(duration: JarvisMotion.groupTransition), value: vm.activeGroup)
        .contentShape(Rectangle())
        .gesture(
            DragGesture(minimumDistance: 40)
                .onEnded { g in
                    if g.translation.width < 0 { vm.nextGroup() } else { vm.prevGroup() }
                }
        )
        .accessibilityLabel("مدار الإيجنتات — مجموعة \(vm.activeGroup)")
    }

    private var titleAndGreeting: some View {
        VStack(spacing: 4) {
            Text("جارفس")
                .font(.custom("IBMPlexSansArabic-Bold", size: 30))
                .foregroundColor(JarvisColor.text_primary)
            Text("مساء الخير يا دكتور.")
                .font(.system(size: 16))
                .foregroundColor(JarvisColor.text_secondary)
            Text("كل شيء تحت السيطرة.")
                .font(.system(size: 13))
                .foregroundColor(JarvisColor.text_muted)
        }
        .frame(maxWidth: .infinity)
    }

    private var statusLine: some View {
        HStack {
            Circle()
                .fill(JarvisColor.primary_blue)
                .frame(width: 8, height: 8)
            Text(vm.statusText)
                .font(.system(size: 13))
                .foregroundColor(JarvisColor.text_secondary)
        }
        .accessibilityLabel(vm.statusText)
    }

    private func approvalCard(_ action: String) -> some View {
        JarvisCard {
            VStack(alignment: .leading, spacing: JarvisSpacing.md) {
                HStack {
                    Image(systemName: JarvisIconResolver.symbol(for: "util.alert"))
                        .foregroundColor(JarvisColor.warning_demo)
                    Text("طلب موافقة")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundColor(JarvisColor.text_primary)
                    Spacer()
                    DemoBadge()
                }
                Text("الإجراء: \(action)")
                    .font(.system(size: 13))
                    .foregroundColor(JarvisColor.text_secondary)
                HStack(spacing: JarvisSpacing.md) {
                    Button("موافقة") { vm.approve() }
                        .buttonStyle(.borderedProminent)
                        .tint(JarvisColor.success)
                    Button("رفض") { vm.reject() }
                        .buttonStyle(.bordered)
                        .tint(JarvisColor.danger)
                }
            }
        }
        .transition(.opacity)
    }
}
