import Foundation

/// فئات الذاكرة الست المعتمدة.
enum MemoryCategory: String, Codable, CaseIterable {
    case durableFact      // Durable Facts — معلومات طويلة الأجل ومؤكدة
    case preference       // Preferences — أسلوب التواصل وطريقة العمل
    case activeProject    // Active Projects — المرحلة/الهدف/blockers/next action
    case decision         // Decisions / Frozen Baselines — قرارات ملزمة
    case historical       // Historical Context — لا تُعامل كحالة حالية
    case session          // Temporary Session State — لا يتحول تلقائياً لذاكرة دائمة

    var arabicLabel: String {
        switch self {
        case .durableFact: return "حقائق دائمة"
        case .preference: return "تفضيلات"
        case .activeProject: return "مشاريع نشطة"
        case .decision: return "قرارات"
        case .historical: return "سياق تاريخي"
        case .session: return "حالة جلسة"
        }
    }
}

/// مصدر المعلومة — لا نرفع الاستنتاج غير المؤكد إلى حقيقة دائمة.
enum MemoryProvenance: String, Codable, CaseIterable {
    case ownerProvided    // قالها المالك صراحة
    case importedSeed     // من ملف seed مستورد
    case explicitDecision // قرار صريح ملزم
    case runtimeState     // project/engineering state

    /// سلطة المصدر: القرار الصريح > كلام المالك > seed مستورد > حالة تشغيل.
    var authority: Int {
        switch self {
        case .explicitDecision: return 4
        case .ownerProvided: return 3
        case .importedSeed: return 2
        case .runtimeState: return 1
        }
    }
}

struct MemoryItem: Codable, Identifiable, Equatable {
    let id: String
    var category: MemoryCategory
    var provenance: MemoryProvenance
    var content: String
    var keywords: [String]
    var priority: Int            // أعلى = أهم
    var updatedAtEpoch: Double   // epoch seconds
    var createdAtEpoch: Double
    var source: String?
    var isActive: Bool

    var updatedAt: Date { Date(timeIntervalSince1970: updatedAtEpoch) }
    var createdAt: Date { Date(timeIntervalSince1970: createdAtEpoch) }
}
