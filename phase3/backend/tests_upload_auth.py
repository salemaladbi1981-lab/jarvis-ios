"""اختبارات أمن الرفع (cross-user) + session bootstrap."""
import sys, os, shutil, hashlib
os.environ["JARVIS_STORAGE_ROOT"] = "/tmp/jarvis-upload-auth-test"
os.environ["JARVIS_SESSIONS"] = "/tmp/jarvis-upload-auth-test/sessions.json"
os.environ["JARVIS_BOOTSTRAP_KEY"] = "test-bootstrap-secret-123"
shutil.rmtree("/tmp/jarvis-upload-auth-test", ignore_errors=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import storage, files_api, auth

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS" if cond else "FAIL"), name, detail)

A, B = "salem-aladbi", "other-user"

# A يبدأ رفع
data = b"SECRET-UPLOAD-DATA-12345"
chk = hashlib.sha256(data).hexdigest()
meta = files_api.init_upload(A, "secret.bin", "application/octet-stream", len(data), chk, "conv-a", "sess-a")
upload_id = meta["upload_id"]

# B يحاول part/status/complete على upload يخص A
r = files_api.upload_part(upload_id, 0, data, "", B)
check("B_cannot_upload_part", r["ok"] is False and r["error"] == "forbidden", f"err={r.get('error')}")
r = files_api.upload_status(upload_id, B)
check("B_cannot_see_status", r["ok"] is False and r["error"] == "forbidden", f"err={r.get('error')}")
r = files_api.complete_upload(upload_id, B)
check("B_cannot_complete", r["ok"] is False and r["error"] == "forbidden", f"err={r.get('error')}")

# A يرفع/يكمل بنجاح
check("A_can_upload_part", files_api.upload_part(upload_id, 0, data, "", A)["ok"] is True, "")
check("A_can_see_status", files_api.upload_status(upload_id, A)["ok"] is True, "")
done = files_api.complete_upload(upload_id, A)
check("A_can_complete", done["ok"] is True and done["file"]["checksum"] == chk, "")

# session bootstrap (server-side، العميل لا يختار user_id)
tok = auth.bootstrap("test-bootstrap-secret-123")
check("bootstrap_issues_token", tok is not None and auth.resolve_user(tok) == "salem-aladbi", "")
check("bootstrap_rejects_bad_proof", auth.bootstrap("wrong-secret") is None, "")
check("bootstrap_rejects_empty_proof", auth.bootstrap("") is None, "")

passed = sum(1 for _, c, _ in results if c)
print(f"\n=== {passed}/{len(results)} PASS ===")
sys.exit(0 if passed == len(results) else 1)
