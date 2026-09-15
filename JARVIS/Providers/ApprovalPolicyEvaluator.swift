import Foundation

/// Resolves whether an action requires owner approval, using ONLY the
/// action-specific approval_policy from AGENT-REGISTRY.json. No hard-coded
/// action rules live in any view.
struct ApprovalPolicyEvaluator {
    let registry: AgentRegistry

    /// - Parameters:
    ///   - agentID: stable registry id (e.g. "core_home")
    ///   - action:  action id (e.g. "unlock-door")
    /// - Returns: true if the action is in that agent's required_actions.
    func requiresApproval(agentID: String, action: String) -> Bool {
        guard let agent = registry.agents.first(where: { $0.id == agentID }) else {
            // fail-safe: unknown agent/action → require approval
            return true
        }
        return agent.approvalPolicy.requiresApproval(for: action)
    }
}
