"""OpenAI Realtime WebSocket proxy + server-side tool orchestration (function calling).

Client → our WSS → this proxy → wss://api.openai.com/v1/realtime.
Keeps the API key server-side; supports barge-in via response.cancel pass-through.

Grounded Tool Contract (one real conversation):
user voice → Realtime model → function call → server executes tool →
grounded ToolResult → function_call_output → SAME conversation → model speaks ONE grounded answer.

Stability fixes (Sep 2026):
- Tool execution runs in a SEPARATE asyncio task (not inline in the u2c loop) so the
  upstream read/forward loop keeps flowing audio + interruption events during a slow tool.
- A per-session "turn generation" increments on response.cancel (barge-in); a tool result
  that arrives after its turn was cancelled is NOT fed into a fresh response.create.
- No bare `except: pass` — structured trace logging (no personal content / tokens / audio).
"""
import asyncio, json, time
import config
from realtime_tools import build_email_tools, execute_email_tool
from telegram_tools import TELEGRAM_TOOLS, execute_telegram_tool
from youtube_tools import YOUTUBE_TOOLS, execute_youtube_tool
from instagram_tools import INSTAGRAM_TOOLS, execute_instagram_tool
from maps_tools import MAPS_TOOLS, execute_maps_tool
from brain_tools import BRAIN_TOOLS, execute_brain_tool
from memory_tools import MEMORY_TOOLS, execute_memory_tool
from capabilities_tools import CAPABILITIES_TOOLS, execute_capabilities_tool
from agent_tools import AGENT_TOOLS, execute_agent_tool
from agent_runtime import AgentRuntime

OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"


def _trace(tag, msg):
    # أحداث وأزمنة فقط — لا نصوص محادثة ولا صوت ولا توكنات ولا إحداثيات دقيقة.
    print(f"[TRACE {tag}] {msg}", flush=True)


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
    active_agent = {"id": "core_coordinator"}
    # turn generation: يزداد عند response.cancel (barge-in) → يُبطل نتائج الأدوات المتأخرة
    turn_generation = {"n": 0}

    async with websockets.connect(url, additional_headers=headers) as upstream:
        session = dict(session_config) if session_config else {}
        session.setdefault("type", "realtime")
        session.setdefault("audio", {}).setdefault("output", {})["voice"] = config.REALTIME_VOICE
        inp = session.setdefault("audio", {}).setdefault("input", {})
        inp["transcription"] = {"model": "whisper-1", "language": "ar"}
        # VAD: server_vad لأن semantic_vad تجاهل create_response=false وأعاده true في
        # session.updated (دليل console-session5) — فكان السيرفر يُنشئ رداً بعد كل commit.
        # الرد يُطلب صراحةً من العميل بعد أن تأخذ أدوات الجهاز حقها، والمقاطعة عبر response.cancel.
        inp["turn_detection"] = {"type": "server_vad", "threshold": 0.6, "prefix_padding_ms": 300, "silence_duration_ms": 500, "create_response": False, "interrupt_response": False}
        session.setdefault("instructions", config.REALTIME_INSTRUCTIONS)
        session["tools"] = build_email_tools() + TELEGRAM_TOOLS + YOUTUBE_TOOLS + INSTAGRAM_TOOLS + MAPS_TOOLS + BRAIN_TOOLS + MEMORY_TOOLS + CAPABILITIES_TOOLS + AGENT_TOOLS
        session["tool_choice"] = "auto"
        await upstream.send(json.dumps({"type": "session.update", "session": session}))

        def dispatch_tool(name, args):
            # توزيع تنفيذ الأداة حسب البادئة — لا نص query داخل السجل.
            if name == "jarvis_brain":
                return execute_brain_tool(name, args)
            if name == "jarvis_recall":
                return execute_memory_tool(name, args)
            if name == "jarvis_capabilities":
                return execute_capabilities_tool(name, args)
            if name == "jarvis_agent":
                return execute_agent_tool(name, args)
            if name.startswith("telegram_"):
                return execute_telegram_tool(name, args, pending_tg)
            if name.startswith("youtube_"):
                return execute_youtube_tool(name, args)
            if name.startswith("instagram_"):
                return execute_instagram_tool(name, args)
            if name.startswith("maps_"):
                return execute_maps_tool(name, args)
            return execute_email_tool(name, args, pending_email)

        async def c2u():
            # client → upstream (pass-through؛ يشمل response.cancel للـ barge-in)
            while True:
                try:
                    txt = await client_ws.receive_text()
                except Exception as e:
                    _trace("c2u", f"client receive ended ({type(e).__name__})")
                    return
                try:
                    d = json.loads(txt)
                    t = d.get("type")
                    if t == "response.cancel":
                        turn_generation["n"] += 1
                        _trace("c2u", f"response.cancel → turn_generation={turn_generation['n']}")
                    else:
                        _trace("c2u", f"{t}")
                except Exception as e:
                    _trace("c2u", f"unparseable client message ({type(e).__name__})")
                try:
                    await upstream.send(txt)
                except Exception as e:
                    _trace("c2u", f"upstream send failed ({type(e).__name__})")
                    return

        async def execute_tool_and_respond(name, args, call_id, gen, specialist):
            t0 = time.monotonic()
            _trace("tool", f"start {name} (call_id={call_id[:12]})")
            try:
                output = await asyncio.to_thread(dispatch_tool, name, args)
            except Exception as e:
                output = {"ok": False, "error": type(e).__name__}
                _trace("tool", f"{name} raised {type(e).__name__}")
            _trace("tool", f"end {name} ok={output.get('ok')} in {int((time.monotonic()-t0)*1000)}ms")
            # finished + handoff-back (واجهة العميل)
            await client_ws.send_text(json.dumps(
                runtime.event_payload("finished", specialist, tool=name), ensure_ascii=False))
            if specialist != "core_coordinator":
                await client_ws.send_text(json.dumps(
                    runtime.event_payload("handoff", "core_coordinator", tool=name, from_agent=specialist),
                    ensure_ascii=False))
                active_agent["id"] = "core_coordinator"
            # Playback handoff: يفتح الفيديو في تطبيق YouTube الرسمي
            if name == "youtube_play" and output.get("ok"):
                handoff = {"type": "playback_handoff",
                           "play_url": output.get("play_url", ""),
                           "title": output.get("title", ""),
                           "video_id": output.get("video_id", "")}
                await client_ws.send_text(json.dumps(handoff, ensure_ascii=False))
                _trace("handoff", f"youtube_play -> ok")
            if name == "maps_navigate" and output.get("ok"):
                nav = {"type": "navigation_handoff",
                       "maps_url": output.get("maps_url", ""),
                       "destination": output.get("destination", "")}
                await client_ws.send_text(json.dumps(nav, ensure_ascii=False))
                _trace("nav", f"maps_navigate -> ok")
            # grounded result back to the model (نفس المحادثة)
            await upstream.send(json.dumps({
                "type": "conversation.item.create",
                "item": {"type": "function_call_output", "call_id": call_id,
                         "output": json.dumps(output, ensure_ascii=False)},
            }))
            # لا نبدأ ردًا جديدًا إذا أُلغي الدور أثناء تنفيذ الأداة
            if gen == turn_generation["n"]:
                await upstream.send(json.dumps({"type": "response.create"}))
            else:
                _trace("tool", f"{name} result arrived after cancel (gen={gen}, now={turn_generation['n']}) — skip response.create")

        async def u2c():
            # upstream → client، مع اعتراض function calls للتنفيذ grounded (بمهمة منفصلة لا تعيق القراءة)
            async for msg in upstream:
                if isinstance(msg, bytes):
                    try:
                        await client_ws.send_bytes(msg)
                    except Exception as e:
                        _trace("u2c", f"client send_bytes failed ({type(e).__name__})")
                    continue
                try:
                    d = json.loads(msg)
                except Exception as e:
                    _trace("u2c", f"unparseable upstream message ({type(e).__name__})")
                    continue
                t = d.get("type")
                if t == "response.function_call_arguments.done":
                    call_id = d.get("call_id", "")
                    name = d.get("name", "")
                    try:
                        args = json.loads(d.get("arguments", "{}"))
                    except Exception:
                        args = {}
                    _trace("tool", f"call {name} (call_id={call_id[:12]})")
                    specialist = runtime.agent_for_tool(name)
                    if specialist != active_agent["id"]:
                        await client_ws.send_text(json.dumps(
                            runtime.event_payload("handoff", specialist, tool=name, from_agent=active_agent["id"]),
                            ensure_ascii=False))
                        active_agent["id"] = specialist
                    await client_ws.send_text(json.dumps(
                        runtime.event_payload("started", active_agent["id"], tool=name),
                        ensure_ascii=False))
                    # relay the function-call event (transparency) ثم نفّذ في مهمة منفصلة
                    await client_ws.send_text(msg)
                    gen = turn_generation["n"]
                    asyncio.create_task(execute_tool_and_respond(name, args, call_id, gen, active_agent["id"]))
                    continue
                rid = ""
                resp = d.get("response")
                if isinstance(resp, dict):
                    rid = resp.get("id", "")
                if t != "response.output_audio.delta":
                    _trace("u2c", f"{t} rid={rid[:12]}")
                await client_ws.send_text(msg)

        await asyncio.gather(c2u(), u2c(), return_exceptions=True)
