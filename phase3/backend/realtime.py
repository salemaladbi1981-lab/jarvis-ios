"""OpenAI Realtime WebSocket proxy + server-side tool orchestration (function calling).

Client → our WSS → this proxy → wss://api.openai.com/v1/realtime.
Keeps the API key server-side; supports barge-in via response.cancel pass-through.

Grounded Tool Contract (one real conversation):
user voice → Realtime model → function call → server executes email tool (Gmail) →
grounded ToolResult → function_call_output → SAME conversation → model speaks ONE grounded answer.

No auto-answer-then-interrupt workaround: the model's final answer is only produced AFTER the
tool result returns (function_call_output + response.create).
"""
import asyncio, json, os
import config
from realtime_tools import build_email_tools, execute_email_tool
from telegram_tools import TELEGRAM_TOOLS, execute_telegram_tool
from youtube_tools import YOUTUBE_TOOLS, execute_youtube_tool
from instagram_tools import INSTAGRAM_TOOLS, execute_instagram_tool
from maps_tools import MAPS_TOOLS, execute_maps_tool
from agent_runtime import AgentRuntime

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
    headers = {"Authorization": f"Bearer {config.OPENAI_API_KEY}"}

    # pending drafts — per-session confirmation gate (email + telegram منفصلان)
    pending_email = {}
    pending_tg = {}
    # agent runtime — one per session; routes tool calls to specialist agents
    runtime = AgentRuntime()
    active_agent_id = "core_coordinator"

    async with websockets.connect(url, additional_headers=headers) as upstream:
        session = dict(session_config) if session_config else {}
        session.setdefault("type", "realtime")
        session.setdefault("audio", {}).setdefault("output", {})["voice"] = config.REALTIME_VOICE
        inp = session.setdefault("audio", {}).setdefault("input", {})
        inp["transcription"] = {"model": "whisper-1"}
        inp["turn_detection"] = {"type": "semantic_vad", "interrupt_response": False, "create_response": True}
        session.setdefault("instructions", config.REALTIME_INSTRUCTIONS)
        # email tools + auto tool choice → the model can call them mid-turn
        session["tools"] = build_email_tools() + TELEGRAM_TOOLS + YOUTUBE_TOOLS + INSTAGRAM_TOOLS + MAPS_TOOLS
        session["tool_choice"] = "auto"
        await upstream.send(json.dumps({"type": "session.update", "session": session}))

        async def c2u():
            # client → upstream (pass-through; includes response.cancel for barge-in)
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
                pass

        async def u2c():
            # upstream → client, intercepting function calls for grounded execution
            nonlocal active_agent_id
            try:
                async for msg in upstream:
                    try:
                        d = json.loads(msg)
                    except Exception:
                        d = {}
                    t = d.get("type")
                    if t == "response.function_call_arguments.done":
                        call_id = d.get("call_id", "")
                        name = d.get("name", "")
                        try:
                            args = json.loads(d.get("arguments", "{}"))
                        except Exception:
                            args = {}
                        print(f"[TRACE tool] call {name} args={json.dumps(args)[:200]}", flush=True)
                        specialist = runtime.agent_for_tool(name)
                        if specialist != active_agent_id:
                            await client_ws.send_text(json.dumps(
                                runtime.event_payload("handoff", specialist, tool=name, from_agent=active_agent_id),
                                ensure_ascii=False))
                            active_agent_id = specialist
                        await client_ws.send_text(json.dumps(
                            runtime.event_payload("started", active_agent_id, tool=name),
                            ensure_ascii=False))
                        if name.startswith("telegram_"):
                            output = await asyncio.to_thread(execute_telegram_tool, name, args, pending_tg)
                        elif name.startswith("youtube_"):
                            output = await asyncio.to_thread(execute_youtube_tool, name, args)
                        elif name.startswith("instagram_"):
                            output = await asyncio.to_thread(execute_instagram_tool, name, args)
                        elif name.startswith("maps_"):
                            output = await asyncio.to_thread(execute_maps_tool, name, args)
                        else:
                            output = await asyncio.to_thread(execute_email_tool, name, args, pending_email)
                        print(f"[TRACE tool] {name} -> {json.dumps(output, ensure_ascii=False)[:200]}", flush=True)
                        await client_ws.send_text(json.dumps(
                            runtime.event_payload("finished", active_agent_id, tool=name),
                            ensure_ascii=False))
                        if active_agent_id != "core_coordinator":
                            await client_ws.send_text(json.dumps(
                                runtime.event_payload("handoff", "core_coordinator", tool=name, from_agent=active_agent_id),
                                ensure_ascii=False))
                            active_agent_id = "core_coordinator"
                        # Playback handoff: يفتح الفيديو في تطبيق YouTube الرسمي على الجهاز
                        # (event مخصص من السيرفر إلى العميل، قبل إرجاع النتيجة إلى النموذج).
                        if name == "youtube_play" and output.get("ok"):
                            handoff = {"type": "playback_handoff",
                                       "play_url": output.get("play_url", ""),
                                       "title": output.get("title", ""),
                                       "video_id": output.get("video_id", "")}
                            await client_ws.send_text(json.dumps(handoff, ensure_ascii=False))
                            print(f"[TRACE handoff] -> {output.get('play_url', '')}", flush=True)
                        if name == "maps_navigate" and output.get("ok"):
                            nav = {"type": "navigation_handoff",
                                   "maps_url": output.get("maps_url", ""),
                                   "destination": output.get("destination", "")}
                            await client_ws.send_text(json.dumps(nav, ensure_ascii=False))
                            print(f"[TRACE nav] -> {output.get('maps_url', '')}", flush=True)
                        # relay the function-call event (transparency) then feed the grounded result back
                        await client_ws.send_text(msg)
                        await upstream.send(json.dumps({
                            "type": "conversation.item.create",
                            "item": {"type": "function_call_output", "call_id": call_id,
                                     "output": json.dumps(output, ensure_ascii=False)},
                        }))
                        await upstream.send(json.dumps({"type": "response.create"}))
                        continue
                    try:
                        rid = ""
                        resp = d.get("response")
                        if isinstance(resp, dict):
                            rid = resp.get("id", "")
                        print(f"[TRACE u2c] {t} rid={rid}", flush=True)
                    except Exception:
                        pass
                    await client_ws.send_text(msg)
            except Exception:
                pass

        await asyncio.gather(c2u(), u2c(), return_exceptions=True)
