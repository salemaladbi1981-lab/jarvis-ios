import XCTest
// Memory types compiled directly into this target (MEMORY_SOURCES) — no @testable import.

final class MemoryTests: XCTestCase {

    private func item(_ id: String, _ cat: MemoryCategory, _ prov: MemoryProvenance,
                      _ content: String, _ kw: [String], _ prio: Int, updated: Double = 1_000.0) -> MemoryItem {
        MemoryItem(id: id, category: cat, provenance: prov, content: content,
                   keywords: kw, priority: prio, updatedAtEpoch: updated,
                   createdAtEpoch: 0, source: nil, isActive: true)
    }

    func testRetrievalIsRelevantNotFull() {
        let items = [
            item("name", .durableFact, .ownerProvided, "الاسم: سالم", ["اسم", "هوية"], 10),
            item("meridian", .activeProject, .ownerProvided, "مشروع MERIDIAN", ["مشروع", "مريديان"], 8),
            item("old", .historical, .importedSeed, "سياق قديم", ["تاريخ"], 3),
        ]
        let r = MemoryRetrieval.retrieve(from: items, query: "وش اسمي", scope: .current, limit: 5)
        XCTAssertEqual(r.first?.id, "name", "الاستعلام عن الهوية يجب أن يرجع الاسم أولاً")
        XCTAssertFalse(r.contains { $0.id == "old" }, "العنصر التاريخي لا يظهر في نطاق current")
    }

    func testHistoricalNotCurrent() {
        let items = [
            item("now", .durableFact, .ownerProvided, "حقيقة حالية", ["حالي"], 8),
            item("past", .historical, .importedSeed, "حدث قديم", ["قديم", "تاريخ"], 3),
        ]
        let cur = MemoryRetrieval.retrieve(from: items, query: "حالي قديم تاريخ", scope: .current, limit: 5)
        XCTAssertFalse(cur.contains { $0.category == .historical }, "historical لا يصبح current")
        let hist = MemoryRetrieval.retrieve(from: items, query: "قديم تاريخ", scope: .historical, limit: 5)
        XCTAssertTrue(hist.contains { $0.id == "past" }, "نطاق historical يشمل العناصر التاريخية")
    }

    func testNewerExplicitDecisionOverridesOlder() {
        let store = MemoryStore(items: [])
        let old = item("d1", .decision, .explicitDecision, "V1.0 Live", ["نسخة", "قرار"], 10, updated: 100)
        let newer = item("d2", .decision, .explicitDecision, "V1.1 Live", ["نسخة", "قرار"], 10, updated: 200)
        XCTAssertTrue(store.upsert(old))
        XCTAssertTrue(store.upsert(newer))
        let active = store.allItems(activeOnly: true)
        XCTAssertTrue(active.contains { $0.id == "d2" }, "القرار الأحدث يبقى نشطاً")
        XCTAssertFalse(active.contains { $0.id == "d1" }, "القرار الأقدم المتعارض يُعطَّل")
    }

    func testSecretsRejected() {
        let store = MemoryStore(items: [])
        let secret = item("s1", .durableFact, .ownerProvided, "مفتاحي sk-abcdefghijklmnopqrstuvwx", ["مفتاح"], 5)
        XCTAssertFalse(store.upsert(secret), "الأسرار تُرفض")
        XCTAssertTrue(store.allItems(activeOnly: true).isEmpty)
        XCTAssertTrue(MemoryStore.containsSecret("password=Sup3rSecret123"))
        XCTAssertTrue(MemoryStore.containsSecret("api_key=abcdefghijklmnop"))
    }

    func testOwnerControlDisable() {
        let store = MemoryStore(items: [item("x", .durableFact, .ownerProvided, "معلومة", ["شيء"], 5)])
        XCTAssertTrue(store.disable(id: "x"))
        XCTAssertTrue(store.allItems(activeOnly: true).isEmpty)
        XCTAssertFalse(store.allItems(activeOnly: false).isEmpty)
    }

    func testRetrievalCharBudget() {
        let long = item("long", .durableFact, .ownerProvided, String(repeating: "كلمة ", count: 500), ["طويل"], 5)
        let r = MemoryRetrieval.retrieve(from: [long], query: "طويل", scope: .current, limit: 5, charBudget: 100)
        // مع حدّ أحرف 100، العنصر الطويل (أكبر من الميزانية) يُستبعد
        XCTAssertTrue(r.isEmpty, "حدّ حجم السياق يُحترم — لا يُحقن عنصر أكبر من الميزانية")
    }
}
