import Foundation

/// Seed Context أولي — بيانات، ليست prompt يُرسل بالكامل كل turn.
/// مصدرها: SALEM_JARVIS_PERSONAL_CONTEXT_MASTER.txt (سياق Manus المستورد).
/// قابلة للاستبدال عند تزويد ملف seed محدّث.
enum MemorySeed {

    private static let t: Double = 1_750_000_000.0

    private static func item(
        _ id: String, _ cat: MemoryCategory, _ prov: MemoryProvenance,
        _ content: String, _ keywords: [String], _ priority: Int,
        source: String? = nil, updated: Double? = nil
    ) -> MemoryItem {
        MemoryItem(
            id: id, category: cat, provenance: prov,
            content: content, keywords: keywords, priority: priority,
            updatedAtEpoch: updated ?? t, createdAtEpoch: t,
            source: source, isActive: true
        )
    }

    static func defaultItems() -> [MemoryItem] {
        [
            // MARK: Durable Facts — الهوية
            item("f-name", .durableFact, .importedSeed,
                 "المالك: د. سالم خجيم العذبة (Dr. Salem Khejaim Al-Adhba).",
                 ["اسم", "هوية", "من أنا", "سالم", "العذبة"], 10,
                 source: "SALEM_JARVIS_PERSONAL_CONTEXT_MASTER.txt"),
            item("f-phd", .durableFact, .importedSeed,
                 "دكتوراه في الاستثمار الأجنبي المباشر (Foreign Direct Investment).",
                 ["دكتوراه", "شهادة", "تعليم", "استثمار", "دراسة"], 8),
            item("f-married", .durableFact, .importedSeed,
                 "متزوج.",
                 ["متزوج", "زواج", "عائلة"], 6),
            item("f-cities", .durableFact, .importedSeed,
                 "يتنقل بين الدوحة ولندن.",
                 ["الدوحة", "لندن", "تنقل", "سفر", "مدينة"], 7),
            item("f-studio", .durableFact, .importedSeed,
                 "مؤسس ومدير Salem AI Studio W.L.L. (الدوحة).",
                 ["شركة", "استوديو", "عمل", "salem", "studio"], 9),
            item("f-club", .durableFact, .importedSeed,
                 "مدير العلاقات العامة والتسويق في نادي قطر للسباق والفروسية.",
                 ["نادي", "سباق", "فروسية", "عمل", "قطر"], 8),
            item("f-audience", .durableFact, .importedSeed,
                 "صانع محتوى: سناب شات +1 مليون، إنستغرام ~99 ألف.",
                 ["سناب", "انستغرام", "متابعين", "محتوى", "منصات"], 8),

            // MARK: Preferences — أسلوب العمل والتواصل
            item("p-dialect", .preference, .importedSeed,
                 "يتواصل بالعربية الخليجية (مش على سناب، مو على X)، والإنجليزية مع الشركاء الأجانب.",
                 ["لهجة", "لغة", "تواصل", "مش", "مو"], 7),
            item("p-result-first", .preference, .importedSeed,
                 "يبدأ بالنتيجة ثم التفاصيل، تنفيذ لا شرح.",
                 ["أسلوب", "نتيجة", "ترتيب", "تنفيذ"], 7),
            item("p-proof", .preference, .importedSeed,
                 "الكلام ما يُحسب — الدليل بس. لا ادعاء بدون تحقق.",
                 ["دليل", "صدق", "تحقق", "برهان"], 8),
            item("p-no-flattery", .preference, .importedSeed,
                 "لا مجاملة — ينبّه للمشاريع المتعثرة والالتزامات غير المنجزة بوضوح.",
                 ["مجاملة", "صدق", "تنبيه", "صراحة"], 7),
            item("p-desktop", .preference, .importedSeed,
                 "التسليمات على سطح المكتب، لا مجلد التنزيلات.",
                 ["سطح المكتب", "تسليم", "desktop"], 5),
            item("p-voice", .preference, .importedSeed,
                 "الصوت السينمائي الحيوي الأسرع (Yousuf — سرد إماراتي سينمائي).",
                 ["صوت", "نبرة", "سينمائي", "حيوي"], 6),

            // MARK: Active Projects
            item("prj-jarvis", .activeProject, .runtimeState,
                 "JARVIS V1.1 — Phase 1: Memory architecture + Real Tools (Calendar/Reminders).",
                 ["جارفس", "مشروع", "مرحلة", "memory", "أدوات"], 9,
                 source: "PROJECT_STATE.md"),
            item("prj-qeyas", .activeProject, .importedSeed,
                 "Qeyas — علامة ثوب (qeyas.app).",
                 ["قياس", "ثوب", "مشروع", "علامة"], 7),
            item("prj-meridian", .activeProject, .importedSeed,
                 "MERIDIAN — مشروع نشط قيد الإغلاق.",
                 ["مريديان", "مشروع", "صفقة"], 7),
            item("prj-rafiq", .activeProject, .importedSeed,
                 "Rafiq — مدرب لياقة AI.",
                 ["رفيق", "لياقة", "مشروع", "مدرب"], 6),

            // MARK: Decisions / Frozen Baselines
            item("d-live", .decision, .explicitDecision,
                 "JARVIS-V1.0-LIVE معتمد كنسخة Live مستقرة (tag → 2f36cfb).",
                 ["نسخة", "قرار", "اعتماد", "live", "v1", "مستقر"], 10,
                 source: "قرار المالك 2026-09-17"),
            item("d-frozen", .decision, .explicitDecision,
                 "مجمّد بدون regression مثبت + موافقة المالك: AEC / PCM / Playback / Barge-in / WSS / verse / persona / VAD.",
                 ["مجمّد", "قرار", "صوت", "aec", "vad", "barge"], 10,
                 source: "قرار المالك"),
            item("d-coremotion", .decision, .explicitDecision,
                 "Core Motion غير مكتملة بصرياً ومؤجلة إلى V1.1.",
                 ["core motion", "مؤجل", "قرار", "حركة", "نواة"], 9,
                 source: "قرار المالك"),

            // MARK: Historical Context
            item("h-manus", .historical, .importedSeed,
                 "Manus «JARVIS Master Context» — ملف ذاكرة 45 صفحة، seed مستورد (سبتمبر 2026).",
                 ["مانوس", "سياق", "تاريخ", "master", "context"], 4),
            item("h-claude", .historical, .importedSeed,
                 "مراجعة استخدام Claude (167 محادثة عبر 6 مشاريع، يونيو–سبتمبر 2026).",
                 ["كلود", "تاريخ", "مراجعة"], 3),
        ]
    }
}
