"""اختبارات PHASE B: Capability Registry (مع status model + validation)."""
import sys, os
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capabilities, capabilities_tools

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS" if cond else "FAIL"), name, detail)

doc = capabilities.load()

# 1) 375 مهارة مغطاة بالكامل
total = sum(c["skill_count"] for c in doc["capabilities"])
check("all_375_skills_mapped", total == 375, f"mapped={total}")

# 2) كل سكيل يظهر مرة واحدة فقط (لا تكرار في الـ Registry)
flat = []
for c in doc["capabilities"]:
    flat += c["underlying_skills"]
dup = [k for k, v in Counter(flat).items() if v > 1]
check("no_duplicate_skill_mapping", len(flat) == len(set(flat)) and len(dup) == 0,
      f"total={len(flat)} unique={len(set(flat))} dups={dup[:5]}")

# 3) لا capability = verified بدون test evidence فعلي
bad_verified = [c["capability_id"] for c in doc["capabilities"]
                if c["status"] == "verified" and (not c["tested"] or not c.get("test_evidence"))]
check("verified_requires_evidence", len(bad_verified) == 0, f"bad={bad_verified}")

# 4) status ضمن الـ4 قيم المسموحة فقط
VALID = {"declared", "verified", "unverified", "unavailable"}
bad_status = [c["capability_id"] for c in doc["capabilities"] if c["status"] not in VALID]
check("status_model_valid", len(bad_status) == 0, f"bad={bad_status}")

# 5) "وش تقدر تسوي؟" → قدرات منظمة
ans = capabilities.answer_what_can_you_do()
check("what_can_you_do_organized", ans["capability_count"] == 22, f"count={ans['capability_count']}")

# 6) لا تكشف raw skills في الجواب المنظم
raw_leak = any("underlying_skills" in c for c in ans["capabilities"])
check("no_raw_skills_in_summary", not raw_leak, "")

# 7) get_capability يرجع underlying skills + status
c = capabilities.get_capability("communication")
check("capability_detail_has_skills_and_status",
      c is not None and len(c["underlying_skills"]) > 0 and c["status"] in VALID,
      f"status={c['status']} skills={len(c['underlying_skills'])}")

# 8) overlaps مسجلة
ov = capabilities.overlap_groups()
check("overlaps_recorded", len(ov) == 10, f"groups={len(ov)}")

# 9) أداة jarvis_capabilities
r = capabilities_tools.execute_capabilities_tool("jarvis_capabilities", {})
check("tool_returns_capabilities", r["ok"] and r["capability_count"] == 22, f"ok={r.get('ok')}")

passed = sum(1 for _, c, _ in results if c)
print(f"\n=== {passed}/{len(results)} PASS ===")
sys.exit(0 if passed == len(results) else 1)
