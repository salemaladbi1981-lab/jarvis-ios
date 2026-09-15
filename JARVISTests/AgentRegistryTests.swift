import XCTest
@testable import JARVIS

final class AgentRegistryTests: XCTestCase {
    func testRegistryDecodesAllGroupsAnd21Agents() throws {
        let r = try AgentRegistry.load()
        XCTAssertEqual(Set(r.groups.keys), ["core", "system", "content"])
        XCTAssertEqual(r.agents.count, 21)
        XCTAssertEqual(r.agents(in: "core").count, 8)
        XCTAssertEqual(r.agents(in: "system").count, 5)
        XCTAssertEqual(r.agents(in: "content").count, 8)
        let ids = r.agents.map { $0.id }
        XCTAssertEqual(Set(ids).count, ids.count)
        XCTAssertEqual(r.groups["system"]?.default, nil)
        XCTAssertEqual(r.defaultGroup, "core")
    }
}
