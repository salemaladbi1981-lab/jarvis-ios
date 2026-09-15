import SwiftUI

/// Agent orbit: one group visible around the core at a time.
struct JarvisOrbitView: View {
    let agents: [Agent]
    var coreSize: CGFloat = 250
    var activeAgentID: String?
    var onTapAgent: (Agent) -> Void = { _ in }

    var body: some View {
        GeometryReader { geo in
            let center = CGPoint(x: geo.size.width / 2, y: geo.size.height / 2)
            let radius = min(geo.size.width, geo.size.height) / 2 - 26
            ZStack {
                ForEach(Array(agents.enumerated()), id: \.element.id) { idx, agent in
                    let angle = angleFor(idx, count: agents.count)
                    let pos = CGPoint(
                        x: center.x + cos(angle) * radius,
                        y: center.y + sin(angle) * radius
                    )
                    AgentChip(agent: agent, isActive: agent.id == activeAgentID)
                        .position(pos)
                        .onTapGesture { onTapAgent(agent) }
                }
            }
            .frame(width: geo.size.width, height: geo.size.height)
        }
    }

    private func angleFor(_ idx: Int, count: Int) -> Double {
        -Double.pi / 2 + Double(idx) * 2 * Double.pi / Double(count)
    }
}

struct AgentChip: View {
    let agent: Agent
    var isActive: Bool = false

    var body: some View {
        Text(agent.name)
            .font(.system(size: 13, weight: isActive ? .bold : .regular))
            .foregroundColor(isActive ? JarvisColor.highlight_blue : JarvisColor.text_muted)
            .padding(.horizontal, JarvisSpacing.md)
            .padding(.vertical, 6)
            .background(Capsule().fill(JarvisColor.bg_0.opacity(isActive ? 0.92 : 0.85)))
            .overlay(Capsule().stroke(isActive ? JarvisColor.highlight_blue : JarvisColor.primary_blue.opacity(0.4), lineWidth: 1))
            .shadow(color: isActive ? JarvisColor.primary_blue.opacity(0.35) : .clear, radius: isActive ? 8 : 0)
            .fixedSize()
            .accessibilityLabel("إيجنت \(agent.name)")
    }
}
