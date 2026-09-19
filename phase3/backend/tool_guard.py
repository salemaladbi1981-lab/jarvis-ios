"""Tool Guard — منع تقني عند حدود التنفيذ (execution-boundary enforcement).

الأفعال غير القابلة للعكس (إرسال/دفع/حجز/حذف/توقيع) ممنوعة تقنيًا بلا موافقة ملزمة صالحة.
هذا gate يُستدعى عند حدود التنفيذ (dispatch)، لا كمجرد تعليمة prompt.
"""
from __future__ import annotations

# أفعال غير قابلة للعكس — تتطلب موافقة ملزمة (approval) قبل التنفيذ.
SENSITIVE_TOOLS = {"email_send", "telegram_send", "payment", "booking", "delete", "sign"}


def check(tool_name: str, approval: dict | None = None) -> dict:
    """يتحقق عند حدود التنفيذ. sensitive بلا موافقة صالحة → ممنوع.

    approval = {"valid": bool, "approval_id": str} (من ApprovalStore بعد الاستهلاك الناجح).
    """
    if tool_name in SENSITIVE_TOOLS:
        if not approval or not approval.get("valid"):
            return {"allowed": False, "reason": "approval_required"}
    return {"allowed": True, "reason": ""}


def is_sensitive(tool_name: str) -> bool:
    return tool_name in SENSITIVE_TOOLS
