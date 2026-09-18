"""اختبارات PHASE C: Agent Execution Model."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_profiles, agent_runner

REQUIRED = ["agent_id","name_ar","name_en","group","role","system_prompt",
            "allowed_tools","allowed_capabilities","memory_scope","task_state",
            "execution_status","audit_trail"]
results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS" if cond else "FAIL"), name, detail)

profiles = agent_profiles.list_profiles()

# 1) 21 profile
check("agents_defined_21", len(profiles) == 21, f"n={len(profiles)}")

# 2) كل profile فيه كل الحقول المطلوبة
missing = [(p.get("agent_id"), [f for f in REQUIRED if f not in p]) for p in profiles if any(f not in p for f in REQUIRED)]
check("all_fields_present", len(missing) == 0, f"missing={missing}")

# 3) كل agent_id فريد
ids = [p["agent_id"] for p in profiles]
check("unique_agent_ids", len(ids) == len(set(ids)), "")

# 4) لا agent = verified بدون execution (الكل يبدأ declared)
bad = [p["agent_id"] for p in profiles if p["execution_status"] == "verified"]
check("no_false_verified", len(bad) == 0, f"verified_before_test={bad}")

# 5) تشغيل وكيل واحد end-to-end (ct_scriptwriter) عبر Hermes
IDENT = {"user_id":"salem-aladbi","session_id":"sess-agent-test",
         "conversation_id":"salem-aladbi-conv-agenttest","memory_namespace":"jarvis:salem-aladbi:scriptwriter"}
r = agent_runner.run_agent("ct_scriptwriter", "اكتب هوك 30 ثانية لفيديو عن القهوة القطرية للريلز.", IDENT)
check("agent_end_to_end_execution", r["ok"] is True, f"ok={r.get('ok')} err={r.get('error')}")

# 6) audit trail فيه started + finished
evs = [e["event"] for e in r.get("audit_trail", [])]
check("audit_trail_started_finished", "started" in evs and "finished" in evs, f"events={evs}")

# 7) execution_status يصبح verified بعد التنفيذ الناجح
check("execution_status_verified_after_run", r.get("execution_status") == "verified",
      f"status={r.get('execution_status')}")

# 8) الإجابة غير فارغة
check("answer_non_empty", bool(r.get("answer", "").strip()), f"len={len(r.get('answer',''))}")

passed = sum(1 for _, c, _ in results if c)
print(f"\n=== {passed}/{len(results)} PASS ===")
# عرض مقتطف من الإجابة كدليل
if r.get("ok"):
    print("--- AGENT OUTPUT (first 300 chars) ---")
    print(r["answer"][:300])
sys.exit(0 if passed == len(results) else 1)
