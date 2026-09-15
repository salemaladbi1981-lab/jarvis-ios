#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Approval policy evaluator parity (mirrors ApprovalPolicyEvaluatorTests.swift).
Run: python3 approval_policy_test.py
"""
import json, sys

r = json.load(open("JARVIS/Resources/AGENT-REGISTRY.json", encoding="utf-8"))
agents = {a["id"]: a for a in r["agents"]}

def requires_approval(agent_id, action):
    a = agents.get(agent_id)
    if a is None:
        return True  # fail-safe
    return action in a["approval_policy"]["required_actions"]

cases = [
    ("core_home", "unlock-door", True),
    ("core_home", "read-temperature", False),
    ("core_guardian", "disable-camera", True),
    ("core_dealmaker", "financial-commitment", True),
    ("sys_server", "destructive-config", True),
    ("unknown", "anything", True),
]

failed = 0
for agent_id, action, expected in cases:
    got = requires_approval(agent_id, action)
    ok = got == expected
    print(f"  {'PASS' if ok else 'FAIL'}  {agent_id} + {action} → approval={got} (expected {expected})")
    if not ok:
        failed += 1

print(f"\nRESULT: {'PASS' if failed == 0 else f'{failed} FAILURES'}")
sys.exit(1 if failed else 0)
