import SwiftUI

/// الشاشة الرئيسية — Chat يبقى المركز: بدء محادثة + المحادثات الأخيرة + مهام جارية + تسليمات أخيرة.
struct HomeEntryView: View {
    @StateObject private var vm: HomeEntryViewModel
    @State private var newConv: ConvID?
    private let api: JarvisAPI

    init(api: JarvisAPI) {
        self.api = api
        _vm = StateObject(wrappedValue: HomeEntryViewModel(api: api))
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // نقطة دخول واضحة لبدء محادثة جديدة
                    Button {
                        Task { await vm.newConversation() }
                    } label: {
                        HStack(spacing: 10) {
                            Image(systemName: "plus.bubble.fill")
                            Text("بدء محادثة جديدة")
                                .font(.system(size: 16, weight: .semibold))
                        }
                        .foregroundColor(JarvisColor.text_primary)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background(JarvisColor.bg_1)
                        .cornerRadius(14)
                    }

                    if !vm.conversations.isEmpty {
                        section("المحادثات الأخيرة") {
                            ForEach(vm.conversations.prefix(5)) { c in
                                NavigationLink {
                                    ConversationView(api: api, conversationId: c.id)
                                } label: {
                                    row(icon: "bubble.left", title: c.title ?? "محادثة",
                                        subtitle: c.source)
                                }
                            }
                        }
                    }

                    if !vm.activeTasks.isEmpty {
                        section("المهام الجارية") {
                            ForEach(vm.activeTasks.prefix(3)) { t in
                                NavigationLink {
                                    TaskDetailView(api: api, taskId: t.id)
                                } label: {
                                    row(icon: "hammer", title: t.prompt ?? "مهمة",
                                        subtitle: "قيد التنفيذ")
                                }
                            }
                        }
                    }

                    if !vm.deliveries.isEmpty {
                        section("التسليمات الأخيرة") {
                            ForEach(vm.deliveries.prefix(3)) { d in
                                NavigationLink {
                                    DeliveryDetailView(api: api, deliveryId: d.id)
                                } label: {
                                    row(icon: "doc", title: d.filename ?? "تسليم",
                                        subtitle: d.type)
                                }
                            }
                        }
                    }

                    if vm.conversations.isEmpty && vm.activeTasks.isEmpty && vm.deliveries.isEmpty {
                        VStack(spacing: 8) {
                            Image(systemName: "sparkles")
                                .font(.system(size: 30))
                                .foregroundColor(JarvisColor.text_muted)
                            Text("ابدأ محادثة مع جارفس")
                                .foregroundColor(JarvisColor.text_muted)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.top, 24)
                    }
                }
                .padding(16)
            }
            .navigationTitle("جارفس")
            .navigationDestination(item: $newConv) { c in
                ConversationView(api: api, conversationId: c.id)
            }
        }
        .task { await vm.load() }
        .onChange(of: vm.newConversationId) { id in
            if let id = id { newConv = ConvID(id: id) }
        }
    }

    private func section(_ title: String, @ViewBuilder content: () -> some View) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(JarvisColor.text_muted)
            VStack(spacing: 0) { content() }
        }
    }

    private func row(icon: String, title: String, subtitle: String?) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 15))
                .foregroundColor(JarvisColor.highlight_blue)
                .frame(width: 22)
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.system(size: 15))
                    .foregroundColor(JarvisColor.text_primary)
                    .lineLimit(1)
                if let s = subtitle, !s.isEmpty {
                    Text(s)
                        .font(.system(size: 12))
                        .foregroundColor(JarvisColor.text_muted)
                }
            }
            Spacer()
            Image(systemName: "chevron.left")
                .font(.system(size: 12))
                .foregroundColor(JarvisColor.text_muted)
        }
        .padding(.vertical, 10)
    }
}

@MainActor
final class HomeEntryViewModel: ObservableObject {
    @Published var conversations: [Conversation] = []
    @Published var activeTasks: [JarvisTask] = []
    @Published var deliveries: [DeliveryItem] = []
    @Published var newConversationId: String?
    private let api: JarvisAPI
    init(api: JarvisAPI) { self.api = api }

    func load() async {
        async let convs: [Conversation] = api.getArray("conversations")
        async let tasks: [JarvisTask] = api.getArray("tasks")
        async let dels: [DeliveryItem] = api.getArray("deliveries")
        do {
            let (c, t, d) = try await (convs, tasks, dels)
            conversations = c
            activeTasks = t.filter { ["QUEUED", "RUNNING"].contains(($0.jobState ?? $0.status ?? "").uppercased()) }
            deliveries = d
        } catch {
            conversations = []; activeTasks = []; deliveries = []
        }
    }

    func newConversation() async {
        do {
            let c: Conversation = try await api.postObject("conversations", body: [:])
            newConversationId = c.id
        } catch {}
    }
}

struct ConvID: Identifiable { let id: String }
