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
    case permissionRequired(MacOperatorPermission)
    case ownerApprovalRequired
}

/// Fail-closed gate. Permission is checked before owner approval so the UI can request
/// the official macOS permission first; approval alone can never bypass OS permission.
/// Approval is request-bound and time-limited, so changing action/target after confirmation
/// forces a new owner decision instead of inheriting a stale boolean approval.
struct MacOperatorAuthorizationPolicy {
    func evaluate(
        _ request: MacOperatorRequest,
        grantedPermissions: Set<MacOperatorPermission>,
        ownerApproval: MacOperatorApprovalGrant?,
        now: Date = Date()
    ) -> MacOperatorAuthorizationDecision {
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
