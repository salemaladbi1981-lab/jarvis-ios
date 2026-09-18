"""jarvis_recall — استرجاع من الذاكرة الدائمة بلا تخمين.

أسئلة "وش كنا نتكلم عنه؟" / "وش قلت لك قبل؟" تستدعي هذه الأداة.
إذا لا يوجد دليل صريح → no_stored_context.
"""
from __future__ import annotations
import memory_bridge
import audit_memory

MEMORY_TOOLS = [
    {
        "type": "function",
        "name": "jarvis_recall",
        "description": (
            "Retrieve explicit stored context about the user from persistent memory "
            "(user memory + memory store files). Use for recall questions like 'what were we "
            "talking about?' / 'what did I tell you before?'. Returns evidence or no_stored_context. "
            "NEVER answer from guessing when no evidence is returned."
        ),
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "the thing to recall (a name, topic, or keyword)"},
        }, "required": ["query"]},
    },
]


def execute_memory_tool(name, args):
    if name != "jarvis_recall":
        return {"ok": False, "error": "unknown_tool"}
    query = (args.get("query", "") or "").strip()
    if not query:
        return {"ok": False, "error": "query_required"}
    r = memory_bridge.recall(query)
    ident = {"user_id": args.get("user_id", "salem-aladbi"), "session_id": "", "conversation_id": ""}
    audit_memory.log("recall_hit" if r["found"] else "recall_miss", ident, query=query[:120])
    return {"ok": True, **r}
