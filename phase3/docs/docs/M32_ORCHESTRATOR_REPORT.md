# JARVIS — M3.2 Orchestrator Report

## Status: PASS (logic + automated tests)

Central Orchestrator routes every request through one JARVIS personality:
User → Orchestrator → intent/context → agent → tool → approval → result → response.

## Routing model
- Deterministic keyword routing to agent groups (core_home, ct_account,
  ct_director, sys_server), else `general` (direct answer, no tool).
- No manual agent selection; no 21-agent competition.

## Result types (structured)
- direct_answer (no tool)
- safe_read → tool (no approval)
- sensitive_action → approval required (blocked before execution)
- content_request → content agent (no home/system tool)
- capability_unavailable (no fake success)

## Tests: 23 PASS / 0 FAIL (see M32_ROUTING_TEST_REPORT.md)
