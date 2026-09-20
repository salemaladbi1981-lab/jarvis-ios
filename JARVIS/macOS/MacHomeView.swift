import SwiftUI
import Foundation

/// macOS Home — approved cinematic desktop direction (three-zone):
/// Left: nav + connected provider cards (demo-only until live providers are wired)
/// Center: JARVIS + Core/orbit + title + greeting + waveform/status + suggestions + voice
/// Right: contextual modules (empty for now — no invented live data)
#if os(macOS)
struct MacHomeView: View {
    @StateObject private var vm = HomeViewModel()
    @State private var selectedTab = "home"

    /// Synthetic provider data is permitted only for explicitly launched screenshot/demo sessions.
    /// Normal production launches must never present mock home/security/media state as live truth.
    private var demoMode: Bool {
        ProcessInfo.processInfo.arguments.contains("-demo")
    }

    var body: some View {
        HStack(spacing: 0) {
            // LEFT zone — nav + provider-backed cards
            VStack(spacing: JarvisSpacing.md) {
                macSidebar

                if demoMode {
                    SmartHomeCard(devices: vm.homeDevices)
                        .onTapGesture { vm.requestAction(agentID: "core_home", action: "read-temperature") }

                    if let status = vm.securityStatus {
                        SecurityCard(status: status)
                            .onTapGesture { vm.requestAction(agentID: "core_home", action: "unlock-door") }
                    }

                    if let track = vm.mediaTrack, !track.title.isEmpty {
                        MediaCard(track: track)
                    }
                } else {
                    providerUnavailableCard
                }

                Spacer()
            }
            .frame(width: 340)
            .padding(JarvisSpacing.lg)
            .background(JarvisColor.bg_0.opacity(0.5))

            // CENTER zone — hero dominant
            ScrollView {
                VStack(spacing: JarvisSpacing.lg) {
                    Text("JARVIS")
                        .font(.custom("CormorantGaramond-SemiBold", size: 30))
                        .tracking(4)
                        .foregroundColor(JarvisColor.highlight_blue)

                    JarvisHeroView(vm: vm, coreSize: 300)

                    JarvisTitleGreetingView()

                    JarvisWaveformStatusView(vm: vm)

                    QuickSuggestions(commands: QuickCommand.productionCases) { cmd in
                        Task { await vm.handleQuickCommand(cmd) }
                    }

                    VoiceInputBar(isListening: vm.isListening) { vm.toggleVoice() }

                    if let approval = vm.pendingApproval {
                        ApprovalCardView(vm: vm, action: approval)
                    }
                }
                .padding(JarvisSpacing.xl)
                .frame(maxWidth: .infinity)
            }

            // RIGHT zone — contextual (empty, no invented live data)
            VStack(spacing: JarvisSpacing.md) {
                Text("جارفس")
                    .font(.custom("IBMPlexSansArabic-Bold", size: 18))
                    .foregroundColor(JarvisColor.text_secondary)
                Spacer()
            }
            .frame(width: 240)
            .padding(JarvisSpacing.lg)
            .background(JarvisColor.bg_0.opacity(0.3))
        }
        .background(
            LinearGradient(colors: [JarvisColor.bg_0, JarvisColor.bg_1], startPoint: .top, endPoint: .bottom)
                .ignoresSafeArea()
        )
        .task { await vm.load() }
    }

    private var providerUnavailableCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("البيانات المباشرة غير متصلة", systemImage: "link.badge.plus")
                .font(.system(size: 14, weight: .semibold))
                .foregroundColor(JarvisColor.text_secondary)
            Text("لن يعرض جارفس حالة منزل أو أمان أو وسائط وهمية في وضع الإنتاج.")
                .font(.system(size: 12))
                .foregroundColor(JarvisColor.text_muted)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(JarvisSpacing.md)
        .background(
            RoundedRectangle(cornerRadius: JarvisRadius.control)
                .fill(JarvisColor.bg_1.opacity(0.45))
        )
        .accessibilityLabel("البيانات المباشرة غير متصلة")
    }

    private var macSidebar: some View {
        VStack(spacing: 6) {
            ForEach(["home", "devices", "car", "more"], id: \.self) { id in
                let (label, icon) = sideItem(id)
                Button {
                    selectedTab = id
                } label: {
                    HStack(spacing: JarvisSpacing.md) {
                        Image(systemName: icon)
                            .font(.system(size: 15))
                            .frame(width: 20)
                        Text(label)
                            .font(.system(size: 14))
                        Spacer()
                    }
                    .foregroundColor(selectedTab == id ? JarvisColor.highlight_blue : JarvisColor.text_muted)
                    .padding(.horizontal, JarvisSpacing.md)
                    .padding(.vertical, JarvisSpacing.sm)
                    .background(
                        RoundedRectangle(cornerRadius: JarvisRadius.control)
                            .fill(selectedTab == id ? JarvisColor.primary_blue.opacity(0.12) : .clear)
                    )
                }
                .buttonStyle(.plain)
                .accessibilityLabel(label)
            }
            Spacer()
        }
    }

    private func sideItem(_ id: String) -> (String, String) {
        switch id {
        case "home":    return ("الرئيسية", JarvisIconResolver.symbol(for: "nav.home"))
        case "devices": return ("الأجهزة", JarvisIconResolver.symbol(for: "nav.devices"))
        case "car":     return ("السيارة", JarvisIconResolver.symbol(for: "nav.car"))
        default:        return ("المزيد", JarvisIconResolver.symbol(for: "nav.more"))
        }
    }
}
#endif
