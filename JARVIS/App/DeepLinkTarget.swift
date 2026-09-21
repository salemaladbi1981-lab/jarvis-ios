import Foundation

/// deep-link canonical: jarvis://conversation|task|delivery/{id}.
/// Foundation خالصة (قابلة للاختبار في target الاختبار macOS مباشرة).
enum DeepLinkTarget: Equatable {
    case conversation(String)
    case task(String)
    case delivery(String)

    /// الشكل القانوني للـ deep link — يُخزَّن في userInfo إشعار ويُستخدم للفتح المباشر.
    var url: String {
        switch self {
        case .conversation(let id): return "jarvis://conversation/\(id)"
        case .task(let id): return "jarvis://task/\(id)"
        case .delivery(let id): return "jarvis://delivery/\(id)"
        }
    }

    static func parse(_ url: URL) -> DeepLinkTarget? {
        guard url.scheme?.lowercased() == "jarvis" else { return nil }
        // jarvis://conversation/{id} → host = type, path = id
        let host = url.host?.lowercased()
        let id = url.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        guard !id.isEmpty else { return nil }
        switch host {
        case "conversation": return .conversation(id)
        case "task": return .task(id)
        case "delivery": return .delivery(id)
        default: return nil
        }
    }
}

// MARK: - Mac Operator foundation

/// Foundation-only authorization seam for future macOS local actions.
/// This file deliberately performs no Process/AppleScript/Accessibility execution.
/// Platform adapters must first pass this policy and then use an explicitly configured executor.
enum MacOperatorAction: String, Equatable, Hashable {
    /// Read metadata only for a file/folder explicitly selected by the user.
    case inspectSelectedItemMetadata
    /// Reveal a user-selected item in Finder. Visible local side effect.
    case revealSelectedItemInFinder
    /// Future Accessibility-framework interaction. Never executed by this foundation.
    case accessibilityInteraction
    /// Future Apple Events automation. Never executed by this foundation.
    case appleEventAutomation

    var requiredPermission: MacOperatorPermission {
        switch self {
        case .inspectSelectedItemMetadata, .revealSelectedItemInFinder:
            return .userSelectedFiles
        case .accessibilityInteraction:
            return .accessibility
        case .appleEventAutomation:
            return .automation
        }
    }

    var requiresOwnerApproval: Bool {
        switch self {
        case .inspectSelectedItemMetadata:
            return false
        case .revealSelectedItemInFinder, .accessibilityInteraction, .appleEventAutomation:
            return true
        }
    }
}

enum MacOperatorPermission: String, Equatable, Hashable {
    case userSelectedFiles
    case accessibility
    case automation
}

struct MacOperatorRequest: Equatable {
    let action: MacOperatorAction
    let target: String
}

/// Validates target shape before any permission prompt or owner-approval flow.
/// This does not grant filesystem/app access; it only rejects malformed or ambiguous targets
/// so a future adapter never receives relative paths, traversal segments, control characters,
/// or arbitrary command-shaped automation destinations through this foundation seam.
struct MacOperatorTargetPolicy {
    private let maxTargetUTF8Bytes = 1_024

    func isValid(_ request: MacOperatorRequest) -> Bool {
        let target = request.target
        guard !target.isEmpty,
              target.utf8.count <= maxTargetUTF8Bytes,
              target.rangeOfCharacter(from: .controlCharacters) == nil else {
            return false
        }

        switch request.action {
        case .inspectSelectedItemMetadata, .revealSelectedItemInFinder:
            return isAbsoluteUserSelectedPath(target)
        case .accessibilityInteraction:
            return target == "frontmost-app" || isBundleIdentifier(target)
        case .appleEventAutomation:
            return isBundleIdentifier(target)
        }
    }

    private func isAbsoluteUserSelectedPath(_ target: String) -> Bool {
        guard target.hasPrefix("/"), target != "/" else { return false }
        let components = target.split(separator: "/", omittingEmptySubsequences: false)
        return !components.contains(where: { $0 == ".." })
    }

    private func isBundleIdentifier(_ target: String) -> Bool {
        let parts = target.split(separator: ".", omittingEmptySubsequences: false)
        guard parts.count >= 2, !parts.contains(where: { $0.isEmpty }) else { return false }

        let allowed = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "-"))
        return parts.allSatisfy { part in
            part.unicodeScalars.allSatisfy { allowed.contains($0) }
        }
    }
}

/// Owner approval is bound to the exact action + target, uniquely identified, and expires quickly.
/// This prevents a confirmation for one Finder/app target from being reused for a different local
/// action. The unique id also lets the execution gate reject replay of the same approval.
/// This is policy state only; no platform capability is granted here.
struct MacOperatorApprovalGrant: Equatable {
    let id: UUID
    let request: MacOperatorRequest
    let expiresAt: Date

    init(id: UUID = UUID(), request: MacOperatorRequest, expiresAt: Date) {
        self.id = id
        self.request = request
        self.expiresAt = expiresAt
    }

    func authorizes(_ request: MacOperatorRequest, now: Date) -> Bool {
        self.request == request && now < expiresAt
    }
}

enum MacOperatorAuthorizationDecision: Equatable {
    case allowed
    case invalidTarget
    case permissionRequired(MacOperatorPermission)
    case ownerApprovalRequired
}

/// Fail-closed gate. Target shape is validated before prompting for platform permission,
/// then the official macOS permission is checked before owner approval. Approval alone can
/// never bypass either validation or OS permission. Approval is request-bound and time-limited,
/// so changing action/target after confirmation forces a new owner decision.
struct MacOperatorAuthorizationPolicy {
    private let targetPolicy = MacOperatorTargetPolicy()

    func evaluate(
        _ request: MacOperatorRequest,
        grantedPermissions: Set<MacOperatorPermission>,
        ownerApproval: MacOperatorApprovalGrant?,
        now: Date = Date()
    ) -> MacOperatorAuthorizationDecision {
        guard targetPolicy.isValid(request) else {
            return .invalidTarget
        }

        let permission = request.action.requiredPermission
        guard grantedPermissions.contains(permission) else {
            return .permissionRequired(permission)
        }
        if request.action.requiresOwnerApproval {
            guard let ownerApproval, ownerApproval.authorizes(request, now: now) else {
                return .ownerApprovalRequired
            }
        }
        return .allowed
    }
}

/// Opaque authorization passed to an executor only after policy evaluation succeeds.
/// The initializer is file-private so production code cannot manufacture an execution token
/// without going through MacOperatorExecutionGate.
struct MacOperatorExecutionAuthorization: Equatable {
    let request: MacOperatorRequest
    let approvalGrantID: UUID?

    fileprivate init(request: MacOperatorRequest, approvalGrantID: UUID?) {
        self.request = request
        self.approvalGrantID = approvalGrantID
    }
}

enum MacOperatorExecutionGateResult: Equatable {
    case authorized(MacOperatorExecutionAuthorization)
    case blocked(MacOperatorAuthorizationDecision)
}

/// Actor-backed execution gate. Approval-required actions consume their exact approval once.
/// Serialization prevents two concurrent execution attempts from replaying the same grant.
/// Read-only actions that require no owner approval remain reusable after their OS permission passes.
actor MacOperatorExecutionGate {
    private let policy = MacOperatorAuthorizationPolicy()
    private var consumedApprovalIDs: Set<UUID> = []

    func authorize(
        _ request: MacOperatorRequest,
        grantedPermissions: Set<MacOperatorPermission>,
        ownerApproval: MacOperatorApprovalGrant?,
        now: Date = Date()
    ) -> MacOperatorExecutionGateResult {
        let decision = policy.evaluate(
            request,
            grantedPermissions: grantedPermissions,
            ownerApproval: ownerApproval,
            now: now
        )
        guard decision == .allowed else {
            return .blocked(decision)
        }

        guard request.action.requiresOwnerApproval else {
            return .authorized(
                MacOperatorExecutionAuthorization(request: request, approvalGrantID: nil)
            )
        }

        guard let ownerApproval else {
            return .blocked(.ownerApprovalRequired)
        }
        guard !consumedApprovalIDs.contains(ownerApproval.id) else {
            return .blocked(.ownerApprovalRequired)
        }

        consumedApprovalIDs.insert(ownerApproval.id)
        return .authorized(
            MacOperatorExecutionAuthorization(request: request, approvalGrantID: ownerApproval.id)
        )
    }
}

enum MacOperatorExecutionResult: Equatable {
    case completed
    case blocked(String)
}

/// Safe execution seam for a future macOS adapter. Executors receive an authorization token,
/// not a raw request. There is intentionally no concrete privileged executor here; production
/// remains blocked until an authorized platform adapter is wired and reviewed.
protocol MacOperatorExecuting {
    func execute(_ authorization: MacOperatorExecutionAuthorization) async -> MacOperatorExecutionResult
}

/// Production-safe default: authorization still does not grant any concrete Mac control.
struct DisabledMacOperatorExecutor: MacOperatorExecuting {
    func execute(_ authorization: MacOperatorExecutionAuthorization) async -> MacOperatorExecutionResult {
        .blocked("mac_operator_executor_not_configured")
    }
}

/// Permission state is obtained by the service rather than accepted as caller-supplied truth.
/// A future macOS adapter can implement this protocol with official system APIs only.
protocol MacOperatorPermissionProviding {
    func grantedPermissions(for request: MacOperatorRequest) async -> Set<MacOperatorPermission>
}

/// Production-safe default: no local permission is assumed until an official platform adapter
/// explicitly verifies it. This keeps the service fail-closed even if a caller supplies approval.
struct DisabledMacOperatorPermissionProvider: MacOperatorPermissionProviding {
    func grantedPermissions(for request: MacOperatorRequest) async -> Set<MacOperatorPermission> {
        []
    }
}

/// Public operation result keeps authorization failures distinct from executor outcomes.
/// A caller can render a permission/approval request without accidentally invoking a local adapter.
enum MacOperatorOperationResult: Equatable {
    case authorizationBlocked(MacOperatorAuthorizationDecision)
    case execution(MacOperatorExecutionResult)
}

/// Single safe orchestration seam for future Mac Operator call sites.
/// Every execution must obtain verified permission state, then pass target validation and (where
/// required) a request-bound one-shot owner approval before an executor can be invoked. Both the
/// default permission provider and default executor are fail-closed, so adding this service does
/// not grant any local-control capability by itself.
actor MacOperatorService {
    private let gate: MacOperatorExecutionGate
    private let permissionProvider: any MacOperatorPermissionProviding
    private let executor: any MacOperatorExecuting

    init(
        gate: MacOperatorExecutionGate = MacOperatorExecutionGate(),
        permissionProvider: any MacOperatorPermissionProviding = DisabledMacOperatorPermissionProvider(),
        executor: any MacOperatorExecuting = DisabledMacOperatorExecutor()
    ) {
        self.gate = gate
        self.permissionProvider = permissionProvider
        self.executor = executor
    }

    func perform(
        _ request: MacOperatorRequest,
        ownerApproval: MacOperatorApprovalGrant?,
        now: Date = Date()
    ) async -> MacOperatorOperationResult {
        let grantedPermissions = await permissionProvider.grantedPermissions(for: request)
        let gateResult = await gate.authorize(
            request,
            grantedPermissions: grantedPermissions,
            ownerApproval: ownerApproval,
            now: now
        )

        switch gateResult {
        case .blocked(let decision):
            return .authorizationBlocked(decision)
        case .authorized(let authorization):
            return .execution(await executor.execute(authorization))
        }
    }
}
