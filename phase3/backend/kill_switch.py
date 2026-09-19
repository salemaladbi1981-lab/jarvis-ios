"""Kill switch — يمنع المهمات الجديدة ويلغي الجلسات النشطة عند التفعيل."""
import json, os, time

KILL_PATH = os.environ.get("JARVIS_KILL_SWITCH", "/opt/data/logs/jarvis-kill-switch.json")


def _load():
    try:
        with open(KILL_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"engaged": False, "reason": "", "at": None}


def _save(d):
    os.makedirs(os.path.dirname(KILL_PATH), exist_ok=True)
    tmp = KILL_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tmp, KILL_PATH)


def engaged() -> bool:
    return bool(_load().get("engaged"))


def engage(reason: str = "") -> dict:
    d = {"engaged": True, "reason": reason, "at": time.time()}
    _save(d)
    return d


def disengage() -> dict:
    d = {"engaged": False, "reason": "", "at": time.time()}
    _save(d)
    return d


def guard():
    """يرمي/يرجع False إذا المفتاح مفعّل (يُستخدم قبل إنشاء مهمة/تنفيذ حساس)."""
    if engaged():
        return False
    return True
