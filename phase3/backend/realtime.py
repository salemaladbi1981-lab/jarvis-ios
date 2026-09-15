"""OpenAI Realtime WebSocket proxy (server-to-server).
Client → our WSS → this proxy → wss://api.openai.com/v1/realtime.
Keeps the API key server-side; supports barge-in via response.cancel pass-through.
"""
import asyncio, json, os
import config

OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"

async def openai_realtime_proxy(client_ws, session_config: dict):
    if not config.OPENAI_API_KEY:
        await client_ws.send_json({"type": "error", "error": "no_openai_key"})
        return
    try:
        import websockets
    except ImportError:
        await client_ws.send_json({"type": "error", "error": "websockets_missing"})
        return

    url = f"{OPENAI_REALTIME_URL}?model={config.REALTIME_MODEL}"
    # GA Realtime API — no beta header required.
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
    }
    async with websockets.connect(url, additional_headers=headers) as upstream:
        # relay session config (voice persona + instructions)
        session = dict(session_config) if session_config else {}
        session.setdefault("type", "realtime")   # مطلوب في GA
        # GA: الصوت تحت audio.output.voice (وليس session.voice)
        session.setdefault("audio", {}).setdefault("output", {})["voice"] = config.REALTIME_VOICE
        session.setdefault("instructions", config.REALTIME_INSTRUCTIONS)
        await upstream.send(json.dumps({"type": "session.update", "session": session}))
        # bidirectional relay
        async def c2u():
            # client → upstream (pass-through, includes response.cancel for barge-in)
            try:
                while True:
                    txt = await client_ws.receive_text()
                    try:
                        d = json.loads(txt)
                        print(f"[TRACE c2u] {d.get('type')}", flush=True)
                    except Exception:
                        pass
                    await upstream.send(txt)
            except Exception:
                pass  # client disconnected

        async def u2c():
            # upstream → client (session events, audio/text deltas)
            try:
                async for msg in upstream:
                    try:
                        d = json.loads(msg)
                        rid = ""
                        resp = d.get("response")
                        if isinstance(resp, dict):
                            rid = resp.get("id", "")
                        elif isinstance(d.get("response_id"), str):
                            rid = d.get("response_id")
                        print(f"[TRACE u2c] {d.get('type')} rid={rid}", flush=True)
                    except Exception:
                        pass
                    await client_ws.send_text(msg)
            except Exception:
                pass

        await asyncio.gather(c2u(), u2c(), return_exceptions=True)
