"""سجل أصوات ElevenLabs الرجولية — يختار منها د. سالم من الإعدادات.

10 أصوات رجولية جاهزة (premade) تعمل مع eleven_flash_v2_5 / eleven_multilingual_v2
وتنطق العربية. المفاتيح (keys) هي نفسها في تطبيق iOS (VoiceCatalog.swift) بحيث
يمرّر العميل مفتاح الصوت المختار عبر ?voice=<key> ويحلّه الخادم إلى voice_id.

لاستبدالها بأصوات خليجية أصلية (voice library / cloned): اضبط المتغير البيئي
JARVIS_ELEVENLABS_VOICES بـ JSON على الشكل:
    {"key": {"id": "<voice_id>", "name": "...", "name_ar": "..."}, ...}
يستبدل السجل بالكامل. أو استخدم JARVIS_ELEVENLABS_VOICE لتغيير المفتاح الافتراضي فقط.
"""
import json
import os

# مفتاح مستقر -> {voice_id من ElevenLabs, اسم إنجليزي، اسم عربي، وصف قصير}.
# أصوات خليجية رجولية حقيقية من مكتبة ElevenLabs (accent: gulf/saudi/kuwaiti/emirati/omani) —
# جميعها مُتحقَّق منها (HTTP 200) مع eleven_flash_v2_5. يمكن تجاوزها بالكامل عبر env.
_DEFAULT_VOICES = {
    "omar_deep":    {"id": "u2nyDCDuMGCCGx5X6FMY", "name": "Omar",     "name_ar": "عمر",       "desc": "سعودي، عميق سينمائي"},
    "mohammed_uae": {"id": "cWKuRwIA5GW57OPMLC3A", "name": "Mohammed", "name_ar": "محمد",      "desc": "إماراتي خليجي، هادئ"},
    "mohamed_kw":   {"id": "KJe6YIQ4MHI94EGaDZC7", "name": "Mohamed",  "name_ar": "محمد",      "desc": "كويتي، واثق"},
    "mazin_omani":  {"id": "faws6CwamdGbX8RSkPOL", "name": "Mazin",    "name_ar": "مازن",      "desc": "عُماني، هادئ"},
    "firas":        {"id": "T9KaXxyeFWyP8DFgs9bx", "name": "Firas",    "name_ar": "فراس",      "desc": "سعودي، لطيف"},
    "ahmad":        {"id": "UXEyt6rtmFO9w5hBhzq9", "name": "Ahmad",    "name_ar": "أحمد",      "desc": "سعودي، هادئ"},
    "saad":         {"id": "3vR1KVyyNDhdkucpugQI", "name": "Saad",     "name_ar": "سعد",       "desc": "سعودي، هادئ"},
    "ali_saudi":    {"id": "Hvlnv5DwiIO2CQ6oYMZ3", "name": "Ali",      "name_ar": "علي",       "desc": "سعودي، عفوي"},
    "ali_ahmed":    {"id": "4cNMUnP82XXb8lCOMzrt", "name": "Ali Ahmed","name_ar": "علي أحمد",  "desc": "سعودي، سردي"},
    "osamah":       {"id": "CWVr3UPCDYlT6oZmdrEG", "name": "Osamah",   "name_ar": "أسامة",     "desc": "سعودي، عفوي"},
}


def _load_voices() -> dict:
    raw = os.environ.get("JARVIS_ELEVENLABS_VOICES", "").strip()
    if not raw:
        return dict(_DEFAULT_VOICES)
    try:
        data = json.loads(raw)
        # نقبل فقط الإدخالات التي تحمل voice_id غير فارغ.
        cleaned = {k: v for k, v in data.items() if isinstance(v, dict) and v.get("id")}
        return cleaned or dict(_DEFAULT_VOICES)
    except Exception:
        return dict(_DEFAULT_VOICES)


VOICES = _load_voices()


def default_key() -> str:
    """المفتاح الافتراضي من config، مع الرجوع لأول مفتاح متاح إن كان غير صالح."""
    import config
    key = config.ELEVENLABS_DEFAULT_VOICE
    if key in VOICES:
        return key
    return next(iter(VOICES), "omar_deep")


def resolve(key: str | None) -> str:
    """يحوّل مفتاح صوت (من العميل) إلى voice_id لـ ElevenLabs. أي مفتاح غير معروف → الافتراضي."""
    if key and key in VOICES:
        return VOICES[key]["id"]
    return VOICES.get(default_key(), {}).get("id", "")


def list_voices() -> list[dict]:
    """قائمة الأصوات للعرض (key + الأسماء + الوصف) — بدون تسريب voice_id للعميل."""
    return [
        {"key": k, "name": v.get("name", k), "name_ar": v.get("name_ar", ""), "desc": v.get("desc", "")}
        for k, v in VOICES.items()
    ]
