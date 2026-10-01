import Foundation

/// Opt-in probe against a disposable backend. Never point it at production: it creates a conversation.
@main
struct ChatHTTPProbe {
    @MainActor static func main() async throws {
        let env = ProcessInfo.processInfo.environment
        guard let base = env["JARVIS_TEST_URL"], let url = URL(string: base),
              ["127.0.0.1", "localhost"].contains(url.host ?? ""),
              let token = env["JARVIS_TEST_SESSION"] else {
            fatalError("An explicitly configured localhost test session is required")
        }
        let api = JarvisAPI(baseURL: url, sessionToken: token)
        let envelope: ConversationEnvelope = try await api.postObject("conversations", body: ["create_new": true])
        let vm = ChatViewModel(api: api)
        await vm.load(envelope.conversation.id)
        precondition(vm.errorMessage == nil && vm.messages.isEmpty)
        await vm.send("what is my name")
        precondition(vm.errorMessage == nil, vm.errorMessage ?? "chat failed")
        precondition(vm.messages.count == 2)
        precondition(vm.messages.filter { $0.role == "user" }.count == 1)
        precondition(vm.messages.last?.content?.contains("لا أملك معلومات محفوظة") == true)
        await vm.retry() // completed sends refresh, they do not re-submit the user message.
        precondition(vm.errorMessage == nil)
        precondition(vm.messages.count == 2)
        precondition(vm.messages.filter { $0.role == "user" }.count == 1)
        print("PASS Swift → HTTP backend: auth, create, decode, load, SSE, grounded memory miss and retry without duplication")
    }
}
