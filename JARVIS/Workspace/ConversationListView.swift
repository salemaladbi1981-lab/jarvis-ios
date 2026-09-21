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
            ZStack {
                JarvisColor.bg_0.ignoresSafeArea()

                Group {
                    if vm.conversations.isEmpty {
                        emptyState
                    } else {
                        ScrollView {
                            LazyVStack(spacing: JarvisSpacing.sm) {
                                ForEach(vm.conversations) { conversation in
                                    NavigationLink(value: conversation.id) {
                                        ConversationGoldCard(conversation: conversation)
                                    }
                                    .buttonStyle(.plain)
                                }
                            }
                            .padding(.horizontal, JarvisSpacing.lg)
                            .padding(.vertical, JarvisSpacing.md)
                        }
                    }
                }
            }
            .navigationTitle("المحادثات")
            .navigationDestination(for: String.self) { id in
                ConversationView(api: api, conversationId: id)
            }
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button { Task { await vm.newConversation() } } label: {
                        Image(systemName: "square.and.pencil")
                            .foregroundColor(JarvisColor.highlight_gold)
                    }
                    .accessibilityLabel("بدء محادثة")
                }
            }
            .task { await vm.load() }
        }
        .tint(JarvisColor.highlight_gold)
    }

    private var emptyState: some View {
        VStack(spacing: JarvisSpacing.md) {
            Image(systemName: "message.badge.plus")
                .font(.system(size: 28, weight: .medium))
                .foregroundColor(JarvisColor.primary_gold)

            Text("لا محادثات بعد")
                .font(.system(size: 17, weight: .semibold))
                .foregroundColor(JarvisColor.text_primary)

            Text("ابدأ محادثة جديدة مع جارفس")
                .font(.system(size: 13))
                .foregroundColor(JarvisColor.text_muted)

            Button {
                Task { await vm.newConversation() }
            } label: {
                Label("بدء محادثة", systemImage: "square.and.pencil")
            }
            .buttonStyle(.borderedProminent)
            .tint(JarvisColor.highlight_gold)
        }
        .padding(JarvisSpacing.xl)
        .frame(maxWidth: 420)
        .background(JarvisColor.card)
        .overlay(
            RoundedRectangle(cornerRadius: JarvisRadius.card)
                .stroke(JarvisColor.primary_gold.opacity(0.18), lineWidth: 1)
        )
        .shadow(color: JarvisColor.primary_gold.opacity(0.05), radius: 14, y: 6)
        .clipShape(RoundedRectangle(cornerRadius: JarvisRadius.card))
        .padding(JarvisSpacing.lg)
    }
}

private struct ConversationGoldCard: View {
    let conversation: Conversation

    var body: some View {
        HStack(spacing: JarvisSpacing.md) {
            Image(systemName: "message.fill")
                .font(.system(size: 14, weight: .semibold))
                .foregroundColor(JarvisColor.primary_gold)
                .frame(width: 34, height: 34)
                .background(JarvisColor.primary_gold.opacity(0.10))
                .clipShape(Circle())

            VStack(alignment: .leading, spacing: 4) {
                Text(conversation.title ?? "محادثة")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundColor(JarvisColor.text_primary)
                    .lineLimit(2)

                if let source = conversation.source, !source.isEmpty {
                    Text(source)
                        .font(.system(size: 12))
                        .foregroundColor(JarvisColor.text_muted)
                        .lineLimit(1)
                }
            }

            Spacer(minLength: JarvisSpacing.sm)

            Image(systemName: "chevron.forward")
                .font(.system(size: 12, weight: .semibold))
                .foregroundColor(JarvisColor.highlight_gold.opacity(0.72))
        }
        .padding(JarvisSpacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(JarvisColor.card)
        .overlay(
            RoundedRectangle(cornerRadius: JarvisRadius.card)
                .stroke(JarvisColor.primary_gold.opacity(0.14), lineWidth: 1)
        )
        .shadow(color: JarvisColor.primary_gold.opacity(0.04), radius: 10, y: 4)
        .clipShape(RoundedRectangle(cornerRadius: JarvisRadius.card))
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
