"""Task classifier — INLINE_RESPONSE vs BACKGROUND_TASK.

Property-based (ليس keyword-only): حجم المرفق/عدده، نوع الوسائط، تعقيد النص
(عدد الجمل/الكلمات)، إشارات intent (توليد/خارجي/وكيل). كلها تُرجَّح معًا.
"""
from __future__ import annotations
import re

# إشارات intent (تُستخدم كأحد المدخلات، لا وحدها)
_GENERATION_TERMS = ["أنشئ", "صمم", "ولّد", "فيديو", "ريل", "مونتاج", "رندر", "تصميم",
                     "generate", "render", "create video", "video"]
_EXTERNAL_TERMS = ["أرسل", "احجز", "اشتر", "ادفع", "انشر", "جدول", "موعد",
                   "send", "book", "publish", "schedule", "post"]
_AGENT_TERMS = ["ابحث", "حلل", "اكتب تقرير", "خطة", "ملخص", "قارن",
                "research", "analyze", "plan", "report", "compare"]

_SENT_SPLIT = re.compile(r"[.!؟?\n؛;]+")
_MULTI_STEP_CONNECTORS = ["ثم", "وبعد", "بعدها", "أيضًا", "بعدين", "also", "then"]
_WORD = re.compile(r"\S+")

THRESHOLD = 3  # score >= 3 → BACKGROUND_TASK


def _sentences(text: str) -> int:
    return len([s for s in _SENT_SPLIT.split(text or "") if s.strip()])


def _words(text: str) -> int:
    return len(_WORD.findall(text or ""))


def classify(text: str = "", attachment_count: int = 0, total_bytes: int = 0,
             media_kinds: list | None = None, conversation_message_count: int = 0) -> dict:
    score = 0
    reasons = []
    caps: set[str] = set()
    media_kinds = media_kinds or []
    t = text.lower()

    # structural (الأعلى وزنًا — لا كلمات)
    if total_bytes > 5_000_000:
        score += 3
        reasons.append("large_attachment")
    if attachment_count >= 2:
        score += 2
        reasons.append("multi_attachment")
    if "video" in media_kinds:
        score += 3
        reasons.append("video_processing")
        caps.add("video")
    if "image" in media_kinds:
        caps.add("image")
    if _sentences(text) >= 3 or any(c in t for c in _MULTI_STEP_CONNECTORS):
        score += 2
        reasons.append("multi_step")
    if _words(text) > 80:
        score += 1
        reasons.append("long_request")

    # intent (أحد المدخلات، لا وحدها)
    if any(k in t for k in _GENERATION_TERMS):
        score += 2
        reasons.append("generation_or_render")
        caps.add("generation")
    if any(k in t for k in _EXTERNAL_TERMS):
        score += 2
        reasons.append("external_action")
        caps.add("external")
    if any(k in t for k in _AGENT_TERMS):
        score += 2
        reasons.append("agent_required")
        caps.add("research")

    classification = "BACKGROUND_TASK" if score >= THRESHOLD else "INLINE_RESPONSE"
    return {
        "classification": classification,
        "reasons": reasons,
        "score": score,
        "required_capabilities": sorted(caps),
        "estimated_execution_mode": "worker" if classification == "BACKGROUND_TASK" else "inline",
    }
