import SwiftUI

/// iPad landscape two-zone composition:
/// Primary zone (Hero + title + waveform + voice) | Secondary zone (cards).
struct iPadLandscapeView: View {
    @StateObject private var vm = HomeViewModel()
    @State private var selectedTab = "home"

    var body: some View {
        VStack(spacing: 0) {
            HeaderView()
                .padding(.horizontal, JarvisSpacing.xl)
                .padding(.top, JarvisSpacing.lg)

            HStack(alignment: .top, spacing: JarvisSpacing.xl) {
                // Primary zone — Hero dominant
                VStack(spacing: JarvisSpacing.lg) {
                    JarvisHeroView(vm: vm, coreSize: 300)
                    JarvisTitleGreetingView()
                    JarvisWaveformStatusView(vm: vm)
                    VoiceInputBar(isListening: vm.isListening) { vm.cycleState() }
                    if let approval = vm.pendingApproval {
                        ApprovalCardView(vm: vm, action: approval)
                    }
                }
                .frame(maxWidth: .infinity)

                // Secondary zone — cards
                ScrollView {
                    VStack(spacing: JarvisSpacing.md) {
                        SmartHomeCard(devices: vm.homeDevices)
                            .onTapGesture { vm.requestAction(agentID: "core_home", action: "read-temperature") }
                        SecurityCard(status: vm.securityStatus ?? SecurityStatus(systemsNormal: true, doorsLocked: true, camerasActive: true))
                            .onTapGesture { vm.requestAction(agentID: "core_home", action: "unlock-door") }
                        MediaCard(track: vm.mediaTrack ?? MediaTrack(title: "Blinding Lights", artist: "The Weeknd", current: "2:06", duration: "3:20"))
                        QuickSuggestions(commands: QuickCommand.allCases) { cmd in
                            Task { await vm.handleQuickCommand(cmd) }
                        }
                    }
                }
                .frame(maxWidth: .infinity)
            }
            .padding(JarvisSpacing.xl)
        }
        .safeAreaInset(edge: .bottom) {
            BottomNavBar(selected: $selectedTab)
        }
        .background(
            LinearGradient(colors: [JarvisColor.bg_0, JarvisColor.bg_1], startPoint: .top, endPoint: .bottom)
                .ignoresSafeArea()
        )
        .task { await vm.load() }
    }
}
