import Foundation
import Combine

/// Loads the agent registry from the bundled AGENT-REGISTRY.json.
/// Views never hard-code Arabic display names; they read from this store.
final class AgentStore: ObservableObject {
    @Published private(set) var registry: AgentRegistry?
    @Published var activeGroup: String = "core"

    init() {
        load()
    }

    func load() {
        guard let url = Bundle.main.url(forResource: "AGENT-REGISTRY", withExtension: "json") else {
            assertionFailure("AGENT-REGISTRY.json missing from bundle")
            return
        }
        registry = try? AgentRegistry.load(from: url)
    }

    func agents(in group: String) -> [Agent] {
        registry?.agents(in: group) ?? []
    }

    var allGroups: [String] {
        registry?.allGroupKeys ?? ["core", "system", "content"]
    }
}
