import SwiftUI

/// قائمة المحادثات — نقطة دخول Chat + بدء محادثة جديدة.
struct ConversationListView: View {
    @StateObject private var vm: ConversationListViewModel
    @State private var path: [String] = []
    private let api: JarvisAPI

    init(api: JarvisAPI) {
        self.api = api
        _vm = StateObject(wrappedValue: ConversationListViewModel(api: api))
    }

    var body: some View {
        NavigationStack(path: $path) {
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

                }
            }
            .navigationDestination(for: String.self) { id in
                ConversationView(api: api, conversationId: id)
            }
            .onChange(of: vm.activeConversationId) { _, id in
                if let id { path.append(id) }
            }
            .safeAreaInset(edge: .bottom) {
                if let error = vm.errorMessage {
                    Text(error).font(.caption).foregroundColor(JarvisColor.danger).padding()
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
            .disabled(vm.isCreating)
            .task { await vm.load() }
            .refreshable { await vm.load() }
        }
    }
}

@MainActor
final class ConversationListViewModel: ObservableObject {
    @Published var conversations: [Conversation] = []
    @Published var activeConversationId: String?
    @Published var errorMessage: String?
    @Published private(set) var isCreating = false
    private let api: JarvisAPI
    init(api: JarvisAPI) { self.api = api }

    func load() async {
        do {
            conversations = try await api.getArray("conversations")
            errorMessage = nil
        } catch { errorMessage = JarvisAPIError.message(for: error) }
    }

    func newConversation() async {
        guard !isCreating else { return }
        isCreating = true
        defer { isCreating = false }
        do {
            let envelope: ConversationEnvelope = try await api.postObject("conversations", body: ["create_new": true])
            let c = envelope.conversation
            errorMessage = nil
            conversations.insert(c, at: 0)
            activeConversationId = c.id
        } catch { errorMessage = JarvisAPIError.message(for: error) }
    }
}
