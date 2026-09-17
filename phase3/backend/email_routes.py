"""Email routes — additive. No impact on /realtime voice proxy."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import gmail_tools

router = APIRouter(prefix="/email", tags=["email"])


class SendReq(BaseModel):
    to: str
    subject: str = ""
    body: str


@router.get("/summary")
def email_summary(limit: int = 10, q: str = None):
    try:
        return {"ok": True, "emails": gmail_tools.summary(limit=limit, q=q)}
    except Exception as e:
        raise HTTPException(502, f"gmail_failed: {type(e).__name__}")


@router.get("/read")
def email_read(id: str):
    try:
        return {"ok": True, "message": gmail_tools.read_message(id)}
    except Exception as e:
        raise HTTPException(502, f"gmail_failed: {type(e).__name__}")


@router.get("/search")
def email_search(q: str, limit: int = 20):
    try:
        return {"ok": True, "emails": gmail_tools.search(q, limit=limit)}
    except Exception as e:
        raise HTTPException(502, f"gmail_failed: {type(e).__name__}")


@router.post("/send")
def email_send(req: SendReq):
    if not req.to or not req.body:
        raise HTTPException(400, "to and body required")
    try:
        r = gmail_tools.send(req.to, req.subject, req.body)
        return {"ok": True, "message_id": r.get("id"), "thread_id": r.get("threadId")}
    except Exception as e:
        raise HTTPException(502, f"send_failed: {type(e).__name__}")
