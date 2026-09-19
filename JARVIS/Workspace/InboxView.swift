import SwiftUI

/// Inbox — الأشياء التي تحتاج انتباه المستخدم (موافقات/فشل/اكتمال/تسليم/إجراء).
/// كل عنصر يفتح العنصر الحقيقي المرتبط به.
struct InboxView: View {
    @StateObject private var vm: InboxViewModel
    private let api: JarvisAPI

    init(api: JarvisAPI) {
        self.api = api
        _vm = StateObject(wrappedValue: InboxViewModel(api: api))
    }

    var body: some View {
        NavigationStack {
            Group {
                if vm.loading {
                    ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if vm.items.isEmpty {
                    VStack(spacing: 8) {
                        Image(systemName: "tray")
                            .font(.system(size: 34))
                            .foregroundColor(JarvisColor.text_muted)
                        Text("لا شيء يحتاج انتباهك الآن")
                            .foregroundColor(JarvisColor.text_muted)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    List(vm.items) { item in
                        NavigationLink(value: item) {
                            InboxRow(item: item)
                        }
                    }
                    .listStyle(.plain)
                    .navigationDestination(for: InboxItem.self) { item in
                        destination(for: item)
                    }
                }
            }
            .navigationTitle("الوارد")
        }
        .task { await vm.load() }
    }

    @ViewBuilder
    private func destination(for item: InboxItem) -> some View {
        if let taskId = item.taskId {
            TaskDetailView(api: api, taskId: taskId)
        } else if let deliveryId = item.deliveryId {
            DeliveryDetailView(api: api, deliveryId: deliveryId)
        } else if let convId = item.conversationId {
            ConversationView(api: api, conversationId: convId)
        } else {
            Text("العنصر غير متاح").foregroundColor(JarvisColor.text_muted)
        }
    }
}

private struct InboxRow: View {
    let item: InboxItem
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: item.kind.systemImage)
                .font(.system(size: 16))
                .foregroundColor(color)
                .frame(width: 24)
            VStack(alignment: .leading, spacing: 3) {
                Text(item.title ?? item.kind.label)
                    .font(.system(size: 15, weight: .medium))
                    .foregroundColor(JarvisColor.text_primary)
                    .lineLimit(2)
                Text(item.kind.label)
                    .font(.system(size: 12))
                    .foregroundColor(color)
            }
            Spacer()
        }
        .padding(.vertical, 4)
    }

    private var color: Color {
        switch item.kind {
        case .approval, .action: return JarvisColor.warning_demo
        case .failed: return JarvisColor.danger
        case .completed, .delivery: return JarvisColor.success
        }
    }
}

@MainActor
final class InboxViewModel: ObservableObject {
    @Published var items: [InboxItem] = []
    @Published var loading = false
    private let api: JarvisAPI
    init(api: JarvisAPI) { self.api = api }

    func load() async {
        loading = true
        defer { loading = false }
        do {
            items = try await api.getArray("inbox")
        } catch {
            items = []
        }
    }
}
