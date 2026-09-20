"""Conservative activation inventory for JARVIS specialist agents.

This module does not activate agents or grant tools. It reports what the current
runtime can prove:
- all 21 profiles are declared;
- explicit task selection is wired through worker -> agent_runner;
- verification is persistent only after a successful execution;
- enforcement is currently request-level, not native Hermes tool enforcement;
- automatic activation/routing remains disabled until stronger enforcement and
  per-agent tool evidence exist.
"""
from __future__ import annotations

from typing import Any

import agent_profiles
import agent_runner
import agent_state


def activation_record(agent_id: str) -> dict[str, Any] | None:
    profile = agent_profiles.get_profile(agent_id)
    if not profile:
        return None

    state = agent_state.get_agent_state(agent_id) or {}
    verified = state.get("execution_status") == "verified" and state.get("last_result") == "ok"

    return {
        "agent_id": agent_id,
        "name_ar": profile.get("name_ar", ""),
        "name_en": profile.get("name_en", ""),
        "group": profile.get("group", ""),
        "role": profile.get("role", ""),
        "activation_status": "verified_explicit" if verified else "declared",
        "profile_declared": True,
        "explicit_task_selection": True,
        "automatic_routing": False,
        "safe_auto_activation": False,
        "execution_path": "task_worker->agent_runner->hermes-agent",
        "enforcement_type": agent_runner.ENFORCEMENT_TYPE,
        "native_hermes_tool_enforcement": False,
        "declared_tool_labels": list(profile.get("allowed_tools", [])),
        "declared_capabilities": list(profile.get("allowed_capabilities", [])),
        "last_tested_at": state.get("last_tested_at"),
        "test_evidence": state.get("test_evidence"),
        "reason_auto_activation_blocked": (
            "native Hermes per-agent tool enforcement is not available; "
            "declared tool labels are not proof of executable tool bindings"
        ),
    }


def activation_inventory() -> list[dict[str, Any]]:
    """Return an honest, non-activating inventory for every declared profile."""
    return [activation_record(agent_id) for agent_id in agent_profiles.agent_ids()]


def activation_summary() -> dict[str, Any]:
    rows = activation_inventory()
    return {
        "declared": len(rows),
        "verified_explicit": sum(1 for r in rows if r["activation_status"] == "verified_explicit"),
        "automatic_routing_enabled": False,
        "native_hermes_tool_enforcement": False,
        "enforcement_type": agent_runner.ENFORCEMENT_TYPE,
        "agents": rows,
    }
