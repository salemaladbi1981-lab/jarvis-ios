import Foundation

/// Tool Foundation — abstraction خفيفة تفصل: intent / execution / result / confirmation / error.
/// قابلة للتوسّع بـ Web/Search ثم Files لاحقاً دون تضخيم HomeViewModel.

enum ToolIntent: Equatable {
    case emailSummary
    case emailSearch(query: String)
    case emailRead
    case emailReply(body: String)
    case none
}

/// متطلب التأكيد قبل التنفيذ.
enum ConfirmationRequirement: Equatable {
    case none                        // قراءة فقط / آمن
    case confirm(description: String) // يحتاج موافقة المالك (تُعرض الوصف)
}

/// نتيجة تنفيذ أداة — نجاح صادق أو فشل صادق.
enum ToolResult: Equatable {
    case success(message: String)
    case failure(reason: String)
}

/// أي أداة: تكتشف intent، تعلن متطلب التأكيد، تنفّذ.
protocol Tool: AnyObject {
    func detectIntent(from transcript: String) -> ToolIntent
    func confirmation(for intent: ToolIntent) -> ConfirmationRequirement
    func execute(_ intent: ToolIntent) async -> ToolResult
}
