import XCTest
@testable import JarvisTransport

private final class StubProtocol: URLProtocol {
    static var handler: ((URLRequest) throws -> (Int, String, Data))?
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        do {
            let (status, type, data) = try Self.handler!(request)
            let response = HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil,
                                           headerFields: ["Content-Type": type])!
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch { client?.urlProtocol(self, didFailWithError: error) }
    }
    override func stopLoading() {}
}

@MainActor
final class ChatTransportTests: XCTestCase {
    private func api() -> JarvisAPI {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [StubProtocol.self]
        return JarvisAPI(baseURL: URL(string: "https://jarvis.test")!, sessionToken: "test-session",
                         workspace: "BUSINESS", session: URLSession(configuration: config))
    }

    func testRequestCarriesIdentityWorkspaceAndJSON() throws {
        let req = try api().request("conversations/c/chat", method: "POST", body: ["text": "hello"])
        XCTAssertEqual(req.value(forHTTPHeaderField: "X-Jarvis-Session"), "test-session")
        XCTAssertEqual(req.value(forHTTPHeaderField: "X-Jarvis-Workspace"), "BUSINESS")
        XCTAssertEqual(req.httpMethod, "POST")
        XCTAssertEqual(req.timeoutInterval, 90)
        XCTAssertNotNil(req.httpBody)
    }

    func testNoRequestWithEmptySession() {
        let api = JarvisAPI(baseURL: URL(string: "https://jarvis.test")!, sessionToken: " ")
        XCTAssertThrowsError(try api.request("conversations")) { XCTAssertEqual($0 as? JarvisAPIError, .authentication) }
    }

    func testHTTPStatusMapping() {
        for (code, error) in [(401, JarvisAPIError.authentication), (403, .forbidden), (404, .notFound),
                              (409, .conflict), (429, .rateLimited), (500, .server), (503, .server), (400, .invalidResponse)] {
            let response = HTTPURLResponse(url: api().baseURL, statusCode: code, httpVersion: nil, headerFields: nil)!
            XCTAssertThrowsError(try JarvisAPI.validate(response)) { XCTAssertEqual($0 as? JarvisAPIError, error) }
        }
    }

    func testErrorsDoNotExposeTransportDetails() {
        XCTAssertNotEqual(JarvisAPIError.message(for: URLError(.timedOut)), JarvisAPIError.message(for: URLError(.notConnectedToInternet)))
        XCTAssertFalse(JarvisAPIError.message(for: NSError(domain: "sk-secret", code: 0)).contains("sk-secret"))
    }

    func testEnvelopeAndSnakeCaseDecoding() throws {
        let json = #"{"ok":true,"created":true,"conversation":{"conversation_id":"c-1","workspace_id":"BUSINESS"}}"#
        let result = try JarvisJSON.decoder().decode(ConversationEnvelope.self, from: Data(json.utf8))
        XCTAssertEqual(result.conversation.id, "c-1")
        let event = try JarvisJSON.decoder().decode(CompleteEvent.self, from: Data(#"{"message_id":"m-1","task_id":"t-1","status":"background_task"}"#.utf8))
        XCTAssertEqual(event.messageId, "m-1")
        XCTAssertEqual(event.taskId, "t-1")
    }

    func testSSEFrameParsing() {
        var parser = ChatEventParser()
        XCTAssertNil(parser.consume(": heartbeat"))
        XCTAssertNil(parser.consume("event:content_delta"))
        XCTAssertNil(parser.consume("data: {\"delta\":"))
        XCTAssertNil(parser.consume("data: \"hello\"}"))
        let event = parser.consume("")
        XCTAssertEqual(event?.name, "content_delta")
        XCTAssertEqual(event?.payload, "{\"delta\":\n\"hello\"}")
        XCTAssertNil(parser.finish())
    }

    func testSuccessfulStreamingAndNoDuplicateCompletion() async {
        StubProtocol.handler = { req in
            XCTAssertEqual(req.value(forHTTPHeaderField: "X-Jarvis-Workspace"), "BUSINESS")
            return (200, "text/event-stream", Data("event: content_delta\ndata: {\"delta\":\"Hello\"}\n\nevent: message_complete\ndata: {\"message_id\":\"a1\",\"status\":\"complete\"}\n\nevent: message_complete\ndata: {\"message_id\":\"a1\",\"status\":\"complete\"}\n\n".utf8))
        }
        let vm = ChatViewModel(api: api())
        vm.conversationId = "c1"
        await vm.send("hi")
        XCTAssertNil(vm.errorMessage)
        XCTAssertEqual(vm.messages.map(\.content), ["hi", "Hello"])
        XCTAssertEqual(vm.messages.last?.id, "a1")
        XCTAssertFalse(vm.isSending)
    }

    func testRetryReusesUserMessageAndRequestID() async {
        var calls = 0
        var requestIDs: [String] = []
        StubProtocol.handler = { req in
            calls += 1
            // URLSession may present body as a stream to URLProtocol.
            var body = req.httpBody
            if body == nil, let stream = req.httpBodyStream {
                stream.open(); defer { stream.close() }
                var bytes = [UInt8](repeating: 0, count: 4096)
                let count = stream.read(&bytes, maxLength: bytes.count)
                if count > 0 { body = Data(bytes.prefix(count)) }
            }
            if let body, let obj = try JSONSerialization.jsonObject(with: body) as? [String: String] {
                requestIDs.append(obj["client_msg_id"] ?? "")
            }
            if calls == 1 { throw URLError(.networkConnectionLost) }
            return (200, "text/event-stream", Data("event: content_delta\ndata: {\"delta\":\"Recovered\"}\n\nevent: message_complete\ndata: {\"message_id\":\"a1\",\"status\":\"complete\"}\n\n".utf8))
        }
        let vm = ChatViewModel(api: api()); vm.conversationId = "c1"
        await vm.send("hi")
        XCTAssertEqual(vm.status, .failed)
        await vm.retry()
        XCTAssertEqual(vm.messages.filter { $0.role == "user" }.count, 1)
        XCTAssertEqual(vm.messages.last?.content, "Recovered")
        XCTAssertEqual(requestIDs.count, 2)
        XCTAssertEqual(Set(requestIDs).count, 1)
        XCTAssertFalse(requestIDs.contains(""))
    }

    func testTruncatedOrNonSSEStreamIsNotSuccess() async {
        for (code, type, body) in [(200, "text/event-stream", "event: content_delta\ndata: {\"delta\":\"partial\"}\n\n"),
                                  (200, "application/json", "{}"), (401, "application/json", "{}"), (503, "text/html", "error")] {
            StubProtocol.handler = { _ in (code, type, Data(body.utf8)) }
            let vm = ChatViewModel(api: api()); vm.conversationId = "c1"
            await vm.send("hi")
            XCTAssertEqual(vm.status, .failed)
            XCTAssertNotNil(vm.errorMessage)
            XCTAssertFalse(vm.isSending)
            XCTAssertEqual(vm.messages.count, 1)
        }
    }

    func testSSEPreservesArabicAndCRLFAcrossBytes() throws {
        var parser = ChatEventParser()
        var events: [ChatEventParser.Event] = []
        for byte in "event:content_delta\r\ndata:{\"delta\":\"مرحبا\"}\r\n\r\n".utf8 {
            if let event = try parser.consume(byte) { events.append(event) }
        }
        XCTAssertEqual(events.count, 1)
        XCTAssertEqual(events.first?.payload, "{\"delta\":\"مرحبا\"}")
    }

    func testBackgroundTaskIDDecodes() async {
        StubProtocol.handler = { _ in (200, "text/event-stream", Data("event: message_complete\ndata: {\"status\":\"background_task\",\"task_id\":\"t1\"}\n\n".utf8)) }
        let vm = ChatViewModel(api: api()); vm.conversationId = "c1"
        await vm.send("hi")
        XCTAssertEqual(vm.pendingTaskId, "t1")
        XCTAssertEqual(vm.status, .backgroundTask)
        XCTAssertFalse(vm.isSending)
    }
}
