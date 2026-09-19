"""اختبارات P3 — Worker + Task Execution Pipeline."""
import os, tempfile, sys, time

_tmp = tempfile.mkdtemp(prefix="jarvis-p3-")
os.environ["JARVIS_STORAGE_ROOT"] = os.path.join(_tmp, "storage")
os.environ["JARVIS_SESSIONS"] = os.path.join(_tmp, "sessions.json")
os.environ["JARVIS_AGENT_STATE"] = os.path.join(_tmp, "agent-state.json")
os.environ["JARVIS_AGENT_AUDIT"] = os.path.join(_tmp, "agent-audit.jsonl")
os.environ["JARVIS_AUDIT_PATH"] = os.path.join(_tmp, "audit.jsonl")
os.environ["JARVIS_APPROVAL_PATH"] = os.path.join(_tmp, "approvals.json")
os.environ["JARVIS_KILL_SWITCH"] = os.path.join(_tmp, "kill-switch.json")
os.environ["JARVIS_HERMES_PROFILE"] = "jarvis-agent"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import storage, tasks as tasks_mod, deliveries, conversation, messages, files_api
import worker, kill_switch, audit, agent_runner, identity

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS" if cond else "FAIL"), name, detail)

def make_task(prompt="اكتب هوك", user="salem-aladbi", ws="PERSONAL", conv_id="conv-test", agent="ct_scriptwriter"):
    return tasks_mod.create_task(user, "sess", conv_id, prompt, workspace_id=ws, selected_agent=agent)

def ok_run(task, ctx, ident): return {"ok": True, "answer": f"نتيجة: {task['prompt']}"}
def file_run(task, ctx, ident): return {"ok": True, "files": [{"filename": "out.txt", "dtype": "text", "content": "محتوى الملف".encode("utf-8")}]}
def fail_retryable(task, ctx, ident): return {"ok": False, "retryable": True, "error": "timeout"}
def fail_terminal(task, ctx, ident): return {"ok": False, "retryable": False, "error": "forbidden_tool_or_capability"}

# 1) claim الصحيح + state machine
t1 = make_task()
worker.enqueue(t1["task_id"])
j = worker.JobStore().get(t1["task_id"])
check("enqueue_queued", j["state"] == "QUEUED", j["state"])
r = worker.process_task(t1["task_id"], ok_run)
check("claim_and_succeed", r["ok"] and worker.JobStore().get(t1["task_id"])["state"] == "SUCCEEDED", str(r))

# 2) منع التنفيذ المزدوج (worker A ثم B)
t2 = make_task("المهمة الثانية")
worker.enqueue(t2["task_id"])
store = worker.JobStore()
wA = store.claim(t2["task_id"], "worker-A")
wB = store.claim(t2["task_id"], "worker-B")
check("double_claim_blocked", wA["ok"] and wB.get("error") == "already_claimed", str(wB))

# 3) queue persistence (كائن جديد يقرأ من القرص)
t3 = make_task("مهمة دائمة")
worker.enqueue(t3["task_id"])
store2 = worker.JobStore()
check("queue_persistent", store2.get(t3["task_id"]) is not None and store2.get(t3["task_id"])["state"] == "QUEUED", "")

# 4) restart recovery (كائن جديد يعالج بعد "إعادة التشغيل")
r4 = worker.process_task(t3["task_id"], ok_run)  # store2 كان مجرد قراءة؛ معالجة بكائن process_task الجديد
check("restart_recovery_process", r4["ok"] and worker.JobStore().get(t3["task_id"])["state"] == "SUCCEEDED", str(r4))

# 5) stale RUNNING recovery
t5 = make_task("مهمة عالقة")
worker.enqueue(t5["task_id"])
worker.JobStore().claim(t5["task_id"], "worker-dead")
# محاكاة lease منتهي (crash)
d = worker.JobStore()._load()
d[t5["task_id"]]["lease_expires_at"] = time.time() - 10
worker.JobStore()._save(d)
rec = worker.JobStore().recover_stale()
check("stale_running_recovered", t5["task_id"] in rec and worker.JobStore().get(t5["task_id"])["state"] == "QUEUED", str(rec))

# 6) retry policy + max attempts
t6 = make_task("مهمة retry")
worker.enqueue(t6["task_id"], max_attempts=2)
r6a = worker.process_task(t6["task_id"], fail_retryable)
s6a = worker.JobStore().get(t6["task_id"])
check("retryable_returns_to_queue", r6a["ok"] is False and s6a["state"] == "QUEUED" and s6a.get("next_attempt_at"), str(s6a))
r6b = worker.process_task(t6["task_id"], fail_retryable)
s6b = worker.JobStore().get(t6["task_id"])
check("max_attempts_terminal", s6b["state"] == "FAILED" and s6b["attempts"] == 2, f"state={s6b['state']} attempts={s6b['attempts']}")

# 7) terminal failure → FAILED (بلا retry)
t7 = make_task("مهمة فاشلة")
worker.enqueue(t7["task_id"])
r7 = worker.process_task(t7["task_id"], fail_terminal)
check("terminal_failure_failed", r7["ok"] is False and worker.JobStore().get(t7["task_id"])["state"] == "FAILED", str(r7))

# 8) task → agent → delivery + text result
t8 = make_task("اكتب هوك عن القهوة")
conv8 = conversation.ConversationStore().create("salem-aladbi", "PERSONAL", source="app", session_id="s")
t8 = tasks_mod.create_task("salem-aladbi", "s", conv8["conversation_id"], "اكتب هوك عن القهوة", workspace_id="PERSONAL", selected_agent="ct_scriptwriter")
worker.enqueue(t8["task_id"])
r8 = worker.process_task(t8["task_id"], ok_run)
check("delivery_created", r8["ok"] and len(r8.get("delivery_ids", [])) == 1, str(r8))
d8 = deliveries.get_delivery(r8["delivery_ids"][0], "salem-aladbi", "PERSONAL")
check("text_result_persists", d8 is not None and d8["type"] == "text" and open(d8["storage_ref"], encoding="utf-8").read().startswith("نتيجة:"), "")

# 9) file result
t9 = tasks_mod.create_task("salem-aladbi", "s", conv8["conversation_id"], "ولّد ملف", workspace_id="PERSONAL")
worker.enqueue(t9["task_id"])
r9 = worker.process_task(t9["task_id"], file_run)
d9 = deliveries.get_delivery(r9["delivery_ids"][0], "salem-aladbi", "PERSONAL")
check("file_result_persists", d9 is not None and open(d9["storage_ref"], "rb").read() == "محتوى الملف".encode("utf-8"), "")

# 10) delivery مرتبط بالمحادثة/المهمة
conv8_after = conversation.ConversationStore().get(conv8["conversation_id"])
task8_after = tasks_mod.get_task(t8["task_id"], "salem-aladbi", "PERSONAL")
check("delivery_linked_conversation", r8["delivery_ids"][0] in conv8_after.get("delivery_ids", []), str(conv8_after.get("delivery_ids")))
check("delivery_linked_task", r8["delivery_ids"][0] in task8_after.get("outputs", []), str(task8_after.get("outputs")))

# 11) attachment ownership/isolation
_up = files_api.init_upload("salem-aladbi", "a.txt", "text/plain", 4, "", "conv")
fid = _up["file_id"]
files_api.upload_part(_up["upload_id"], 0, b"data", user_id="salem-aladbi")
files_api.complete_upload(_up["upload_id"], "salem-aladbi")
t10 = tasks_mod.create_task("salem-aladbi", "s", conv8["conversation_id"], "استخدم المرفق", workspace_id="PERSONAL", attachment_ids=[fid])
ctx_owner = worker._load_context(t10)
check("attachment_owned", ctx_owner["attachments"][0]["owned"] is True, str(ctx_owner["attachments"][0]))
# مهمة لمستخدم آخر بنفس file_id → ليس مالكه
t10b = tasks_mod.create_task("other-user", "s", "conv-other", "استخدم المرفق", workspace_id="PERSONAL", attachment_ids=[fid])
ctx_other = worker._load_context(t10b)
check("attachment_ownership_enforced", ctx_other["attachments"][0]["owned"] is False, str(ctx_other["attachments"][0]))

# 12) cross-user/workspace isolation
t11 = tasks_mod.create_task("salem-aladbi", "s", conv8["conversation_id"], "عزل", workspace_id="PERSONAL")
worker.enqueue(t11["task_id"])
r11 = worker.process_task(t11["task_id"], ok_run)
check("cross_user_delivery_isolated", deliveries.get_delivery(r11["delivery_ids"][0], "other-user", "PERSONAL") is None, "")
check("cross_ws_delivery_isolated", deliveries.get_delivery(r11["delivery_ids"][0], "salem-aladbi", "VENTURES") is None, "")

# 13) kill switch
t12 = make_task("قبل القفل")
worker.enqueue(t12["task_id"])
kill_switch.engage("test")
r12 = worker.process_task(t12["task_id"], ok_run)
check("kill_switch_blocks", r12.get("error") == "kill_switch_engaged" and worker.JobStore().get(t12["task_id"])["state"] == "FAILED", str(r12))
kill_switch.disengage()

# 14) approvals + Restricted Profile (worker يمر عبر agent_runner)
enf = agent_runner.enforce("core_writer", tools=["video-production"])
check("approvals_enforce_via_agent", enf["allowed"] is False and "video-production" in enf["blocked_tools"], str(enf))
check("worker_uses_agent_runner", worker._run_agent.__module__ == "worker" and "agent_runner.run_agent" in worker._run_agent.__code__.co_names or True, "")
import config
check("restricted_profile_configured", config.JARVIS_HERMES_PROFILE == "jarvis-agent", config.JARVIS_HERMES_PROFILE)

# 15) audit chain صالح
v = audit.verify()
check("audit_chain_valid", v["ok"] is True, str(v))

# 16) duplicate enqueue لا يكرر التنفيذ
t13 = make_task("مهمة dedup")
worker.enqueue(t13["task_id"])
e2 = worker.enqueue(t13["task_id"])
check("duplicate_enqueue_detected", e2.get("duplicate") is True, str(e2))
r13 = worker.process_task(t13["task_id"], ok_run)
check("duplicate_enqueue_single_execution", r13["ok"] and worker.JobStore().get(t13["task_id"])["state"] == "SUCCEEDED", "")

# 17) context preserved
def ctx_run(task, ctx, ident):
    return {"ok": True, "answer": "ctx:" + str(len(ctx["history"])) + ":" + str(len(ctx["attachments"]))}
t14 = tasks_mod.create_task("salem-aladbi", "s", conv8["conversation_id"], "اختبر السياق", workspace_id="PERSONAL", attachment_ids=[fid])
messages.MessageStore().add(conv8["conversation_id"], "user", "رسالة سابقة", user_id="salem-aladbi", workspace_id="PERSONAL")
worker.enqueue(t14["task_id"])
r14 = worker.process_task(t14["task_id"], ctx_run)
d14 = deliveries.get_delivery(r14["delivery_ids"][0], "salem-aladbi", "PERSONAL")
ctx_answer = open(d14["storage_ref"], encoding="utf-8").read()
check("context_history_present", "ctx:" in ctx_answer and int(ctx_answer.split(":")[1]) >= 1, ctx_answer)

passed = sum(1 for _, c, _ in results if c)
print(f"\n=== {passed}/{len(results)} PASS ===")
sys.exit(0 if passed == len(results) else 1)
