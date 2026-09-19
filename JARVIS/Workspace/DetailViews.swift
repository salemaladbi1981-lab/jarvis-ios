import SwiftUI

/// تفاصيل مهمة — الحالة الحقيقية + open conversation.
struct TaskDetailView: View {
    @StateObject private var vm: TaskDetailViewModel
    private let api: JarvisAPI
    let taskId: String

    init(api: JarvisAPI, taskId: String) {
        self.api = api
        self.taskId = taskId
        _vm = StateObject(wrappedValue: TaskDetailViewModel(api: api))
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if let t = vm.task {
                    HStack(spacing: 8) {
                        Image(systemName: "hammer")
                            .foregroundColor(JarvisColor.highlight_blue)
                        Text(t.prompt ?? "مهمة")
                            .font(.system(size: 17, weight: .semibold))
                            .foregroundColor(JarvisColor.text_primary)
                    }
                    HStack(spacing: 8) {
                        Text(stateLabel(t))
                            .font(.system(size: 13, weight: .semibold))
                            .foregroundColor(stateColor(t))
                        Text(t.taskId)
                            .font(.system(size: 11))
                            .foregroundColor(JarvisColor.text_muted)
                    }
                    if let err = t.lastError ?? t.error, !err.isEmpty {
                        Text("الخطأ: \(err)")
                            .font(.system(size: 13))
                            .foregroundColor(JarvisColor.danger)
                    }
                    if let conv = t.conversationId, !conv.isEmpty {
                        NavigationLink {
                            ConversationView(api: api, conversationId: conv)
                        } label: {
                            Label("فتح المحادثة", systemImage: "bubble.left.and.bubble.right")
                                .font(.system(size: 14, weight: .semibold))
                                .foregroundColor(JarvisColor.highlight_blue)
                        }
                    }
                } else if vm.loading {
                    ProgressView()
                } else {
                    Text("المهمة غير متاحة")
                        .foregroundColor(JarvisColor.text_muted)
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .navigationTitle("المهمة")
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
        .task { await vm.load(taskId) }
    }

    private func stateLabel(_ t: JarvisTask) -> String {
        switch (t.jobState ?? t.status ?? "").uppercased() {
        case "QUEUED": return "في الانتظار"
        case "RUNNING": return "قيد التنفيذ"
        case "SUCCEEDED", "READY": return "اكتملت"
        case "FAILED": return "فشلت"
        case "CANCELLED": return "أُلغيت"
        default: return t.status ?? "—"
        }
    }

    private func stateColor(_ t: JarvisTask) -> Color {
        switch (t.jobState ?? t.status ?? "").uppercased() {
        case "SUCCEEDED", "READY": return JarvisColor.success
        case "FAILED": return JarvisColor.danger
        case "RUNNING", "QUEUED": return JarvisColor.warning_demo
        default: return JarvisColor.text_muted
        }
    }
}

@MainActor
final class TaskDetailViewModel: ObservableObject {
    @Published var task: JarvisTask?
    @Published var loading = false
    private let api: JarvisAPI
    init(api: JarvisAPI) { self.api = api }
    func load(_ id: String) async {
        loading = true
        defer { loading = false }
        do { task = try await api.getObject("tasks/\(id)") } catch { task = nil }
    }
}

/// تفاصيل تسليم — نوع + حجم + فتح المهمة المصدر.
struct DeliveryDetailView: View {
    @StateObject private var vm: DeliveryDetailViewModel
    private let api: JarvisAPI
    let deliveryId: String

    init(api: JarvisAPI, deliveryId: String) {
        self.api = api
        self.deliveryId = deliveryId
        _vm = StateObject(wrappedValue: DeliveryDetailViewModel(api: api))
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if let d = vm.delivery {
                    HStack(spacing: 8) {
                        Image(systemName: "doc.fill")
                            .foregroundColor(JarvisColor.highlight_blue)
                        Text(d.filename ?? "تسليم")
                            .font(.system(size: 17, weight: .semibold))
                            .foregroundColor(JarvisColor.text_primary)
                    }
                    Text("النوع: \(d.type ?? "—")")
                        .font(.system(size: 13))
                        .foregroundColor(JarvisColor.text_secondary)
                    if let task = d.taskId, !task.isEmpty {
                        NavigationLink {
                            TaskDetailView(api: api, taskId: task)
                        } label: {
                            Label("فتح المهمة المصدر", systemImage: "hammer")
                                .font(.system(size: 14, weight: .semibold))
                                .foregroundColor(JarvisColor.highlight_blue)
                        }
                    }
                } else if vm.loading {
                    ProgressView()
                } else {
                    Text("التسليم غير متاح")
                        .foregroundColor(JarvisColor.text_muted)
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .navigationTitle("التسليم")
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
        .task { await vm.load(deliveryId) }
    }
}

@MainActor
final class DeliveryDetailViewModel: ObservableObject {
    @Published var delivery: DeliveryItem?
    @Published var loading = false
    private let api: JarvisAPI
    init(api: JarvisAPI) { self.api = api }
    func load(_ id: String) async {
        loading = true
        defer { loading = false }
        do { delivery = try await api.getObject("deliveries/\(id)") } catch { delivery = nil }
    }
}
