import SwiftUI

/// Shared Hero (Core + Orbit + group-swipe) — reused by iPhone and iPad layouts.
struct JarvisHeroView: View {
    @ObservedObject var vm: HomeViewModel
    var coreSize: CGFloat = 250

    var body: some View {
        VStack(spacing: 10) {
            if let active = vm.orbit.items.last {
                ActiveAgentBadge(agent: active)
            }
            ZStack {
                JarvisCoreView(
                    levels: vm.levels,
                    state: vm.state,
                    successPulse: vm.successPulse,
                    size: coreSize,
                    onFrameTime: { vm.frameTimeMs = $0 }
                )
                JarvisOrbitView(orbit: vm.orbit, coreSize: coreSize)
            }
            .frame(height: coreSize * 1.28)
        }
        .allowsHitTesting(false)
        .frame(maxWidth: .infinity)
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
            WaveformView(levels: vm.levels, state: vm.state)
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


/// Cinematic active-agent indicator — فوق النواة عند وجود agent نشط من الـ runtime.
private struct ActiveAgentBadge: View {
    let agent: AgentOrbitItem

    var body: some View {
        VStack(spacing: 3) {
            Text("ACTIVE AGENT")
                .font(.system(size: 9, weight: .bold))
                .kerning(2.5)
                .foregroundColor(JarvisColor.primary_blue)
            Text(agent.name)
                .font(.custom("IBMPlexSansArabic-Bold", size: 17))
                .foregroundColor(JarvisColor.text_primary)
            Text(agent.id)
                .font(.system(size: 10, weight: .medium, design: .monospaced))
                .foregroundColor(JarvisColor.text_muted)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(JarvisColor.primary_blue.opacity(0.10))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .stroke(JarvisColor.primary_blue.opacity(0.45), lineWidth: 1)
        )
        .shadow(color: JarvisColor.primary_blue.opacity(0.25), radius: 10, x: 0, y: 0)
    }
}
