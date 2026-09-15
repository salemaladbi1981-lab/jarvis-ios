import SwiftUI

/// Shared Hero (Core + Orbit + group-swipe) — reused by iPhone and iPad layouts.
struct JarvisHeroView: View {
    @ObservedObject var vm: HomeViewModel
    var coreSize: CGFloat = 250

    var body: some View {
        ZStack {
            JarvisCoreView(state: vm.state, size: coreSize)
            JarvisOrbitView(
                agents: vm.agents(in: vm.activeGroup),
                coreSize: coreSize,
                activeAgentID: vm.state == .executing ? vm.agents(in: vm.activeGroup).first?.id : nil
            )
        }
        .frame(maxWidth: .infinity)
        .frame(height: coreSize * 1.28)
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
}

/// Shared title + greeting.
struct JarvisTitleGreetingView: View {
    var body: some View {
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
}

/// Shared waveform + status line.
struct JarvisWaveformStatusView: View {
    @ObservedObject var vm: HomeViewModel

    var body: some View {
        VStack(spacing: 4) {
            WaveformView(state: vm.state)
            statusLine
        }
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
}
