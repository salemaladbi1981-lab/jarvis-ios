"""اختبارات PHASE B: Capability Registry."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capabilities, capabilities_tools

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS" if cond else "FAIL"), name, detail)

# 1) 375 skills مغطاة بالكامل
doc = capabilities.load()
total = sum(c["skill_count"] for c in doc["capabilities"])
check("all_375_skills_mapped", total == 375, f"mapped={total}")

# 2) "وش تقدر تسوي؟" → قدرات منظمة (22) لا 375
ans = capabilities.answer_what_can_you_do()
check("what_can_you_do_organized", ans["capability_count"] == 22 and len(ans["capabilities"]) == 22,
      f"count={ans['capability_count']}")

# 3) لا تكشف raw skills في الجواب المنظم
raw_leak = any("underlying_skills" in c or "skill_count" not in c for c in ans["capabilities"])
check("no_raw_skills_in_summary", not raw_leak, "")

# 4) get_capability يرجع underlying skills عند الطلب
c = capabilities.get_capability("communication")
check("capability_detail_has_skills", c is not None and len(c["underlying_skills"]) > 0,
      f"communication skills={len(c['underlying_skills'])}")

# 5) overlaps مسجلة
ov = capabilities.overlap_groups()
check("overlaps_recorded", len(ov) == 10, f"groups={len(ov)}")

# 6) الأداة jarvis_capabilities
r = capabilities_tools.execute_capabilities_tool("jarvis_capabilities", {})
check("tool_returns_capabilities", r["ok"] and r["capability_count"] == 22, f"ok={r.get('ok')}")

# 7) أداة بتفصيل capability واحد
r2 = capabilities_tools.execute_capabilities_tool("jarvis_capabilities", {"capability_id": "video"})
check("tool_capability_detail", r2["ok"] and r2["capability"]["capability_id"] == "video",
      f"skills={len(r2['capability']['underlying_skills'])}")

passed = sum(1 for _, c, _ in results if c)
print(f"\n=== {passed}/{len(results)} PASS ===")
sys.exit(0 if passed == len(results) else 1)
