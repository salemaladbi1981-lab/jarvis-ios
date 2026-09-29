import Foundation

/// خيار صوت TTS واحد. المفتاح (key) يطابق سجل الأصوات في الخادم (voices.py)
/// ويُمرّر عبر ?voice=<key> ليحلّه الخادم إلى صوت ElevenLabs الفعلي.
struct VoiceOption: Identifiable, Hashable {
    let key: String
    let nameAr: String
    let nameEn: String
    let desc: String
    var id: String { key }
}

/// الأصوات الرجولية العشرة — نفس المفاتيح والترتيب في الخادم (backend/voices.py).
/// اختيار د. سالم يُحفظ في UserDefaults ويُطبَّق عند بدء محادثة صوتية جديدة.
enum VoiceCatalog {
    static let all: [VoiceOption] = [
        .init(key: "omar_deep",    nameAr: "عمر",      nameEn: "Omar",      desc: "سعودي، عميق سينمائي"),
        .init(key: "mohammed_uae", nameAr: "محمد",     nameEn: "Mohammed",  desc: "إماراتي خليجي، هادئ"),
        .init(key: "mohamed_kw",   nameAr: "محمد",     nameEn: "Mohamed",   desc: "كويتي، واثق"),
        .init(key: "mazin_omani",  nameAr: "مازن",     nameEn: "Mazin",     desc: "عُماني، هادئ"),
        .init(key: "firas",        nameAr: "فراس",     nameEn: "Firas",     desc: "سعودي، لطيف"),
        .init(key: "ahmad",        nameAr: "أحمد",     nameEn: "Ahmad",     desc: "سعودي، هادئ"),
        .init(key: "saad",         nameAr: "سعد",      nameEn: "Saad",      desc: "سعودي، هادئ"),
        .init(key: "ali_saudi",    nameAr: "علي",      nameEn: "Ali",       desc: "سعودي، عفوي"),
        .init(key: "ali_ahmed",    nameAr: "علي أحمد", nameEn: "Ali Ahmed", desc: "سعودي، سردي"),
        .init(key: "osamah",       nameAr: "أسامة",    nameEn: "Osamah",    desc: "سعودي، عفوي"),
    ]

    static let defaultKey = "omar_deep"
    /// مفتاح UserDefaults — مشترك مع @AppStorage في شاشة الإعدادات.
    static let storeKey = "jarvis.tts.voice"

    static var selectedKey: String {
        get { UserDefaults.standard.string(forKey: storeKey) ?? defaultKey }
        set { UserDefaults.standard.set(newValue, forKey: storeKey) }
    }

    static var selected: VoiceOption {
        all.first { $0.key == selectedKey } ?? all[0]
    }
}
