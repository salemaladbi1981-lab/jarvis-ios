import SwiftUI

/// قائمة المحادثات — نقطة دخول Chat + بدء محادثة جديدة.
struct ConversationListView: View {
    @StateObject private var vm: ConversationListViewModel
    private let api: JarvisAPI

    init(api: JarvisAPI) {
        self.api = api
        _vm = StateObject(wrappedValue: ConversationListViewModel(api: api))
    }

    var body: some View {
        NavigationStack {
            Group {
                if vm.conversations.isEmpty {
                    VStack(spacing: 12) {
                        Text("لا محادثات بعد")
                            .foregroundColor(JarvisColor.text_muted)
                        Button("بدء محادثة") { Task { await vm.newConversation() } }
                            .buttonStyle(.borderedProminent)
                            .tint(JarvisColor.highlight_blue)
                    }
                } else {
                    List {
                        ForEach(vm.conversations) { c in
                            NavigationLink(value: c.id) {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(c.title ?? "محادثة")
                                        .font(.system(size: 15, weight: .medium))
                                        .foregroundColor(JarvisColor.text_primary)
                                    Text(c.source ?? "")
                                        .font(.system(size: 12))
                                        .foregroundColor(JarvisColor.text_muted)
                                }
                            }
                        }
                    }
                    .listStyle(.plain)
                    .navigationDestination(for: String.self) { id in
                        ConversationView(api: api, conversationId: id)
                    }
                }
            }
            .navigationTitle("المحادثات")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button { Task { await vm.newConversation() } } label: {
                        Image(systemName: "square.and.pencil")
                    }
                }
            }
            .task { await vm.load() }
        }
    }
}

@MainActor
final class ConversationListViewModel: ObservableObject {
    @Published var conversations: [Conversation] = []
    @Published var activeConversationId: String?
    private let api: JarvisAPI
    init(api: JarvisAPI) { self.api = api }

    func load() async {
        do { conversations = try await api.getArray("conversations") } catch {}
    }

    func newConversation() async {
        do {
            let c: Conversation = try await api.postObject("conversations", body: [:])
            conversations.insert(c, at: 0)
            activeConversationId = c.id
        } catch {}
    }
}
