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
                .fill(JarvisColor.primary_gold)
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
                .foregroundColor(JarvisColor.primary_gold)
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
                .fill(JarvisColor.primary_gold.opacity(0.10))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .stroke(JarvisColor.primary_gold.opacity(0.45), lineWidth: 1)
        )
        .shadow(color: JarvisColor.primary_gold.opacity(0.25), radius: 10, x: 0, y: 0)
    }
}


/// Prominent microphone control (Concept 2) — زر مايك بارز تحت النواة.
/// يعكس الحالة الحقيقية (state/isListening) ولا يحرّك أي شيء من تلقاء نفسه؛
/// الضغط يدوي فقط: toggleVoice() → مقاطعة أثناء الكلام، أو بدء/إيقاف الاستماع.
struct JarvisMicControl: View {
    @ObservedObject var vm: HomeViewModel

    var body: some View {
        VStack(spacing: 8) {
            Button(action: { vm.toggleVoice() }) {
                ZStack {
                    Circle()
                        .fill(coreColor.opacity(0.14))
                        .frame(width: 96, height: 96)
                    Circle()
                        .fill(coreColor.opacity(0.30))
                        .frame(width: 74, height: 74)
                    Image(systemName: iconName)
                        .font(.system(size: 30, weight: .medium))
                        .foregroundColor(.white)
                }
                .shadow(color: coreColor.opacity(isActive ? 0.55 : 0.20), radius: isActive ? 24 : 10, x: 0, y: 0)
                .overlay(Circle().stroke(coreColor.opacity(isActive ? 0.6 : 0.28), lineWidth: 1.5))
            }
            .buttonStyle(.plain)
            .accessibilityLabel(micLabel)

            Text(micLabel)
                .font(.system(size: 13, weight: .medium))
                .foregroundColor(JarvisColor.text_secondary)
        }
        .frame(maxWidth: .infinity)
    }

    private var iconName: String {
        switch vm.state {
        case .listening, .speaking: return JarvisIconResolver.symbol(for: "util.waveform")
        case .thinking: return "ellipsis"
        case .executing: return "gearshape.2.fill"
        case .alert: return "exclamationmark.triangle.fill"
        case .approval: return "hand.raised.fill"
        default: return JarvisIconResolver.symbol(for: "util.mic")
        }
    }

    private var micLabel: String {
        switch vm.state {
        case .idle: return "اضغط للتحدث"
        case .listening: return "أنا أسمعك…"
        case .thinking: return "أفكر…"
        case .speaking: return "اضغط للمقاطعة"
        case .executing: return "أُنفّذ…"
        case .alert: return "حدث خطأ"
        case .approval: return "بانتظار موافقتك"
        }
    }

    private var coreColor: Color {
        switch vm.state {
        case .listening, .speaking, .thinking: return JarvisColor.primary_gold
        case .executing: return JarvisColor.success
        case .alert: return JarvisColor.danger
        case .approval: return JarvisColor.warning_demo
        default: return JarvisColor.primary_gold
        }
    }

    private var isActive: Bool { vm.state != .idle }
}
