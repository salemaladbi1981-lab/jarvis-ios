import Foundation

/// خيار نموذج TTS (ElevenLabs). المفتاح يُمرَّر عبر ?model=<key> ويحلّه الخادم.
struct ModelOption: Identifiable, Hashable {
    let key: String
    let nameAr: String
    let desc: String
    var id: String { key }
}

/// نماذج ElevenLabs الثلاثة القابلة للاختيار — نفس مفاتيح الخادم (elevenlabs_tts.MODEL_MAP).
enum ModelCatalog {
    static let all: [ModelOption] = [
        .init(key: "multilingual", nameAr: "الأعلى جودة",  desc: "أنقى وأثبت صوت — أبطأ قليلاً (Multilingual v2)"),
        .init(key: "turbo",        nameAr: "متوازن",       desc: "جودة عالية وسرعة جيدة (Turbo v2.5)"),
        .init(key: "flash",        nameAr: "الأسرع",       desc: "أقل زمن استجابة — جودة أقل (Flash v2.5)"),
    ]

    static let defaultKey = "multilingual"
    static let storeKey = "jarvis.tts.model"

    static var selectedKey: String {
        get { UserDefaults.standard.string(forKey: storeKey) ?? defaultKey }
        set { UserDefaults.standard.set(newValue, forKey: storeKey) }
    }
}
