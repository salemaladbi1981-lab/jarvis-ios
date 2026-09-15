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
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1",
    }
    async with websockets.connect(url, additional_headers=headers) as upstream:
        # relay session config
        if session_config:
            await upstream.send(json.dumps({"type": "session.update", "session": session_config}))
        # bidirectional relay
        async def c2u():
            async for msg in client_ws:
                if msg.type == "websocket.receive":
                    txt = msg.get("text")
                    if txt is None:
                        continue
                    # pass-through (includes response.cancel for barge-in)
                    await upstream.send(txt)
        async def u2c():
            async for msg in upstream:
                await client_ws.send_text(msg)
        await asyncio.gather(c2u(), u2c(), return_exceptions=True)
