"""Deep-link canonical: jarvis://conversation/{id} و jarvis://task/{id}.

الرابط يحمل معرفًا آمنًا فقط (لا بيانات حساسة). الـresolve يتحقق من الملكية server-side.
"""
from __future__ import annotations
import conversation, tasks as tasks_mod

SCHEME = "jarvis"


def conversation_link(conversation_id: str) -> str:
    return f"{SCHEME}://conversation/{conversation_id}"


def task_link(task_id: str) -> str:
    return f"{SCHEME}://task/{task_id}"


def parse(uri: str) -> dict | None:
    """يُعيد {kind: conversation|task, id} أو None إذا صيغة غير صالحة."""
    if not uri or not uri.startswith(f"{SCHEME}://"):
        return None
    body = uri[len(f"{SCHEME}://"):]
    parts = body.split("/")
    if len(parts) != 2 or not parts[1]:
        return None
    kind, ident = parts[0], parts[1]
    if kind not in ("conversation", "task"):
        return None
    return {"kind": kind, "id": ident}


def resolve_target(uri: str, user_id: str, workspace_id: str | None = None) -> dict | None:
    """يتحقق أن الهدف موجود ويملكه المستخدم/المساحة. None إذا لا وصول."""
    p = parse(uri)
    if not p:
        return None
    if p["kind"] == "conversation":
        conv = conversation.ConversationStore().get(p["id"], user_id, workspace_id)
        return {"kind": "conversation", "id": p["id"], "record": conv} if conv else None
    if p["kind"] == "task":
        t = tasks_mod.get_task(p["id"], user_id, workspace_id)
        return {"kind": "task", "id": p["id"], "record": t} if t else None
    return None
