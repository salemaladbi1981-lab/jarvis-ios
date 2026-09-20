# JARVIS Agents Activation Audit

Evidence baseline: `JARVIS/Resources/AGENT-REGISTRY.json`, `JARVIS/Agents/AgentRouter.swift`, and `phase3/backend/orchestrator.py`.

Status legend:
- **YES** = directly proven by current code path.
- **PARTIAL** = present/routable but no proven end-to-end executable tool path.
- **NO** = not currently wired for that capability.
- **UNKNOWN** = registry declares a capability, but current inspected runtime does not prove execution.

| Agent | Exists | UI/orbit-capable | Local routable | Backend routed | Proven real tools | Executable now | Mock-only | Needs activation |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| المنسق (`core_coordinator`) | YES | YES | YES (fallback) | NO direct route | NO | PARTIAL | NO | YES |
| المراقب (`core_watcher`) | YES | YES | NO | NO | NO | NO | YES/registry-only | YES |
| المنتج (`core_producer`) | YES | YES | NO | NO | NO | NO | YES/registry-only | YES |
| الصفقات (`core_dealmaker`) | YES | YES | NO | NO | NO | NO | YES/registry-only | YES |
| الحارس (`core_guardian`) | YES | YES | NO | NO | NO | NO | YES/registry-only | YES |
| الكاتب (`core_writer`) | YES | YES | YES | NO | NO | PARTIAL | NO | YES |
| المراجع (`core_reviewer`) | YES | YES | NO | NO | NO | NO | YES/registry-only | YES |
| البيت (`core_home`) | YES | YES | YES | YES | temperature/light/unlock via tool gateway | YES | NO | NO |
| البناء (`sys_builder`) | YES | YES | NO | NO | NO | NO | YES/registry-only | YES |
| المدرب (`sys_coach`) | YES | YES | NO | NO | NO | NO | YES/registry-only | YES |
| الربع (`sys_circle`) | YES | YES | NO | NO | NO | NO | YES/registry-only | YES |
| الخادم (`sys_server`) | YES | YES | YES | YES | service health via tool gateway | YES | NO | NO |
| معمار (`sys_architect`) | YES | YES | NO | NO | NO | NO | YES/registry-only | YES |
| مدير العميل (`ct_account`) | YES | YES | NO local | YES | calendar/reminders in orchestrator | YES | NO | NO/optional local parity |
| المدير الإبداعي (`ct_creative`) | YES | YES | NO | NO | NO | NO | YES/registry-only | YES |
| المخرج (`ct_director`) | YES | YES | NO local | YES | NO concrete tool (`content_request -> None`) | PARTIAL | NO | YES |
| كاتب السيناريو (`ct_scriptwriter`) | YES | YES | YES | NO | NO | PARTIAL | NO | YES |
| مهندس البرومبت (`ct_prompteng`) | YES | YES | YES | NO | NO | PARTIAL | NO | YES |
| مصمم الحركة (`ct_motion`) | YES | YES | NO | NO | NO | NO | YES/registry-only | YES |
| مراقب الجودة (`ct_qc`) | YES | YES | NO | NO | NO | NO | YES/registry-only | YES |
| مراجع التسويق (`ct_mkt`) | YES | YES | NO | NO | NO | NO | YES/registry-only | YES |

## Findings

1. The registry contains **21 agents** across core/system/content.
2. The on-device deterministic router can return only **6 IDs**: `core_coordinator`, `core_writer`, `core_home`, `sys_server`, `ct_scriptwriter`, `ct_prompteng`.
3. The inspected backend orchestrator directly routes only **4 specialist IDs**: `core_home`, `ct_account`, `ct_director`, `sys_server`.
4. Only `core_home`, `sys_server`, and `ct_account` have clearly proven concrete tool execution in the inspected orchestrator path. `ct_director` is routed, but its content request deliberately resolves to no concrete tool.
5. Registry metadata (tool names/capabilities) must not be treated as proof of implementation.

## Safe next activation order

1. **Routing parity**: align local/backend routing tables so the same intent does not select different agents.
2. **Coordinator handoff contract**: make `core_coordinator` explicitly orchestrate specialist handoff rather than being only a local fallback.
3. **Content specialists**: wire `ct_scriptwriter` and `ct_prompteng` to a real backend execution contract before calling them executable.
4. **Builder/architect**: activate only behind repository/tool permissions and approval gates.
5. **Watcher/circle/dealmaker/guardian**: require explicit data sources, action contracts, and approval policies before execution.

No agent in this document should be presented to the user as fully executable unless its runtime path is proven end-to-end.
