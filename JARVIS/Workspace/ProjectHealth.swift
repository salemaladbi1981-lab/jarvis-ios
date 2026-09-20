import Foundation

struct ProjectHealth: Codable {
    let ok: Bool?
    let phase: String?
    let currentMilestone: String?
    let nextMilestone: String?
    let buildSha: String?
    let ciStatus: String?
    let testsStatus: String?
    let provider: String?
    let killSwitch: Bool?
    let workspaceId: String?
    let tasksTotal: Int?
    let tasksActive: Int?
    let tasksFailed: Int?
    let pendingApprovals: Int?
    let ownerActions: Int?
    let capabilityCount: Int?
    let blockers: Int?

    var ciDisplay: String {
        switch (ciStatus ?? "unknown").lowercased() {
        case "success", "passed", "green": return "CI أخضر"
        case "failed", "failure", "red": return "CI فاشل"
        case "running", "in_progress": return "CI يعمل"
        default: return "CI غير متاح"
        }
    }

    var testsDisplay: String {
        switch (testsStatus ?? "unknown").lowercased() {
        case "success", "passed", "green": return "الاختبارات ناجحة"
        case "failed", "failure", "red": return "الاختبارات فاشلة"
        case "running", "in_progress": return "الاختبارات تعمل"
        default: return "حالة الاختبارات غير متاحة"
        }
    }
}
