"""اختبارات AUTH/IDENTITY: هوية server-side + منع impersonation."""
import sys, os, shutil
os.environ["JARVIS_SESSIONS"] = "/tmp/jarvis-auth-test/sessions.json"
shutil.rmtree("/tmp/jarvis-auth-test", ignore_errors=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auth
from fastapi import HTTPException

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS" if cond else "FAIL"), name, detail)

# 1) لا session → مرفوض (resolve None)
check("no_session_resolves_none", auth.resolve_user(None) is None, "")
check("empty_session_resolves_none", auth.resolve_user("") is None, "")
check("fake_token_resolves_none", auth.resolve_user("deadbeef-fake") is None, "")

# 2) session موثّق → يرجّع user_id server-side
sid_a = auth.create_session("salem-aladbi")
check("valid_session_resolves_user", auth.resolve_user(sid_a) == "salem-aladbi", "")

# 3) impersonation: توكن لـ other-user لا يعطي هوية salem-aladbi مهما ادّعى العميل
sid_b = auth.create_session("other-user")
check("impersonation_session_identity_wins", auth.resolve_user(sid_b) == "other-user"
      and auth.resolve_user(sid_b) != "salem-aladbi", "")

# 4) get_user_id (الـ dependency الحقيقي) يرفض بدون session
from main import get_user_id
try:
    get_user_id("")
    check("get_user_id_rejects_no_session", False, "no exception")
except HTTPException as e:
    check("get_user_id_rejects_no_session", e.status_code == 401, f"status={e.status_code}")

try:
    get_user_id("forged-token")
    check("get_user_id_rejects_forged", False, "no exception")
except HTTPException as e:
    check("get_user_id_rejects_forged", e.status_code == 401, f"status={e.status_code}")

# 5) session موثّق يمرّ عبر الـ dependency
check("get_user_id_accepts_valid_session", get_user_id(sid_a) == "salem-aladbi", "")
check("get_user_id_session_identity_not_spoofable", get_user_id(sid_b) == "other-user", "")

passed = sum(1 for _, c, _ in results if c)
print(f"\n=== {passed}/{len(results)} PASS ===")
sys.exit(0 if passed == len(results) else 1)
