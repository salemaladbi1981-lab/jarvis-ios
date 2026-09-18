"""JARVIS Capability Registry — يقرأ JARVIS-CAPABILITIES.json ويجيب بأسئلة القدرات."""
from __future__ import annotations
import json, os

CAPS_PATH = os.environ.get("JARVIS_CAPS_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "JARVIS-CAPABILITIES.json"))
_cache = None


def load() -> dict:
    global _cache
    if _cache is None:
        with open(CAPS_PATH, encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def list_capabilities(summary: bool = True) -> list[dict]:
    doc = load()
    if not summary:
        return doc["capabilities"]
    keys = ("capability_id", "display_name_ar", "display_name_en", "description",
            "category", "skill_count", "tools", "execution_status", "tested")
    return [{k: c.get(k) for k in keys} for c in doc["capabilities"]]


def get_capability(cid: str) -> dict | None:
    for c in load()["capabilities"]:
        if c["capability_id"] == cid:
            return c
    return None


def overlap_groups() -> list[dict]:
    return load()["overlap_groups"]


def answer_what_can_you_do() -> dict:
    """جواب منظم لسؤال 'وش تقدر تسوي؟' — قدرات، لا hundreds من raw skills."""
    caps = [c for c in load()["capabilities"] if c["capability_id"] != "other"]
    return {
        "capability_count": len(caps),
        "capabilities": [
            {"id": c["capability_id"], "name_ar": c["display_name_ar"],
             "name_en": c["display_name_en"], "description": c["description"],
             "skill_count": c["skill_count"]}
            for c in caps
        ],
    }


def describe_ar() -> str:
    """نص عربي مرتب للعرض المباشر."""
    lines = []
    for c in load()["capabilities"]:
        if c["capability_id"] == "other":
            continue
        lines.append(f"• {c['display_name_ar']} — {c['description']}")
    return "\n".join(lines)
