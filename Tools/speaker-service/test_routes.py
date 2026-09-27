"""Exercise the real authentication bridge with an ASGI request, no network."""
import asyncio, importlib.util, json, sys, types
from fastapi import FastAPI, Header, HTTPException
sys.modules["auth"] = types.SimpleNamespace(PRIMARY_USER_ID="owner")
spec = importlib.util.spec_from_file_location("speaker_routes", sys.argv[1])
routes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(routes)
app = FastAPI()
def user(x_jarvis_session: str = Header(default="")):
    if not x_jarvis_session: raise HTTPException(401)
    return x_jarvis_session
def workspace(x_jarvis_workspace: str = Header(default="PERSONAL")):
    return x_jarvis_workspace
routes.install_routes(app, user, workspace)
routes._worker = lambda path, data=None: {"enabled":True,"matched":True,"score":0.99}
async def request(path, token="", workspace="PERSONAL", data=b""):
    output=[]
    headers=[(b"x-jarvis-workspace",workspace.encode())]
    if token: headers.append((b"x-jarvis-session",token.encode()))
    scope={"type":"http","asgi":{"version":"3.0"},"method":"POST" if path.endswith("verify") else "GET",
           "path":path,"raw_path":path.encode(),"query_string":b"","headers":headers,
           "scheme":"http","server":("test",80),"client":("test",123),"http_version":"1.1"}
    async def receive(): return {"type":"http.request","body":data,"more_body":False}
    async def send(message): output.append(message)
    await app(scope,receive,send)
    status=next(x["status"] for x in output if x["type"]=="http.response.start")
    body=b"".join(x.get("body",b"") for x in output if x["type"]=="http.response.body")
    return status,json.loads(body)
async def test():
    cases=[
      ("unauthenticated", await request("/voice/owner/status"),401),
      ("different user", await request("/voice/owner/status","other"),403),
      ("wrong workspace", await request("/voice/owner/status","owner","QREC_LOCKED"),403),
      ("owner status", await request("/voice/owner/status","owner"),200),
      ("short audio", await request("/voice/owner/verify","owner",data=b"x"),422),
      ("oversized audio", await request("/voice/owner/verify","owner",data=bytes(153602)),413),
      ("valid wire audio", await request("/voice/owner/verify","owner",data=bytes(96000)),200),
    ]
    for name,(status,body),expected in cases:
        assert status==expected,(name,status,body)
        print("PASS",name)
    assert cases[-1][1][1]=={"matched":True}
    routes._worker=lambda *args: {"reason":"unavailable"}
    assert (await request("/voice/owner/verify","owner",data=bytes(96000)))[1]=={"matched":False}
    print("PASS unavailable verifier fails closed")
asyncio.run(test())
