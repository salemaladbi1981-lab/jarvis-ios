# AGENTS_ACTIVATION_AUDIT

Audit date: 2026-09-20. Scope: all 21 IDs in the app/backend registry and execution profiles. This is code evidence, not a claim that remote providers or credentials were tested live tonight.

- **EXISTS:** same ID in app registry, backend registry, and execution profile.
- **UI_VISIBLE:** “Active orbit” means visible only when actual runtime events arrive; no always-on catalog or fabricated activity.
- **ROUTABLE:** explicit `jarvis_agent(agent_id)` is supported for all IDs. Local keyword routing remains an observation-only six-agent subset.
- **BACKEND_SUPPORTED:** execution profile plus real `agent_runner.run_agent` HTTP delegation exists.
- **HAS_REAL_TOOLS:** local provider handlers actually exist; abstract profile labels such as `scenes` or `video-production` do not count as tools.
- **EXECUTABLE:** “Conditional” requires a reachable configured Hermes backend and provider authorization. No live credential-dependent execution was attempted.
- **MOCK_ONLY:** no production agent is intentionally powered by fake success after the integrity fixes. Unavailable is not mock execution.
- **NEEDS_ACTIVATION:** “Provider” requires real domain integration; “Verify” requires deployment/provider verification rather than invented plumbing.

| Agent | EXISTS | UI_VISIBLE | ROUTABLE | BACKEND_SUPPORTED | HAS_REAL_TOOLS | EXECUTABLE | MOCK_ONLY | NEEDS_ACTIVATION | Evidence / limitation |
|---|---|---|---|---|---|---|---|---|---|
| `core_coordinator` (Coordinator) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Yes, limited | Conditional | No | Verify | Email reads, maps, memory, brain delegation |
| `core_watcher` (Watcher) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Unverified remote only | Conditional | No | Provider | No persistent monitoring scheduler or alert provider wired. |
| `core_producer` (Producer) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Yes, limited | Conditional | No | Verify | YouTube search/details/transcript/playback handoff; not video production |
| `core_dealmaker` (Dealmaker) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Unverified remote only | Conditional | No | Provider | Advisory prompt only; no investment or transaction tools. |
| `core_guardian` (Guardian) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Unverified remote only | Conditional | No | Provider | No connected security or reputation provider. |
| `core_writer` (Writer) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Yes, limited | Conditional | No | Verify | Email draft/send; explicit confirmation gate |
| `core_reviewer` (Reviewer) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Unverified remote only | Conditional | No | Provider | Text review prompt; real media inspection tools unverified. |
| `core_home` (Home) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Unverified remote only | Conditional | No | Provider | Smart-home/scenes unavailable; fabricated handlers removed. |
| `sys_builder` (Builder) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Unverified remote only | Conditional | No | Provider | Hermes delegation exists; build/file tools inside remote Hermes unverified. |
| `sys_coach` (Coach) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Unverified remote only | Conditional | No | Provider | Advisory prompt; no live health/fitness provider. |
| `sys_circle` (Circle) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Yes, limited | Conditional | No | Verify | Telegram search/read/draft/send; confirmation gate |
| `sys_server` (Server) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Unverified remote only | Conditional | No | Provider | Advisory prompt; no generic infrastructure mutation or health handler verified. |
| `sys_architect` (Architect) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Unverified remote only | Conditional | No | Verify | Architecture prompt; no verified topology/control provider. |
| `ct_account` (Account Manager) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Unverified remote only | Conditional | No | Verify | Brief/clarification prompt; EventKit is a separate client capability. |
| `ct_creative` (Creative Director) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Unverified remote only | Conditional | No | Verify | Concept prompt; image-generation execution unverified. |
| `ct_director` (Director) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Unverified remote only | Conditional | No | Provider | Shot-list/framing prompt; no video-production execution verified. |
| `ct_scriptwriter` (Scriptwriter) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Unverified remote only | Conditional | No | Verify | Script/dialogue/hook prompt via existing Hermes agent runner. |
| `ct_prompteng` (Prompt Engineer) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Unverified remote only | Conditional | No | Verify | Prompt-writing role; generation-provider execution unverified. |
| `ct_motion` (Motion Designer) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Unverified remote only | Conditional | No | Provider | Motion/pacing advice; no rendering integration verified. |
| `ct_qc` (QC) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Unverified remote only | Conditional | No | Provider | QA prompt; no connected visual QA pipeline verified. |
| `ct_mkt` (Marketing Reviewer) | Yes | Active orbit | Yes, explicit | Yes, profile/delegation | Yes, limited | Conditional | No | Verify | Instagram profile/insights/media reads; not publishing |

## Low-risk activation completed

`AgentRuntime.agent_for_tool("jarvis_agent", args)` now resolves the requested registered specialist. Previously every explicit specialist call appeared as the coordinator. The same validated ID drives `handoff` and `started` events, so the existing client orbit can show the real specialist. Unknown IDs still resolve safely to the coordinator and the execution handler rejects unknown profiles. No new provider capability was invented or enabled.

`tests_agent_activation.py` checks all 21 profiles/registries, all 21 explicit routes and runtime payloads, invalid IDs, and existing provider routes (four tests). Registries remain identical.

## Material constraints

- `agent_runner.ENFORCEMENT_TYPE` remains `request-level`. Profile allowlists do not prove enforcement inside remote Hermes. Restrict and verify the deployed Hermes tool profile before enabling sensitive autonomous execution.
- Native device/home/security/media actions remain unavailable. Approving a UI card cannot manufacture a connected provider.
- Text-only prompts are useful specialist roles, but are not evidence of operational monitoring, transactions, video rendering, device control, or an external service integration.
- Meeting Agent is not registered among these 21 agents. Any foundation added tonight must remain explicitly unavailable until its authorized capture/storage/execution contract is implemented.

Sources: `JARVIS/Resources/AGENT-REGISTRY.json`, `JARVIS/Agents/AgentRouter.swift`, `JARVIS/Core/JarvisHeroView.swift`, `phase3/backend/AGENT-REGISTRY.json`, `agent_profiles.py`, `agent_runtime.py`, `agent_runner.py`, `realtime.py`, and provider dispatch modules.
