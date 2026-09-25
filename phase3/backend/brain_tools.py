"""jarvis_brain — delegate deep requests to the Hermes agent (skills/agents/memory/web).

الـ API_SERVER_KEY يُقرأ من env فقط (config.API_SERVER_KEY) — لا hardcode ولا logs ولا إرسال للعميل.
"""
import json
import urllib.request
import config
import identity
import audit_memory

BRAIN_TIMEOUT = 180  # Hermes run قد يستغرق دقائق لمهام معقدة

BRAIN_TOOLS = [
    {
        "type": "function",
        "name": "jarvis_brain",
        "description": (
            "Delegate a request to the full JARVIS brain (Hermes agent) which has 370+ skills, "
            "agents, memory, and live web access. Use ONLY for requests beyond the local fast tools "
            "(email/telegram/youtube/instagram/maps): research, current/real-time info, content creation, "
            "travel/flights planning, analysis, creative/editorial tasks, or any skill-based work. "
            "Pass the user's request verbatim as 'query'."
        ),
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "the user's full request (Arabic or English)"},
            "user_id": {"type": "string", "description": "stable user identity (default: salem-aladbi)"},
            "session_id": {"type": "string", "description": "stable id for the active session"},
            "conversation_id": {"type": "string", "description": "stable id for this conversation"},
            "memory_namespace": {"type": "string", "description": "memory scope tied to user+conversation"},
        }, "required": ["query"]},
    },
]


def execute_brain_tool(name, args):
    if name != "jarvis_brain":
        return {"ok": False, "error": "unknown_tool"}
    query = (args.get("query", "") or "").strip()
    if not query:
        return {"ok": False, "error": "query_required"}
    key = config.API_SERVER_KEY
    if not key:
        return {"ok": False, "error": "hermes_key_missing"}
    ident = identity.from_args(args)
    sys_msg = (f"Identity: user_id={ident.user_id}, workspace_id={ident.workspace_id}, conversation_id={ident.conversation_id}, "
               f"memory_namespace={ident.memory_namespace}. "
               "Use only verified memory from this user and workspace. Never use seeded/demo context "
               "or another workspace. If no stored evidence exists, say you do not have that memory.")
    body = json.dumps({
        "model": "hermes-agent",
        "messages": [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": query},
        ],
    }).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + key,
        **ident.to_headers(),
    }
    req = urllib.request.Request(config.JARVIS_HERMES_API_URL, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=BRAIN_TIMEOUT) as r:
            d = json.loads(r.read())
    except Exception as e:
        return {"ok": False, "error": type(e).__name__}
    try:
        answer = d["choices"][0]["message"]["content"]
    except Exception:
        return {"ok": False, "error": "bad_hermes_response"}
    audit_memory.log("brain_delegate", ident.to_dict(), query=query, query_type="brain")
    return {"ok": True, "answer": answer, "identity": ident.to_dict()}
