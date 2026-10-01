"""jarvis_recall — استرجاع من الذاكرة الدائمة بلا تخمين.

يحمل هوية كاملة (user_id/session_id/conversation_id/memory_namespace)
ويستخدمها في scoping + retrieval + audit.
"""
from __future__ import annotations
import identity
import memory_bridge
import audit_memory

MEMORY_TOOLS = [
    {
        "type": "function",
        "name": "jarvis_recall",
        "description": (
            "Retrieve explicit stored context about the user from persistent memory "
            "(user memory + memory store files + persisted conversation log). "
            "Use for recall questions like 'what were we talking about?' / 'what did I tell you?'. "
            "Returns evidence or no_stored_context. NEVER answer from guessing."
        ),
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "the thing to recall (a name, topic, or keyword)"},
            "user_id": {"type": "string", "description": "stable user identity (default: salem-aladbi)"},
            "session_id": {"type": "string", "description": "stable id for the active session"},
            "conversation_id": {"type": "string", "description": "stable id for this conversation"},
            "memory_namespace": {"type": "string", "description": "memory scope tied to user+conversation"},
        }, "required": ["query"]},
    },
]


def execute_memory_tool(name, args):
    if name != "jarvis_recall":
        return {"ok": False, "error": "unknown_tool"}
    query = (args.get("query", "") or "").strip()
    if not query:
        return {"ok": False, "error": "query_required"}

    ident = identity.from_args(args).to_dict()
    r = memory_bridge.recall(query, ident)
    query_type = "recall" if memory_bridge._is_recall_query(query) else "keyword"
    audit_memory.log(
        "recall_hit" if r["found"] else "recall_miss",
        ident,
        query=query,
        query_type=query_type,
    )
    return {"ok": True, "identity": ident, "query_type": query_type, **r}


def personal_memory_queries(text):
    """Narrow personal-recall intents; ordinary tasks still go to the brain."""
    q = text.strip().casefold()
    if any(phrase in q for phrase in ("what is my name", "what's my name", "وش اسمي", "ما اسمي", "تعرف اسمي")):
        return ["الاسم", "اسمي", "name"]
    if any(phrase in q for phrase in ("what do you know about me", "وش تعرف عني", "ماذا تعرف عني",
                                     "what were we", "what did i tell", "وش كنا", "كنا نتكلم", "وش قلت لك")):
        return ["what were we discussing"]
    return None


def answer_personal_memory(text, ident):
    """Return only backend evidence, or an explicit miss. Never synthesize a fact."""
    queries = personal_memory_queries(text)
    if queries is None:
        return None
    snippets = []
    for query in queries:
        result = execute_memory_tool("jarvis_recall", {"query": query, **ident})
        for evidence in result.get("evidence", []):
            snippet = evidence.get("snippet")
            if snippet and snippet not in snippets:
                snippets.append(snippet)
    if not snippets:
        return "لا أملك معلومات محفوظة موثّقة تجيب عن ذلك في مساحة العمل الحالية."
    return "من السجل المحفوظ في مساحة العمل الحالية:\n" + "\n".join("• " + s for s in snippets[:5])
