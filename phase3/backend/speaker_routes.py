"""Authenticated owner-only bridge to the private speaker verifier."""
import asyncio
import json
import urllib.request
from fastapi import Depends, HTTPException, Request
import auth


def _worker(path, data=None):
    try:
        request = urllib.request.Request(
            "http://127.0.0.1:18010/" + path,
            data=data,
            headers={"Content-Type": "application/octet-stream"},
        )
        with urllib.request.urlopen(request, timeout=2.0) as response:
            return json.loads(response.read(4096))
    except Exception:
        return {"enabled": False, "matched": False, "reason": "unavailable"}


def install_routes(app, get_user_id, get_workspace):
    def require_owner(user_id=Depends(get_user_id), workspace_id=Depends(get_workspace)):
        if user_id != auth.PRIMARY_USER_ID or workspace_id != "PERSONAL":
            raise HTTPException(403, "owner_voice_forbidden")

    @app.get("/voice/owner/status", dependencies=[Depends(require_owner)])
    async def status():
        return await asyncio.to_thread(_worker, "status")

    @app.post("/voice/owner/verify", dependencies=[Depends(require_owner)])
    async def verify(request: Request):
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > 153600:
                raise HTTPException(413, "audio_too_large")
        if len(data) < 76800 or len(data) % 2:
            raise HTTPException(422, "invalid_audio")
        result = await asyncio.to_thread(_worker, "verify", bytes(data))
        # Only the decision leaves the private worker, never the embedding or score.
        return {"matched": result.get("matched") is True}
