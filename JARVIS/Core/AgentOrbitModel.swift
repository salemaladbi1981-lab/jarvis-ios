import Foundation
import Combine

/// Agent orbit activity — prototype (single + handoff + 3 agents).
/// Real events only: activate/deactivate/handoff تُستدعى من runtime (لا timers وهمية).
struct AgentOrbitItem: Identifiable, Equatable {
    let id: String          // canonical agent ID (من AGENT-REGISTRY.json)
    let name: String
    let group: String
    var position: Double = 0   // angle rad (يُعاد توزيعه عند layout)
}

@MainActor
final class AgentOrbitModel: ObservableObject {
    @Published private(set) var items: [AgentOrbitItem] = []
    @Published var handoffArc: (from: String, to: String)? = nil
    private var arcClearTask: Task<Void, Never>?

    func activate(_ agentID: String, name: String, group: String) {
        if let idx = items.firstIndex(where: { $0.id == agentID }) {
            items[idx] = AgentOrbitItem(id: agentID, name: name, group: group,
                                        position: items[idx].position)
        } else {
            items.append(AgentOrbitItem(id: agentID, name: name, group: group))
        }
        relayout()
    }

    func deactivate(_ agentID: String) {
        items.removeAll { $0.id == agentID }
        relayout()
    }

    func handoff(from: String, to: String) {
        handoffArc = (from, to)
        arcClearTask?.cancel()
        arcClearTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: UInt64(MotionTokens.Duration.handoff * 1_000_000_000))
            if !Task.isCancelled { self?.handoffArc = nil }
        }
    }

    private func relayout() {
        let count = max(items.count, 1)
        for i in items.indices {
            items[i].position = -Double.pi / 2 + Double(i) * 2 * Double.pi / Double(count)
        }
    }
}
