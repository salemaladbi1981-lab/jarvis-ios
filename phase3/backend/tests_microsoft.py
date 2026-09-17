"""Microsoft/Hotmail Provider — deterministic tests (provider routing, OAuth URL, mixed Gmail+Microsoft)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from email_accounts import EmailAccount, make_provider
from email_provider import GmailProvider, MicrosoftProvider
from realtime_tools import execute_email_tool
from test_fakes import fake_registry, FakeProvider

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")

# 1) make_provider routing (gmail vs microsoft/outlook/hotmail)
check("make_provider gmail → GmailProvider", isinstance(make_provider(EmailAccount("a","A","gmail","x@y.com","/tmp/t.json")), GmailProvider))
check("make_provider microsoft → MicrosoftProvider", isinstance(make_provider(EmailAccount("a","A","microsoft","x@y.com","/tmp/t.json")), MicrosoftProvider))
check("make_provider outlook → MicrosoftProvider", isinstance(make_provider(EmailAccount("a","A","outlook","x@y.com","/tmp/t.json")), MicrosoftProvider))
check("make_provider hotmail → MicrosoftProvider", isinstance(make_provider(EmailAccount("a","A","hotmail","x@y.com","/tmp/t.json")), MicrosoftProvider))

# 2) ms_oauth build_auth_url + scopes
os.environ["MS_CLIENT_ID"] = "test-cid"
os.environ["MS_CLIENT_SECRET"] = "test-sec"
import ms_oauth
u = ms_oauth.build_auth_url("work:Work")
check("ms_oauth auth url has client_id", "client_id=test-cid" in u)
check("ms_oauth auth url has redirect_uri", "redirect_uri=" in u)
check("ms_oauth auth url has scopes", "Mail.ReadWrite" in u and "Mail.Send" in u and "offline_access" in u)
check("ms_oauth is_configured True (with creds)", ms_oauth.is_configured())

# 3) Unified summary عبر Gmail + Microsoft (mixed providers, fake injected)
reg = fake_registry([
    ("personal", "Personal", "me@gmail.com",
     {"m1": {"from": "friend@x.com", "subject": "Gmail note", "body": "from gmail"}}),
    ("work", "Work", "me@hotmail.com",
     {"w1": {"from": "boss@x.com", "subject": "Hotmail note", "body": "from hotmail"}}),
])
r = execute_email_tool("email_summary", {"limit": 5}, {}, reg)
aids = {e["account_id"] for e in r.get("emails", [])}
check("mixed summary returns both accounts", {"personal", "work"} <= aids)
check("mixed summary tags account (display name)", all(e.get("account") for e in r.get("emails", [])))

# 4) cross-account send protection بين Gmail و Microsoft
pending = {}
execute_email_tool("email_draft_reply", {"account_id": "personal", "message_id": "m1", "body": "hi"}, pending, reg)
r = execute_email_tool("email_send", {"confirmed": True, "account_id": "work"}, pending, reg)
check("send from wrong account (gmail→hotmail) → account_mismatch", r.get("ok") is False and r.get("error") == "account_mismatch")
check("blocked send → pending intact", "draft" in pending)
check("blocked send → hotmail provider not used", len(reg._providers["work"].sent) == 0)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
