import Foundation

/// نطاق الاسترجاع — التاريخ/الجلسة لا يظهران في الاستعلامات الحالية تلقائياً.
enum MemoryScope: Equatable {
    case current      // durable + preference + project + decision
    case historical   // + historical
    case all          // + session
}

/// استرجاع محدود الحجم — لا يُحقن كامل الذاكرة أبداً.
enum MemoryRetrieval {

    /// يرجع العناصر الأكثر صلة بالاستعلام، ضمن حدّ عدد + حدّ حجم أحرف.
    static func retrieve(
        from items: [MemoryItem],
        query: String,
        scope: MemoryScope = .current,
        limit: Int = 5,
        charBudget: Int = 1200
    ) -> [MemoryItem] {
        let queryTokens = tokenize(query)
        guard !queryTokens.isEmpty else { return [] }

        var scored: [(item: MemoryItem, score: Double)] = []
        for item in items where item.isActive {
            let s = score(item: item, queryTokens: queryTokens, scope: scope)
            if s > 0 { scored.append((item, s)) }
        }
        scored.sort { $0.score > $1.score }

        var result: [MemoryItem] = []
        var usedChars = 0
        for entry in scored {
            guard scopeAllows(entry.item.category, scope: scope) else { continue }
            if result.count >= limit { break }
            if usedChars + entry.item.content.count > charBudget { continue }
            result.append(entry.item)
            usedChars += entry.item.content.count
        }
        return result
    }

    static func scopeAllows(_ c: MemoryCategory, scope: MemoryScope) -> Bool {
        switch scope {
        case .current:     return c != .historical && c != .session
        case .historical:  return c != .session
        case .all:         return true
        }
    }

    static func score(item: MemoryItem, queryTokens: Set<String>, scope: MemoryScope) -> Double {
        var s = 0.0
        let kw = Set(item.keywords.map { $0.lowercased() })
        let body = tokenize(item.content)
        for t in queryTokens {
            if kw.contains(t) { s += 3.0 }
            else if body.contains(t) { s += 1.0 }
        }
        switch item.category {
        case .durableFact, .decision: s += 2.0
        case .preference, .activeProject: s += 1.5
        case .historical: s += (scope == .historical) ? 1.0 : 0.0
        case .session: s += (scope == .all) ? 0.5 : 0.0
        }
        s += Double(item.priority) * 0.1
        return s
    }

    /// يُقسّم النص (عربي/لاتيني) إلى كلمات ≥ حرفين، مع تجاهل علامات الترقيم والفراغات.
    static func tokenize(_ s: String) -> Set<String> {
        let parts = s.lowercased().components(separatedBy: CharacterSet.alphanumerics.inverted)
        return Set(parts.filter { $0.count >= 2 })
    }
}
