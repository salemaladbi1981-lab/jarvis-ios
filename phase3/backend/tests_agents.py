"""اختبارات PHASE C: Agent Execution Model + enforcement + persistence."""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_profiles, agent_runner, agent_state, agent_audit

REQUIRED = ["agent_id","name_ar","name_en","group","role","system_prompt",
            "allowed_tools","allowed_capabilities","memory_scope","task_state",
            "execution_status","audit_trail"]
results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS" if cond else "FAIL"), name, detail)

profiles = agent_profiles.list_profiles()

# --- unit: profiles ---
check("agents_defined_21", len(profiles) == 21, f"n={len(profiles)}")
missing = [(p.get("agent_id"), [f for f in REQUIRED if f not in p]) for p in profiles if any(f not in p for f in REQUIRED)]
check("all_fields_present", len(missing) == 0, f"missing={missing}")
ids = [p["agent_id"] for p in profiles]
check("unique_agent_ids", len(ids) == len(set(ids)), "")

# --- enforcement: forbidden tool/capability ---
enf_t = agent_runner.enforce("core_writer", tools=["video-production"])
check("forbidden_tool_blocked", enf_t["allowed"] is False and "video-production" in enf_t["blocked_tools"],
      f"blocked={enf_t['blocked_tools']}")
enf_c = agent_runner.enforce("ct_scriptwriter", capabilities=["business"])
check("forbidden_capability_blocked", enf_c["allowed"] is False and "business" in enf_c["blocked_capabilities"],
      f"blocked={enf_c['blocked_capabilities']}")
enf_ok = agent_runner.enforce("core_writer", tools=["copywriting"], capabilities=["content"])
check("allowed_tool_passes", enf_ok["allowed"] is True, "")

# run_agent مع tool ممنوع → يُمنع قبل Hermes
r_blocked = agent_runner.run_agent("core_writer", "اكتب إعلان", {"user_id":"salem-aladbi"}, requested_tools=["video-production"])
check("run_agent_blocks_forbidden_tool", r_blocked["ok"] is False and r_blocked.get("error") == "forbidden_tool_or_capability",
      f"err={r_blocked.get('error')}")

# --- live execution (ct_scriptwriter) ---
IDENT = {"user_id":"salem-aladbi","session_id":"sess-agent-test",
         "conversation_id":"salem-aladbi-conv-agenttest","memory_namespace":"jarvis:salem-aladbi:scriptwriter"}
r = agent_runner.run_agent("ct_scriptwriter", "اكتب هوك 30 ثانية لفيديو عن القهوة القطرية للريلز.", IDENT)
check("agent_end_to_end_execution", r["ok"] is True, f"ok={r.get('ok')} err={r.get('error')}")
evs = [e["event"] for e in r.get("audit_trail", [])]
check("audit_trail_started_finished", "started" in evs and "finished" in evs, f"events={evs}")
check("answer_non_empty", bool(r.get("answer", "").strip()), f"len={len(r.get('answer',''))}")

# --- persistent status readback (بعد إعادة التشغيل = عملية جديدة) ---
st = agent_state.get_agent_state("ct_scriptwriter")
check("persistent_status_readback", st is not None and st.get("execution_status") == "verified"
      and st.get("last_tested_at") and st.get("test_evidence"),
      f"status={st.get('execution_status') if st else None}")

# عملية منفصلة (محاكاة restart)
sub = subprocess.run(
    [sys.executable, "-c",
     "import sys,os; sys.path.insert(0, os.path.abspath('.')); import agent_state; "
     "s=agent_state.get_agent_state('ct_scriptwriter'); "
     "print(s.get('execution_status') if s else 'MISSING')"],
    capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
check("persistent_status_after_restart", "verified" in sub.stdout, f"subprocess={sub.stdout.strip()}")

# --- audit persistence readback ---
audit = agent_audit.read("ct_scriptwriter", limit=10)
last_ok = [a for a in audit if a.get("result_status") == "ok"]
check("audit_persistence_readback", len(last_ok) > 0
      and all(k in last_ok[-1] for k in ("task_id","agent_id","started","capability","tools_used","finished","duration_s","result_status")),
      f"records={len(last_ok)} fields_ok={'task_id' in last_ok[-1] if last_ok else False}")

passed = sum(1 for _, c, _ in results if c)
print(f"\n=== {passed}/{len(results)} PASS ===")
if r.get("ok"):
    print("--- AGENT OUTPUT (first 200 chars) ---")
    print(r["answer"][:200])
sys.exit(0 if passed == len(results) else 1)
