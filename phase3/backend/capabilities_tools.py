"""jarvis_capabilities — أداة عرض القدرات المنظمة (بدل hundreds من raw skills)."""
from __future__ import annotations
import capabilities

CAPABILITIES_TOOLS = [
    {
        "type": "function",
        "name": "jarvis_capabilities",
        "description": (
            "Return JARVIS's organized user-facing capabilities (a clean list, NOT raw skills). "
            "Use for 'what can you do?' / 'وش تقدر تسوي؟' questions. "
            "Pass capability_id to get one capability's underlying skills."
        ),
        "parameters": {"type": "object", "properties": {
            "capability_id": {"type": "string", "description": "optional: get details + underlying skills of one capability"},
        }, "required": []},
    },
]


def execute_capabilities_tool(name, args):
    if name != "jarvis_capabilities":
        return {"ok": False, "error": "unknown_tool"}
    cid = (args.get("capability_id") or "").strip()
    if cid:
        c = capabilities.get_capability(cid)
        if not c:
            return {"ok": False, "error": "unknown_capability"}
        return {"ok": True, "capability": c}
    return {"ok": True, **capabilities.answer_what_can_you_do()}
