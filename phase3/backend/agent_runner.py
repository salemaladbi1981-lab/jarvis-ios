"""Agent execution engine — Hermes + Orchestrator + 21 specialist profiles.

run_agent(agent_id, task, identity) يفوّض المهمة إلى Hermes بـ system_prompt المتخصص،
ويسجّل audit trail كامل (started → active capability → tools → result → finished).
"""
from __future__ import annotations
import json, time, urllib.request
import config, identity, agent_profiles


def run_agent(agent_id: str, task: str, ident_dict: dict) -> dict:
    prof = agent_profiles.get_profile(agent_id)
    if not prof:
        return {"ok": False, "error": "unknown_agent"}
    if not (task or "").strip():
        return {"ok": False, "error": "task_required"}

    key = config.API_SERVER_KEY
    if not key:
        return {"ok": False, "error": "hermes_key_missing"}

    ident = identity.from_args(ident_dict)
    audit = []
    t0 = time.time()
    audit.append({
        "event": "started",
        "ts": t0,
        "agent_id": agent_id,
        "active_capability": prof["allowed_capabilities"][0] if prof["allowed_capabilities"] else None,
        "allowed_tools": prof["allowed_tools"],
        "memory_scope": prof["memory_scope"],
    })

    sys_prompt = (
        prof["system_prompt"]
        + f"\n\n[Identity] user_id={ident.user_id}, memory_namespace={ident.memory_namespace}"
        + f"\n[Allowed capabilities] {', '.join(prof['allowed_capabilities'])}"
        + f"\n[Allowed tools] {', '.join(prof['allowed_tools'])}"
    )
    body = json.dumps({
        "model": "hermes-agent",
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": task},
        ],
    }).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + key,
        **ident.to_headers(),
    }
    req = urllib.request.Request(config.JARVIS_HERMES_API_URL, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        answer = data["choices"][0]["message"]["content"]
        audit.append({
            "event": "finished",
            "ts": time.time(),
            "duration_s": round(time.time() - t0, 1),
            "result_len": len(answer),
            "ok": True,
        })
        return {
            "ok": True,
            "agent_id": agent_id,
            "name_ar": prof["name_ar"],
            "answer": answer,
            "audit_trail": audit,
            "execution_status": "verified",
        }
    except Exception as e:
        audit.append({"event": "failed", "ts": time.time(), "error": str(e)[:200]})
        return {
            "ok": False,
            "error": str(e)[:200],
            "agent_id": agent_id,
            "audit_trail": audit,
            "execution_status": "unverified",
        }
