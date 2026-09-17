import Foundation

/// مخزن الذاكرة — يحفظ + يسترجع + يطبّق قواعد المصدر/التعارض/الخصوصية/تحكم المالك.
/// Pure Foundation، لا يمسّ أي قرار هندسي مجمّد (AEC/PCM/.../VAD/Core Motion).
final class MemoryStore {

    private(set) var items: [MemoryItem]

    init(items: [MemoryItem] = []) {
        self.items = items
    }

    static func seeded() -> MemoryStore {
        MemoryStore(items: MemorySeed.defaultItems())
    }

    // MARK: Owner control — القراءة (المالك يرى ما يعرفه جارفس)
    func allItems(activeOnly: Bool = true) -> [MemoryItem] {
        activeOnly ? items.filter { $0.isActive } : items
    }

    func items(in category: MemoryCategory, activeOnly: Bool = true) -> [MemoryItem] {
        allItems(activeOnly: activeOnly).filter { $0.category == category }
    }

    // MARK: Owner control — إضافة/تصحيح (conflict-aware)
    /// يرجع false إذا رُفض (سرّ) أو لم يستوفِ سلطة المصدر.
    @discardableResult
    func upsert(_ item: MemoryItem) -> Bool {
        guard !Self.containsSecret(item.content) else { return false }

        // نفس المعرّف → الأحدث صراحةً يلغي الأقدم المتعارض
        if let idx = items.firstIndex(where: { $0.id == item.id }) {
            guard item.provenance.authority >= items[idx].provenance.authority else { return false }
            items[idx] = item
            return true
        }

        // تعارض موضوعي: عنصر صريح أحدث (decision/owner) بنفس الفئة وكلمات متداخلة
        // يُعطّل الأقدم المتعارض بدل تكديس معلومتين متناقضتين.
        let isExplicit = item.provenance == .explicitDecision || item.provenance == .ownerProvided
        for idx in items.indices {
            let old = items[idx]
            guard old.isActive, old.category == item.category, old.id != item.id else { continue }
            let overlap = !Set(old.keywords).isDisjoint(with: Set(item.keywords))
            let newer = item.updatedAtEpoch >= old.updatedAtEpoch
            let higherOrEqual = item.provenance.authority >= old.provenance.authority
            if overlap && newer && higherOrEqual && isExplicit {
                items[idx].isActive = false
            }
        }
        items.append(item)
        return true
    }

    // MARK: Owner control — تعطيل/حذف
    @discardableResult
    func disable(id: String) -> Bool {
        guard let idx = items.firstIndex(where: { $0.id == id }) else { return false }
        items[idx].isActive = false
        return true
    }

    @discardableResult
    func remove(id: String) -> Bool {
        guard let idx = items.firstIndex(where: { $0.id == id }) else { return false }
        items.remove(at: idx)
        return true
    }

    // MARK: Privacy — رفض الأسرار داخل الذاكرة العامة
    static func containsSecret(_ text: String) -> Bool {
        let patterns = [
            #"sk-[A-Za-z0-9]{20,}"#,          // OpenAI-style
            #"ghp_[A-Za-z0-9]{20,}"#,         // GitHub PAT
            #"xox[baprs]-[A-Za-z0-9-]{10,}"#, // Slack token
            #"AKIA[0-9A-Z]{16}"#,             // AWS access key
            #"(?i)\bpassword\s*[=:]\s*\S+"#,
            #"(?i)\bapi[_-]?key\s*[=:]\s*\S+"#,
            #"(?i)\btoken\s*[=:]\s*[A-Za-z0-9._-]{16,}"#,
            #"-----BEGIN [A-Z ]*PRIVATE KEY-----"#,
        ]
        for p in patterns {
            if text.range(of: p, options: .regularExpression) != nil { return true }
        }
        return false
    }
}
