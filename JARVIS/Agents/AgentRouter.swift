//
//  AgentRouter.swift — deterministic intent → agent routing.
//  Maps a user request String to one of the six routable agent IDs
//  registered in AGENT-REGISTRY.json. Unknown intent falls back to
//  core_coordinator. Mirrors the keyword-routing convention used by
//  the backend orchestrator (phase3/backend/orchestrator.py) but
//  operates locally on-device, with no network call.
//
import Foundation

/// Deterministic router from a natural-language request to a registered agent ID.
///
/// Routes are evaluated in declared order; the first matching keyword set wins.
/// Requests that match no route return `AgentRouter.defaultAgentID`
/// (`core_coordinator`), so callers always receive a valid agent handle.
public enum AgentRouter {

    /// Agent used when no route matches (unknown / general intent).
    public static let defaultAgentID: String = "core_coordinator"

    /// The set of agent IDs this router may return.
    /// Kept in sync with the routable subset of AGENT-REGISTRY.json.
    public static let routableAgentIDs: Set<String> = [
        "core_coordinator",
        "core_writer",
        "core_home",
        "sys_server",
        "ct_scriptwriter",
        "ct_prompteng",
    ]

    /// Ordered keyword routes. First match (case- and diacritic-insensitive) wins.
    /// Keywords are bilingual (English + Arabic) to match the registry's audience.
    private static let routes: [(agentID: String, keywords: [String])] = [
        // Smart-home: temperature, lights, doors, locks, cameras, alarms, scenes.
        ("core_home", [
            "temperature", "حرارة", "درجة", "light", "إضاءة", "ضوء",
            "door", "باب", "unlock", "lock", "قفل", "فتح",
            "camera", "كاميرا", "alarm", "إنذار", "scene", "مشهد",
            "home", "بيت", "منزل", "smart home",
        ]),

        // Server / infrastructure / health / integrations.
        ("sys_server", [
            "server", "خادم", "health", "صحة", "service", "خدمة",
            "status", "حالة النظام", "infra", "infrastructure", "backend",
            "integration", "تكامل", "deploy", "نشر",
        ]),

        // Scriptwriting: scripts, dialogue, hooks, scenarios.
        ("ct_scriptwriter", [
            "script", "سكريبت", "سيناريو", "dialogue", "حوار",
            "hook", "هوك", "scene", "مشهد سينمائي", "storyboard",
        ]),

        // Prompt engineering: prompts for image / video / audio generation.
        ("ct_prompteng", [
            "prompt", "برومبت", "image prompt", "video prompt",
            "midjourney", "sora", "stable diffusion", "model adaptation",
            "تكييف النموذج", "توليد صورة", "توليد فيديو",
        ]),

        // Copywriting: captions, copy, drafts, narration text.
        ("core_writer", [
            "copy", "نسخ", "caption", "تعليق", "write", "اكتب",
            "draft", "مسودة", "نص", "نصوص", "نص كتابي", "article",
            "مقال", "blog", "مدونة",
        ]),
    ]

    /// Routes `request` to a registered agent ID.
    ///
    /// Matching is case-insensitive and diacritics-insensitive. The first
    /// route whose keyword set contains any substring of the normalized
    /// request wins. Unknown intent returns `defaultAgentID`.
    ///
    /// - Parameter request: Raw user input (any language).
    /// - Returns: A routable agent ID; never empty.
    public static func route(_ request: String) -> String {
        let normalized = Self.normalize(request)
        guard !normalized.isEmpty else { return defaultAgentID }
        for (agentID, keywords) in routes where Self.matches(any: keywords, in: normalized) {
            return agentID
        }
        return defaultAgentID
    }

    /// Convenience: resolve the routed agent against a loaded registry.
    /// Returns `nil` only if the registry is missing the routed ID
    /// (e.g. registry bundle not loaded); callers may then fall back to
    /// `defaultAgentID` or handle the missing-agent case.
    public static func agent(for request: String, in registry: AgentRegistry) -> Agent? {
        let id = route(request)
        return registry.agents.first(where: { $0.id == id })
    }

    // MARK: - Matching helpers

    /// True if any keyword appears as a substring of `normalized`.
    private static func matches(any keywords: [String], in normalized: String) -> Bool {
        keywords.contains { normalized.contains($0) }
    }

    /// Lowercases, folds diacritics, and trims whitespace for stable matching.
    private static func normalize(_ text: String) -> String {
        text
            .folding(options: [.caseInsensitive, .diacriticInsensitive, .widthInsensitive],
                     locale: .init(identifier: "en_US_POSIX"))
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}