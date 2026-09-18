"""اختبارات Secure enrollment (pairing code لمرة واحدة)."""
import sys, os, shutil, time
os.environ["JARVIS_SESSIONS"] = "/tmp/jarvis-enroll-test/sessions.json"
os.environ["JARVIS_ENROLL"] = "/tmp/jarvis-enroll-test/enroll.json"
shutil.rmtree("/tmp/jarvis-enroll-test", ignore_errors=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auth

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS" if cond else "FAIL"), name, detail)

# 1) رمز صالح → session token للمستخدم الأساسي
code = auth.create_enrollment_code(ttl_seconds=600)
tok = auth.redeem_enrollment(code)
check("enroll_issues_session", tok is not None and auth.resolve_user(tok) == "salem-aladbi", "")

# 2) رمز لمرة واحدة فقط
check("enroll_single_use", auth.redeem_enrollment(code) is None, "")

# 3) رمز غير صالح مرفوض
check("enroll_rejects_bad_code", auth.redeem_enrollment("nonexistent-code") is None, "")

# 4) انتهاء الصلاحية
expired = auth.create_enrollment_code(ttl_seconds=0)
time.sleep(0.05)
check("enroll_expires", auth.redeem_enrollment(expired) is None, "")

# 5) رمزان مختلفان مستقلان
c1 = auth.create_enrollment_code()
c2 = auth.create_enrollment_code()
check("enroll_codes_unique", c1 != c2, "")
check("enroll_redeem_c2_works", auth.redeem_enrollment(c2) is not None, "")

passed = sum(1 for _, c, _ in results if c)
print(f"\n=== {passed}/{len(results)} PASS ===")
sys.exit(0 if passed == len(results) else 1)
