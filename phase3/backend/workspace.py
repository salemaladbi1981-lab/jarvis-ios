"""Workspace isolation — مساحات العمل الأربع + بوابة وصول server-side.

كل سجل (task/file/delivery/memory/conversation/agent execution/tool execution/
search/audit event) يجب أن يحمل workspace_id حقيقيًا.
لا cross-workspace retrieval افتراضيًا. QREC_LOCKED: عزل مستقل تمامًا.
"""
from __future__ import annotations

WORKSPACES = ["PERSONAL", "SALEM_AI_STUDIO", "VENTURES", "QREC_LOCKED"]
DEFAULT_WORKSPACE = "PERSONAL"
LOCKED_WORKSPACE = "QREC_LOCKED"


def is_valid(ws: str | None) -> bool:
    return ws in WORKSPACES


def authorize(session_workspace: str | None, requested: str | None) -> str | None:
    """يقرر المساحة المصرحة server-side. يُرجع workspace_id أو None (رفض).

    - المساحة المطلوبة يجب أن تكون صالحة.
    - QREC_LOCKED لا تُفتح إلا من جلسة مقفلة مستقلة (session_workspace == QREC_LOCKED).
    - لا قيمة افتراضية تمنح وصولًا عند غياب workspace_id (تُرفض).
    """
    if not requested or not is_valid(requested):
        return None
    if requested == LOCKED_WORKSPACE:
        return requested if session_workspace == LOCKED_WORKSPACE else None
    # المساحات العادية متاحة للمالك عبر أي جلسة (الطلب الصريح هو المحدد)
    return requested


def scoped(records: list[dict], workspace_id: str | None) -> list[dict]:
    """يرشح السجلات حسب workspace_id. بلا workspace_id → لا شيء (لا تسريب)."""
    if workspace_id is None:
        return []
    return [r for r in records if r.get("workspace_id") == workspace_id]


def owns(record: dict | None, workspace_id: str | None, user_id: str | None = None) -> bool:
    """يتحقق أن السجل يخص المساحة (والمستخدم إن حُدد). لا cross-workspace."""
    if not record:
        return False
    if workspace_id is None or record.get("workspace_id") != workspace_id:
        return False
    if user_id is not None and record.get("user_id") != user_id:
        return False
    return True
