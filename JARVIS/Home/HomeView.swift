import SwiftUI

/// Single-column Home (iPhone + iPad portrait + narrow split view).
/// Reuses shared hero/title/waveform components.
struct HomeView: View {
    @StateObject private var vm = HomeViewModel()
    @State private var selectedTab = "home"

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: JarvisSpacing.lg) {
                    HeaderView()

                    JarvisHeroView(vm: vm)

                    JarvisTitleGreetingView()

                    JarvisWaveformStatusView(vm: vm)

                    SmartHomeCard(devices: vm.homeDevices)
                        .onTapGesture { vm.requestAction(agentID: "core_home", action: "read-temperature") }

                    SecurityCard(status: vm.securityStatus ?? SecurityStatus(systemsNormal: true, doorsLocked: true, camerasActive: true))
                        .onTapGesture { vm.requestAction(agentID: "core_home", action: "unlock-door") }

                    MediaCard(track: vm.mediaTrack ?? MediaTrack(title: "Blinding Lights", artist: "The Weeknd", current: "2:06", duration: "3:20"))

                    QuickSuggestions(commands: QuickCommand.allCases) { cmd in
                        Task { await vm.handleQuickCommand(cmd) }
                    }

                    VoiceInputBar(isListening: vm.isListening) { vm.toggleVoice() }

                    if let msg = vm.calendarMessage {
                        Text(msg)
                            .font(.system(size: 14))
                            .foregroundColor(JarvisColor.text_primary)
                            .padding(JarvisSpacing.md)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(RoundedRectangle(cornerRadius: JarvisRadius.card).fill(JarvisColor.bg_1.opacity(0.45)))
                            .overlay(RoundedRectangle(cornerRadius: JarvisRadius.card).stroke(JarvisColor.primary_blue.opacity(0.16), lineWidth: 1))
                    }

                    if let approval = vm.pendingApproval {
                        ApprovalCardView(vm: vm, action: approval)
                    }
                    Color.clear.frame(height: 1).id("bottom")
                }
                .padding(JarvisSpacing.lg)
            }
            .onAppear {
                if ProcessInfo.processInfo.arguments.contains("-scrollBottom") {
                    proxy.scrollTo("bottom", anchor: .bottom)
                }
            }
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
