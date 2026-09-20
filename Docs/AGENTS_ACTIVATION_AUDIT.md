# JARVIS — Agents Activation Audit

Date: 2026-09-20
Branch: `chatgpt-write-test`

## Executive result

The repository contains 21 declared specialist profiles, but **declared is not the same as active or tool-verified**.

Current safe conclusion:

- 21/21 specialist profiles are structurally declared in `phase3/backend/agent_profiles.py` and the shared registry.
- Background task execution has an explicit specialist path: `selected_agent` -> `worker._run_agent()` -> `agent_runner.run_agent()` -> Hermes.
- Without `selected_agent`, background tasks intentionally fall back to `core_coordinator`.
- Inline text chat currently delegates through `brain_tools.jarvis_brain`; it does not prove that a named specialist profile was selected.
- `agent_tools.py` declares a `jarvis_agent` tool, but repository evidence does not prove that this tool is part of the active inline-chat provider toolset.
- The iOS `AgentRouter` provides deterministic local labels/routes for a small subset, but that is not backend execution verification.
- Enforcement around `agent_runner` is **request-level**. It validates requested tool/capability labels before the Hermes call, but it is not native per-agent Hermes tool enforcement.
- Therefore broad automatic activation of all 21 agents is **not approved by this audit**.

## Activation truth table

| Layer | Current state | What it proves | What it does not prove |
| --- | --- | --- | --- |
| Shared/Backend Registry | 21 profiles declared | IDs, roles, declared capabilities/tool labels exist | Real executable tools or successful runs |
| iOS AgentRegistry | Registry can be loaded and displayed | UI metadata is present | Server-side execution |
| iOS AgentRouter | Deterministic routing for a limited subset | Local routing decision can be made | Backend agent was actually run |
| `agent_runtime.py` | Can score/route across registry data | A candidate agent can be selected | Production path uses that decision |
| Task worker | Explicit `selected_agent` is honored | Named specialist can be passed to runner | Agent is verified or safe to auto-select |
| `agent_runner.py` | Profile prompt + declared allowlists + audit/state | Request boundary checks and persistent run evidence | Native Hermes tool restriction |
| Inline chat | `jarvis_brain` Hermes path | Real brain delegation exists | Named specialist activation |
| Persistent state | `agent_state.mark_verified()` after success | A specific agent completed a recorded execution | All tools/capabilities of that agent are verified |

## Concrete risk found

The strongest blocker to broad activation is enforcement scope. `agent_runner.ENFORCEMENT_TYPE` is explicitly `request-level`. The runner can reject a requested tool/capability that is outside a profile allowlist, but the Hermes runtime itself is not proven to receive a per-agent native tool allowlist. Treating all declared tool labels as real executable bindings would therefore overstate capability and weaken the existing governance model.

## Low-risk activation plumbing implemented

`phase3/backend/agent_activation.py` now exposes a conservative inventory model that:

- distinguishes `declared` from `verified_explicit`;
- reports explicit task-selection wiring without calling it verification;
- keeps automatic routing and safe auto-activation disabled;
- reports enforcement truthfully as `request-level`;
- marks native Hermes tool enforcement as unavailable;
- exposes the last persistent execution evidence only when it exists;
- labels profile tools as **declared tool labels**, not executable proof.

Portable regression coverage in `Tools/agent_activation_audit_test.py` prevents future changes from silently claiming automatic/live activation without evidence.

## Activation policy after this audit

1. Keep broad automatic specialist routing OFF.
2. Explicit specialist selection may continue through the existing task-worker path.
3. A specialist may be promoted from `declared` to `verified_explicit` only after a successful persisted execution record.
4. A tool should not be described as agent-verified merely because its name appears in a profile allowlist.
5. Future automatic routing requires either native Hermes per-agent tool enforcement or an equally strong execution boundary with concrete tool bindings and regression evidence.
6. Sensitive/external actions remain behind the existing approval/tool-guard policy regardless of agent identity.

## Next safe activation candidates

The next candidates should be agents whose work can be completed without consequential external actions (for example writing/review/creative planning) **after** their real execution path is tested. Device control, outbound messaging, finance, home actions, infrastructure mutation, or other consequential agents should remain non-automatic until their concrete tools, approval path, and enforcement are proven individually.

## Status

Phase 2 audit: **COMPLETE**.

Broad agent activation: **BLOCKED BY DESIGN** pending stronger tool enforcement/evidence.

Low-risk activation observability/scaffolding: **IMPLEMENTED**.
