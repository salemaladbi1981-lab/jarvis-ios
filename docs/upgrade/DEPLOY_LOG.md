# JARVIS UPG-1 — Deploy Log

2026-09-19 (UTC)

## Deployed to LIVE (jarvis-api.qeyas.app → localhost:8000)
| File | Change |
| --- | --- |
| realtime.py | voice fix (non-blocking tool execution + turn_generation + structured logging) — 6-tool live-compatible build |
| maps_provider.py | dir_action=navigate (turn-by-turn) |
| config.py | language instruction (explicit requests override default) + maps instruction |

## Rollback
Backup: `.deploy-backup-20260919-002337/` (realtime.py, maps_provider.py, config.py — pre-deploy copies)
Git baseline tag: `UPG-0-BASELINE` → `617b110`

## Verification
- py_compile (venv Python 3.13.5): OK
- local /health: `{"ok":true,"provider":"openai"}` OK
- public /health: `{"ok":true,"provider":"openai"}` OK
- import test (realtime, maps_provider, config): OK
- navigate url now: `...&travelmode=driving&dir_action=navigate`

## NOT deployed (blocker)
Phase A/B/C backend modules (memory_tools.py, capabilities_tools.py, agent_tools.py,
agent_profiles.py, agent_runner.py, agent_state.py, agent_audit.py, JARVIS-CAPABILITIES.json,
memory_bridge.py, identity.py, audit_memory.py) are MISSING on LIVE. The full branch
realtime.py (9 tool groups) was NOT deployed; a 6-tool live-compatible build was deployed instead
so voice keeps working. Deploying Phase A/B/C to LIVE is a separate gate (UPG-2+), not UPG-1.

## iOS (device) — NOT built, NOT tested
Core Location (LocationManager), HeaderView real city, truncate on barge-in, Info.plist
permission: all SOURCE_IMPLEMENTED on the branch, BUILD_PENDING (no Mac/Xcode here).
