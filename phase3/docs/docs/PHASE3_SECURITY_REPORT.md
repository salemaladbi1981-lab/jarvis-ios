# JARVIS — Phase 3 Security Report

## Secret handling
- Provider secrets live ONLY in backend environment (OPENAI_API_KEY etc.).
- Clients hold no long-lived secrets; no API key in Swift/git/registry/screenshots/logs.
- Verified: no secret literals committed to the repo.

## Approval model (verified by unit test)
| Case | Result |
|---|---|
| core_home + unlock-door | approval required ✅ |
| core_home + read-temperature | no approval ✅ |
| core_dealmaker + financial-commitment | approval required ✅ |
| unknown agent + action | deny-by-default ✅ |
| approval with changed params | rejected (parameter_mismatch) ✅ |
| approval expired/unknown | rejected ✅ |

## Privileged execution
- Privileged tools execute in the trusted control plane, not the untrusted client.
- High-risk tools require approval before execution (ToolGateway refuses otherwise).

## Audit
- Real actions logged: timestamp, session, agent, tool, action, risk,
  approval requirement/result, execution result/error. No raw mic audio,
  no long-lived secrets.

## Status
- Backend logic unit-tested locally: PASS.
- End-to-end privileged-tool security test on device: NOT MEASURED (deferred to
  Pre-Release Hardening).
