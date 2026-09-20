#!/usr/bin/env python3
"""Portable regression tests for conservative Agent Activation inventory.

No Hermes key/network required. These checks intentionally prevent the audit
surface from claiming automatic/live activation without execution evidence.
"""
from __future__ import annotations

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "phase3", "backend")
sys.path.insert(0, BACKEND)

import agent_activation
import agent_profiles
import agent_runner
import agent_state


def check(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    print(f"PASS {name} {detail}".rstrip())


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        agent_state.STATE_PATH = os.path.join(td, "agent-state.json")

        rows = agent_activation.activation_inventory()
        ids = [r["agent_id"] for r in rows]
        check("inventory_has_21_profiles", len(rows) == 21, f"count={len(rows)}")
        check("inventory_ids_unique", len(ids) == len(set(ids)))
        check("inventory_matches_profiles", set(ids) == set(agent_profiles.agent_ids()))
        check("unknown_agent_not_invented", agent_activation.activation_record("not_real") is None)

        check(
            "unverified_agents_are_declared_only",
            all(r["activation_status"] == "declared" for r in rows),
        )
        check(
            "automatic_routing_stays_disabled",
            all(r["automatic_routing"] is False and r["safe_auto_activation"] is False for r in rows),
        )
        check(
            "native_tool_enforcement_not_overclaimed",
            all(r["native_hermes_tool_enforcement"] is False for r in rows),
        )
        check(
            "request_level_enforcement_reported_honestly",
            agent_runner.ENFORCEMENT_TYPE == "request-level"
            and all(r["enforcement_type"] == "request-level" for r in rows),
        )
        check(
            "explicit_selection_is_plumbing_not_verification",
            all(r["explicit_task_selection"] is True for r in rows)
            and all(r["activation_status"] != "verified_explicit" for r in rows),
        )

        agent_state.mark_verified(
            "core_writer",
            task_hash="0123456789abcdef",
            test_type="portable-fixture",
            result_status="ok",
            result_len=12,
        )
        writer = agent_activation.activation_record("core_writer")
        check("verified_state_promotes_only_that_agent", writer["activation_status"] == "verified_explicit")
        check("verified_state_keeps_auto_activation_off", writer["safe_auto_activation"] is False)
        check("verification_evidence_exposed", writer["test_evidence"]["task_hash"] == "0123456789abcdef")

        summary = agent_activation.activation_summary()
        check("summary_count_stable", summary["declared"] == 21)
        check("summary_verified_count", summary["verified_explicit"] == 1)
        check("summary_auto_routing_disabled", summary["automatic_routing_enabled"] is False)

    print("\n=== AGENT ACTIVATION AUDIT: PASS ===")


if __name__ == "__main__":
    main()
