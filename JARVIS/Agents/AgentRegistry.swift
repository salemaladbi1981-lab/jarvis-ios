//
//  AgentRegistry.swift — loads SharedSpecs/AGENT-REGISTRY.json
//  Single source of truth for agent labels/groups. Do not hard-code labels in views.
//
import Foundation

public struct ApprovalPolicy: Codable, Equatable {
    public let `default`: String
    public let requiredActions: [String]

    enum CodingKeys: String, CodingKey {
        case `default` = "default"
        case requiredActions = "required_actions"
    }

    public func requiresApproval(for action: String) -> Bool {
        requiredActions.contains(action)
    }
}

public struct Agent: Codable, Identifiable, Equatable {
    public let id: String
    public let name: String
    public let group: String
    public let role: String
    public let capabilities: [String]
    public let risk: String
    public let position: Int
    public let activeVisual: String
    public let inactiveVisual: String
    public let orbitStrategy: String
    public let approvalPolicy: ApprovalPolicy

    enum CodingKeys: String, CodingKey {
        case id, name, group, role, capabilities, risk, position
        case activeVisual = "active_visual"
        case inactiveVisual = "inactive_visual"
        case orbitStrategy = "orbit_strategy"
        case approvalPolicy = "approval_policy"
    }
}

public struct AgentGroup: Codable {
    public let label: String
    public let nodeCount: Int
    public let `default`: Bool?

    enum CodingKeys: String, CodingKey {
        case label
        case nodeCount = "node_count"
        case `default`
    }
}

public struct AgentRegistry: Codable {
    public let groups: [String: AgentGroup]
    public let agents: [Agent]

    public static func load(from url: URL? = nil) throws -> AgentRegistry {
        let u = url ?? Bundle.main.url(forResource: "AGENT-REGISTRY", withExtension: "json")!
        let data = try Data(contentsOf: u)
        let decoder = JSONDecoder()
        return try decoder.decode(AgentRegistry.self, from: data)
    }

    public func agents(in group: String) -> [Agent] {
        agents.filter { $0.group == group }.sorted { $0.position < $1.position }
    }

    public var defaultGroup: String {
        groups.first(where: { $0.value.default == true })?.key ?? "core"
    }

    public var allGroupKeys: [String] {
        ["core", "system", "content"]
    }
}
