import XCTest

/// اختبار توجيه الإشعار/deep-link: parse + url round-trip + حالات الرفض.
final class DeepLinkRoutingTests: XCTestCase {

    func testParseConversation() {
        XCTAssertEqual(DeepLinkTarget.parse(URL(string: "jarvis://conversation/conv-123")!),
                       .conversation("conv-123"))
    }

    func testParseTask() {
        XCTAssertEqual(DeepLinkTarget.parse(URL(string: "jarvis://task/task-456")!),
                       .task("task-456"))
    }

    func testParseDelivery() {
        XCTAssertEqual(DeepLinkTarget.parse(URL(string: "jarvis://delivery/dlv-789")!),
                       .delivery("dlv-789"))
    }

    func testParseRejectsWrongScheme() {
        XCTAssertNil(DeepLinkTarget.parse(URL(string: "https://conversation/x")!))
    }

    func testParseRejectsUnknownHost() {
        XCTAssertNil(DeepLinkTarget.parse(URL(string: "jarvis://nope/x")!))
    }

    func testParseRejectsEmptyId() {
        XCTAssertNil(DeepLinkTarget.parse(URL(string: "jarvis://task/")!))
    }

    /// round-trip: target → url → parse → نفس الـ target (هوية الإشعار لا تتغير).
    func testUrlRoundTrip() {
        let cases: [DeepLinkTarget] = [
            .conversation("conv-abc"), .task("task-def"), .delivery("dlv-ghi")
        ]
        for target in cases {
            let parsed = DeepLinkTarget.parse(URL(string: target.url)!)
            XCTAssertEqual(parsed, target, "round-trip failed for \(target.url)")
        }
    }

    /// محاكاة userInfo إشعار: السلسلة المخزّنة تُفتح نفس العنصر.
    func testNotificationUserInfoRoundTrip() {
        // نفس ما يخزّنه NotificationManager في userInfo["jarvis_deep_link"]
        let stored = DeepLinkTarget.delivery("dlv-42").url
        let parsed = DeepLinkTarget.parse(URL(string: stored)!)
        XCTAssertEqual(parsed, .delivery("dlv-42"))
    }

    // MARK: Mac Operator foundation

    private let now = Date(timeIntervalSince1970: 1_800_000_000)

    private func grant(for request: MacOperatorRequest, ttl: TimeInterval = 120) -> MacOperatorApprovalGrant {
        MacOperatorApprovalGrant(request: request, expiresAt: now.addingTimeInterval(ttl))
    }

    func testMacOperatorReadOnlyMetadataRequiresUserSelectedFilePermission() {
        let policy = MacOperatorAuthorizationPolicy()
        let request = MacOperatorRequest(action: .inspectSelectedItemMetadata, target: "/selected/item")

        XCTAssertEqual(
            policy.evaluate(request, grantedPermissions: [], ownerApproval: nil, now: now),
            .permissionRequired(.userSelectedFiles)
        )
        XCTAssertEqual(
            policy.evaluate(request, grantedPermissions: [.userSelectedFiles], ownerApproval: nil, now: now),
            .allowed
        )
    }

    func testMacOperatorVisibleFinderActionRequiresBoundOwnerApproval() {
        let policy = MacOperatorAuthorizationPolicy()
        let request = MacOperatorRequest(action: .revealSelectedItemInFinder, target: "/selected/item")

        XCTAssertEqual(
            policy.evaluate(request, grantedPermissions: [.userSelectedFiles], ownerApproval: nil, now: now),
            .ownerApprovalRequired
        )
        XCTAssertEqual(
            policy.evaluate(request, grantedPermissions: [.userSelectedFiles], ownerApproval: grant(for: request), now: now),
            .allowed
        )
    }

    func testMacOperatorApprovalCannotBypassAccessibilityPermission() {
        let policy = MacOperatorAuthorizationPolicy()
        let request = MacOperatorRequest(action: .accessibilityInteraction, target: "frontmost-app")

        XCTAssertEqual(
            policy.evaluate(request, grantedPermissions: [], ownerApproval: grant(for: request), now: now),
            .permissionRequired(.accessibility)
        )
    }

    func testMacOperatorAccessibilityNeedsPermissionAndApproval() {
        let policy = MacOperatorAuthorizationPolicy()
        let request = MacOperatorRequest(action: .accessibilityInteraction, target: "frontmost-app")

        XCTAssertEqual(
            policy.evaluate(request, grantedPermissions: [.accessibility], ownerApproval: nil, now: now),
            .ownerApprovalRequired
        )
        XCTAssertEqual(
            policy.evaluate(request, grantedPermissions: [.accessibility], ownerApproval: grant(for: request), now: now),
            .allowed
        )
    }

    func testMacOperatorAutomationNeedsOfficialPermissionAndApproval() {
        let policy = MacOperatorAuthorizationPolicy()
        let request = MacOperatorRequest(action: .appleEventAutomation, target: "com.apple.Finder")

        XCTAssertEqual(
            policy.evaluate(request, grantedPermissions: [], ownerApproval: nil, now: now),
            .permissionRequired(.automation)
        )
        XCTAssertEqual(
            policy.evaluate(request, grantedPermissions: [.automation], ownerApproval: nil, now: now),
            .ownerApprovalRequired
        )
        XCTAssertEqual(
            policy.evaluate(request, grantedPermissions: [.automation], ownerApproval: grant(for: request), now: now),
            .allowed
        )
    }

    func testMacOperatorApprovalIsBoundToExactTarget() {
        let policy = MacOperatorAuthorizationPolicy()
        let approved = MacOperatorRequest(action: .revealSelectedItemInFinder, target: "/selected/item")
        let changedTarget = MacOperatorRequest(action: .revealSelectedItemInFinder, target: "/different/item")

        XCTAssertEqual(
            policy.evaluate(
                changedTarget,
                grantedPermissions: [.userSelectedFiles],
                ownerApproval: grant(for: approved),
                now: now
            ),
            .ownerApprovalRequired
        )
    }

    func testMacOperatorApprovalIsBoundToExactAction() {
        let policy = MacOperatorAuthorizationPolicy()
        let approved = MacOperatorRequest(action: .accessibilityInteraction, target: "frontmost-app")
        let changedAction = MacOperatorRequest(action: .appleEventAutomation, target: "frontmost-app")

        XCTAssertEqual(
            policy.evaluate(
                changedAction,
                grantedPermissions: [.automation],
                ownerApproval: grant(for: approved),
                now: now
            ),
            .ownerApprovalRequired
        )
    }

    func testMacOperatorExpiredApprovalFailsClosed() {
        let policy = MacOperatorAuthorizationPolicy()
        let request = MacOperatorRequest(action: .appleEventAutomation, target: "com.apple.Finder")
        let expired = MacOperatorApprovalGrant(request: request, expiresAt: now)

        XCTAssertEqual(
            policy.evaluate(
                request,
                grantedPermissions: [.automation],
                ownerApproval: expired,
                now: now
            ),
            .ownerApprovalRequired
        )
    }

    func testMacOperatorExecutionGateConsumesApprovalExactlyOnce() async {
        let gate = MacOperatorExecutionGate()
        let request = MacOperatorRequest(action: .revealSelectedItemInFinder, target: "/selected/item")
        let approval = grant(for: request)

        let first = await gate.authorize(
            request,
            grantedPermissions: [.userSelectedFiles],
            ownerApproval: approval,
            now: now
        )
        guard case .authorized(let authorization) = first else {
            return XCTFail("expected first authorization to succeed")
        }
        XCTAssertEqual(authorization.request, request)
        XCTAssertEqual(authorization.approvalGrantID, approval.id)

        let replay = await gate.authorize(
            request,
            grantedPermissions: [.userSelectedFiles],
            ownerApproval: approval,
            now: now
        )
        XCTAssertEqual(replay, .blocked(.ownerApprovalRequired))
    }

    func testMacOperatorExecutionGateRejectsConcurrentApprovalReplay() async {
        let gate = MacOperatorExecutionGate()
        let request = MacOperatorRequest(action: .appleEventAutomation, target: "com.apple.Finder")
        let approval = grant(for: request)

        async let first = gate.authorize(
            request,
            grantedPermissions: [.automation],
            ownerApproval: approval,
            now: now
        )
        async let second = gate.authorize(
            request,
            grantedPermissions: [.automation],
            ownerApproval: approval,
            now: now
        )
        let results = await [first, second]

        XCTAssertEqual(results.filter {
            if case .authorized = $0 { return true }
            return false
        }.count, 1)
        XCTAssertEqual(results.filter { $0 == .blocked(.ownerApprovalRequired) }.count, 1)
    }

    func testMacOperatorReadOnlyAuthorizationRemainsReusableAfterPermissionPasses() async {
        let gate = MacOperatorExecutionGate()
        let request = MacOperatorRequest(action: .inspectSelectedItemMetadata, target: "/selected/item")

        for _ in 0..<2 {
            let result = await gate.authorize(
                request,
                grantedPermissions: [.userSelectedFiles],
                ownerApproval: nil,
                now: now
            )
            guard case .authorized(let authorization) = result else {
                return XCTFail("expected read-only authorization to succeed")
            }
            XCTAssertEqual(authorization.request, request)
            XCTAssertNil(authorization.approvalGrantID)
        }
    }

    func testMacOperatorDefaultExecutorIsFailClosedAfterAuthorization() async {
        let gate = MacOperatorExecutionGate()
        let executor = DisabledMacOperatorExecutor()
        let request = MacOperatorRequest(action: .revealSelectedItemInFinder, target: "/selected/item")
        let approval = grant(for: request)
        let gated = await gate.authorize(
            request,
            grantedPermissions: [.userSelectedFiles],
            ownerApproval: approval,
            now: now
        )

        guard case .authorized(let authorization) = gated else {
            return XCTFail("expected authorization token")
        }
        let result = await executor.execute(authorization)
        XCTAssertEqual(result, .blocked("mac_operator_executor_not_configured"))
    }
}
