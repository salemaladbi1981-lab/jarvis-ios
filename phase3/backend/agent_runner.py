"""Agent execution engine — Hermes + Orchestrator + 21 specialist profiles.

- enforce(): يمنع أي tool/capability خارج allowlist (runtime/orchestrator).
- run_agent(): تنفيذ + حالة persistent + audit trail persistent.
"""
from __future__ import annotations
import json, time, uuid, hashlib, urllib.request
import config, identity, agent_profiles, agent_state, agent_audit, tool_guard

# التقييد الحالي: request-level enforcement (يمنع tool/capability عند الطلب قبل Hermes).
# ليس hermes-tool enforcement (Hermes يحتفظ بأدواته الداخلية الكاملة عند التنفيذ).
ENFORCEMENT_TYPE = "request-level"


def enforce(agent_id: str, tools=None, capabilities=None) -> dict:
    """Enforcement عند حدود التنفيذ: أي tool/capability غير مسموح يُمنع،
    والأفعال غير القابلة للعكس (sensitive) تتطلب موافقة ملزمة (tool_guard)."""
    prof = agent_profiles.get_profile(agent_id)
    if not prof:
        return {"allowed": False, "blocked_tools": [], "blocked_capabilities": [], "error": "unknown_agent"}
    tools = tools or []
    capabilities = capabilities or []
    blocked_tools = [t for t in tools if t not in prof["allowed_tools"]]
    blocked_caps = [c for c in capabilities if c not in prof["allowed_capabilities"]]
    # أفعال غير قابلة للعكس → معطّلة تقنيًا بلا موافقة ملزمة (هذا المسار لا يحمل approval)
    sensitive = [t for t in tools if tool_guard.is_sensitive(t)]
    return {
        "allowed": not (blocked_tools or blocked_caps or sensitive),
        "blocked_tools": blocked_tools,
        "blocked_capabilities": blocked_caps,
        "sensitive_blocked": sensitive,
    }


def run_agent(agent_id: str, task: str, ident_dict: dict,
              requested_tools=None, requested_capabilities=None) -> dict:
    prof = agent_profiles.get_profile(agent_id)
    if not prof:
        return {"ok": False, "error": "unknown_agent"}
    if not (task or "").strip():
        return {"ok": False, "error": "task_required"}

    task_id = uuid.uuid4().hex[:12]
    ident = identity.from_args(ident_dict)
    t0 = time.time()

    # 1) enforcement gate
    enf = enforce(agent_id, requested_tools, requested_capabilities)
    if not enf["allowed"]:
        agent_audit.append({
            "task_id": task_id, "agent_id": agent_id, "started": t0,
            "capability": None, "tools_used": requested_tools or [],
            "blocked_tools": enf["blocked_tools"], "blocked_capabilities": enf["blocked_capabilities"],
            "finished": time.time(), "duration_s": 0.0, "result_status": "blocked",
        })
        return {
            "ok": False, "error": "forbidden_tool_or_capability",
            "blocked_tools": enf["blocked_tools"], "blocked_capabilities": enf["blocked_capabilities"],
        }

    key = config.API_SERVER_KEY
    if not key:
        return {"ok": False, "error": "hermes_key_missing"}

    active_capability = prof["allowed_capabilities"][0] if prof["allowed_capabilities"] else None
    sys_prompt = (
        prof["system_prompt"]
        + f"\n\n[Identity] user_id={ident.user_id}, memory_namespace={ident.memory_namespace}"
        + f"\n[Allowed capabilities] {', '.join(prof['allowed_capabilities'])}"
        + f"\n[Allowed tools] {', '.join(prof['allowed_tools'])}"
        + "\n[Enforcement] Use ONLY the capabilities/tools above; anything else is blocked."
    )
    body = json.dumps({"model": "hermes-agent", "messages": [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": task},
    ]}).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + key, **ident.to_headers()}
    api_url = config.JARVIS_HERMES_API_URL
    prof = getattr(config, "JARVIS_HERMES_PROFILE", "") or ""
    if prof:
        # Restricted Hermes profile: /v1/chat/completions → /p/<profile>/v1/chat/completions
        api_url = api_url.replace("/v1/chat/completions", f"/p/{prof}/v1/chat/completions")
    req = urllib.request.Request(api_url, data=body, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        answer = data["choices"][0]["message"]["content"]
        dur = round(time.time() - t0, 1)
        # persistent status (task_hash فقط، بلا نص المستخدم)
        agent_state.mark_verified(agent_id,
                                  task_hash=hashlib.sha256(task.encode("utf-8")).hexdigest()[:16],
                                  test_type="execution",
                                  result_status="ok", result_len=len(answer))
        # persistent audit
        agent_audit.append({
            "task_id": task_id, "agent_id": agent_id, "started": t0,
            "task_hash": hashlib.sha256(task.encode("utf-8")).hexdigest()[:16],
            "capability": active_capability, "tools_used": requested_tools or prof["allowed_tools"],
            "finished": time.time(), "duration_s": dur, "result_status": "ok", "result_len": len(answer),
            "enforcement_type": ENFORCEMENT_TYPE,
        })
        return {
            "ok": True, "agent_id": agent_id, "name_ar": prof["name_ar"], "answer": answer,
            "task_id": task_id, "execution_status": "verified", "enforcement_type": ENFORCEMENT_TYPE,
            "audit_trail": [
                {"event": "started", "ts": t0, "agent_id": agent_id,
                 "active_capability": active_capability, "allowed_tools": prof["allowed_tools"]},
                {"event": "finished", "ts": time.time(), "duration_s": dur, "result_len": len(answer)},
            ],
        }
    except Exception as e:
        agent_audit.append({
            "task_id": task_id, "agent_id": agent_id, "started": t0,
            "capability": active_capability, "tools_used": requested_tools or [],
            "finished": time.time(), "duration_s": round(time.time() - t0, 1),
            "result_status": "failed", "error": str(e)[:200],
        })
        return {"ok": False, "error": str(e)[:200], "agent_id": agent_id, "execution_status": "unverified"}
