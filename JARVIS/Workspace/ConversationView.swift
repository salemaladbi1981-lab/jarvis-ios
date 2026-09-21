import SwiftUI

/// شاشة المحادثة — رسائل + streaming + حالة + citations + task handoff + error/retry.
struct ConversationView: View {
    @StateObject private var vm: ChatViewModel
    @State private var input: String = ""
    private let api: JarvisAPI
    private let initialText: String?
    let conversationId: String

    init(api: JarvisAPI, conversationId: String, initialText: String? = nil) {
        _vm = StateObject(wrappedValue: ChatViewModel(api: api))
        self.api = api
        self.conversationId = conversationId
        self.initialText = initialText
    }

    var body: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 12) {
                        ForEach(vm.messages) { msg in
                            MessageBubble(msg: msg, api: api)
                        }
                        if vm.status == .working || vm.status == .searching || vm.status == .usingTool || !vm.streamingText.isEmpty {
                            StreamingBubble(text: vm.streamingText,
                                            status: vm.status,
                                            statusLabel: vm.statusLabel,
                                            citations: vm.liveCitations)
                                .id("bottom")
                        }
                        if let taskId = vm.pendingTaskId {
                            TaskHandoffCard(taskId: taskId).id("bottom")
                        }
                    }
                    .padding(16)
                }
                .onChange(of: vm.messages.count) { _ in
                    proxy.scrollTo("bottom", anchor: .bottom)
                }
                .onChange(of: vm.streamingText) { _ in
                    proxy.scrollTo("bottom", anchor: .bottom)
                }
            }

            if let err = vm.errorMessage {
                ErrorBanner(message: err) {
                    Task { await vm.retry() }
                }
            }

            InputBar(text: $input, disabled: vm.status == .working || vm.status == .searching || vm.status == .usingTool) {
                let t = input
                input = ""
                Task { await vm.send(t) }
            }
        }
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
        .task {
            await vm.load(conversationId)
            if let t = initialText, !t.isEmpty {
                await vm.send(t)   // إرسال تلقائي للرسالة القادمة من شريط الإدخال الرئيسي
            }
        }
    }
}

private struct MessageBubble: View {
    let msg: ChatMessage
    let api: JarvisAPI
    var body: some View {
        let isUser = msg.role == "user"
        VStack(alignment: isUser ? .trailing : .leading, spacing: 8) {
            HStack {
                if isUser { Spacer(minLength: 48) }
                Text(msg.content ?? "")
                    .font(.system(size: 15))
                    .foregroundColor(isUser ? JarvisColor.text_primary : JarvisColor.text_primary)
                    .padding(12)
                    .background(isUser ? JarvisColor.bg_1 : JarvisColor.surface)
                    .cornerRadius(12)
                if !isUser { Spacer(minLength: 48) }
            }
            if let cits = msg.citations, !cits.isEmpty {
                CitationsView(citations: cits)
            }
            if let refs = msg.attachmentRefs, !refs.isEmpty {
                ForEach(refs, id: \.self) { ref in
                    AttachmentView(fileId: ref, api: api)
                }
            }
        }
    }
}

private struct StreamingBubble: View {
    let text: String
    let status: ChatStatus
    let statusLabel: String
    let citations: [Citation]
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                if status == .working || status == .searching || status == .usingTool {
                    ProgressView().scaleEffect(0.7)
                }
                Text(statusLabel.isEmpty ? "يعمل" : statusLabel)
                    .font(.system(size: 12))
                    .foregroundColor(JarvisColor.highlight_gold)
            }
            if !text.isEmpty {
                Text(text)
                    .font(.system(size: 15))
                    .foregroundColor(JarvisColor.text_primary)
            }
            if !citations.isEmpty {
                CitationsView(citations: citations)
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(JarvisColor.surface)
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(JarvisColor.primary_gold.opacity(0.16), lineWidth: 1)
        )
        .shadow(color: JarvisColor.primary_gold.opacity(0.05), radius: 10, x: 0, y: 4)
    }
}

private struct TaskHandoffCard: View {
    let taskId: String
    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: "arrow.right.circle.fill")
                .foregroundColor(JarvisColor.primary_gold)
            VStack(alignment: .leading, spacing: 2) {
                Text("تحول الطلب إلى مهمة خلفية")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(JarvisColor.text_primary)
                Text("المهمة: \(taskId)")
                    .font(.system(size: 12))
                    .foregroundColor(JarvisColor.text_muted)
                    .lineLimit(1)
            }
            Spacer()
        }
        .padding(12)
        .background(JarvisColor.bg_1)
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(JarvisColor.primary_gold.opacity(0.14), lineWidth: 1)
        )
    }
}

private struct CitationsView: View {
    let citations: [Citation]
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            ForEach(Array(citations.enumerated()), id: \.offset) { idx, c in
                if let url = c.url, let u = URL(string: url) {
                    Link("[\(idx + 1)] \(c.title ?? "مصدر")", destination: u)
                        .font(.system(size: 12))
                        .foregroundColor(JarvisColor.highlight_gold)
                }
            }
        }
    }
}

private struct ErrorBanner: View {
    let message: String
    let onRetry: () -> Void
    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundColor(JarvisColor.danger)
            Text(message)
                .font(.system(size: 13))
                .foregroundColor(JarvisColor.text_primary)
            Spacer()
            Button("إعادة", action: onRetry)
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(JarvisColor.highlight_gold)
        }
        .padding(12)
        .background(JarvisColor.bg_1)
    }
}

private struct InputBar: View {
    @Binding var text: String
    var disabled: Bool
    var onSend: () -> Void
    var body: some View {
        HStack(spacing: 10) {
            TextField("اكتب رسالة…", text: $text)
                .textFieldStyle(.plain)
                .font(.system(size: 15))
                .foregroundColor(JarvisColor.text_primary)
                .tint(JarvisColor.highlight_gold)
                .padding(12)
                .background(JarvisColor.surface)
                .cornerRadius(12)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(JarvisColor.primary_gold.opacity(0.16), lineWidth: 1)
                )
            Button(action: onSend) {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.system(size: 28))
                    .foregroundColor(disabled ? JarvisColor.text_muted : JarvisColor.highlight_gold)
            }
            .disabled(disabled || text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        }
        .padding(12)
    }
}
