"""WebSocket handshake integration test — يتصل بالـ wss://jarvis-api.qeyas.app/realtime
ويتحقق أن الـ handshake ينجح و session.created يصل (مطابق لمسار iOS).
"""
import asyncio, json, ssl, sys, os

URL = os.environ.get("JARVIS_REALTIME_URL", "wss://jarvis-api.qeyas.app/realtime")

async def test():
    try:
        import websockets
    except ImportError:
        print("SKIP — websockets غير مثبت (يتطلب .venv)")
        return True  # لا نفشل إن لم يتوفر client في البيئة الحالية

    print("connecting:", URL)
    try:
        async with websockets.connect(URL, ssl=ssl.create_default_context(), open_timeout=15) as ws:
            print("PASS  handshake OK (101 upgrade)")
            # أول event يجب أن يكون session.created (أو session.updated بعد relay)
            types = []
            try:
                for _ in range(3):
                    msg = await asyncio.wait_for(ws.recv(), timeout=10)
                    t = json.loads(msg).get("type", "?")
                    types.append(t)
                    if t == "session.created":
                        break
            except asyncio.TimeoutError:
                pass
            print("events:", types)
            if "session.created" in types:
                print("PASS  session.created received")
                print("\n== RESULT: PASS ==")
                return True
            else:
                print("FAIL  session.created لم يصل (events=%s)" % types)
                print("\n== RESULT: FAIL ==")
                return False
    except Exception as e:
        print("FAIL  handshake:", type(e).__name__, str(e)[:200])
        print("\n== RESULT: FAIL ==")
        return False

ok = asyncio.run(test())
sys.exit(0 if ok else 1)
