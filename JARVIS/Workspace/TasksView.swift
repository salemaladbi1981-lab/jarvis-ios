import SwiftUI

/// شاشة المهام — حالة حقيقية من backend (job_state) + ربط بالمحادثة.
struct TasksView: View {
    @StateObject private var vm: TasksViewModel
    init(api: JarvisAPI) { _vm = StateObject(wrappedValue: TasksViewModel(api: api)) }

    var body: some View {
        NavigationStack {
            Group {
                if vm.loading {
                    ProgressView().tint(JarvisColor.highlight_blue)
                } else if vm.items.isEmpty {
                    Text("لا مهام بعد")
                        .font(.system(size: 15))
                        .foregroundColor(JarvisColor.text_muted)
                } else {
                    ScrollView {
                        LazyVStack(spacing: JarvisSpacing.md) {
                            ForEach(vm.items) { task in
                                TaskCard(task: task)
                            }
                        }
                        .padding(JarvisSpacing.lg)
                    }
                }
            }
            .navigationTitle("المهام")
        }
        .task { await vm.load() }
    }
}

private struct TaskCard: View {
    let task: TaskItem
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(task.prompt ?? "بدون عنوان")
                .font(.system(size: 15, weight: .semibold))
                .foregroundColor(JarvisColor.text_primary)
                .lineLimit(2)
            HStack(spacing: 8) {
                Text(statusLabel)
                    .font(.system(size: 12))
                    .foregroundColor(statusColor)
                    .padding(.horizontal, 10).padding(.vertical, 4)
                    .background(statusColor.opacity(0.12))
                    .clipShape(Capsule())
                if let err = task.lastError, !err.isEmpty {
                    Text(err).font(.system(size: 11)).foregroundColor(JarvisColor.danger).lineLimit(1)
                }
            }
        }
        .padding(JarvisSpacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(JarvisColor.card)
        .overlay(RoundedRectangle(cornerRadius: JarvisRadius.card).stroke(JarvisColor.border, lineWidth: 1))
        .clipShape(RoundedRectangle(cornerRadius: JarvisRadius.card))
    }

    private var state: String { (task.jobState ?? task.status ?? "").lowercased() }
    private var statusLabel: String {
        switch state {
        case "queued": return "بانتظار التنفيذ"
        case "running": return "قيد التنفيذ"
        case "succeeded", "ready", "complete": return "مكتمل"
        case "failed": return "فشل"
        case "cancelled": return "ملغى"
        default: return state.isEmpty ? "—" : state
        }
    }
    private var statusColor: Color {
        switch state {
        case "succeeded", "ready", "complete": return JarvisColor.success
        case "failed": return JarvisColor.danger
        case "running", "processing": return JarvisColor.warning_demo
        case "cancelled": return JarvisColor.text_muted
        default: return JarvisColor.text_muted
        }
    }
}

@MainActor
final class TasksViewModel: ObservableObject {
    @Published var items: [TaskItem] = []
    @Published var loading = false
    private let api: JarvisAPI
    init(api: JarvisAPI) { self.api = api }
    func load() async {
        loading = true
        defer { loading = false }
        do {
            items = try await api.getArray("tasks")
        } catch {
            items = []
        }
    }
}
