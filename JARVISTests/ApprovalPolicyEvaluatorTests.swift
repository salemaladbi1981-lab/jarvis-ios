import XCTest
@testable import JARVIS

final class ApprovalPolicyEvaluatorTests: XCTestCase {
    private var evaluator: ApprovalPolicyEvaluator!

    override func setUpWithError() throws {
        let registry = try AgentRegistry.load()
        evaluator = ApprovalPolicyEvaluator(registry: registry)
    }

    func testHomeUnlockDoorRequiresApproval() {
        XCTAssertTrue(evaluator.requiresApproval(agentID: "core_home", action: "unlock-door"))
    }
    func testHomeReadTemperatureNoApproval() {
        XCTAssertFalse(evaluator.requiresApproval(agentID: "core_home", action: "read-temperature"))
    }
    func testGuardianDisableCameraRequiresApproval() {
        XCTAssertTrue(evaluator.requiresApproval(agentID: "core_guardian", action: "disable-camera"))
    }
    func testDealmakerFinancialCommitmentRequiresApproval() {
        XCTAssertTrue(evaluator.requiresApproval(agentID: "core_dealmaker", action: "financial-commitment"))
    }
    func testServerDestructiveConfigRequiresApproval() {
        XCTAssertTrue(evaluator.requiresApproval(agentID: "sys_server", action: "destructive-config"))
    }
    func testUnknownAgentFailsSafe() {
        XCTAssertTrue(evaluator.requiresApproval(agentID: "unknown", action: "anything"))
    }
}
