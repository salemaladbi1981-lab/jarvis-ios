# JARVIS Stability Audit — chatgpt-write-test

Updated: 2026-09-20

## Scope

Phase 1 stability gate before agent activation or broader feature work.

## Verified in source / regression coverage

- POST `/conversations` envelope decode matches backend contract.
- Main composer Enter submit is wired.
- Main composer duplicate-send guard is present.
- Chat SSE request sends both `X-Jarvis-Session` and `X-Jarvis-Workspace`.
- Chat SSE validates HTTP status before parsing events.
- Chat errors distinguish expired/invalid session, forbidden workspace/action, timeout, offline/network loss, and temporary server failure.
- Chat detects a stream that terminates without a terminal SSE event.
- Chat retry does not append a duplicate local user message.
- Concurrent/repeated chat requests are guarded.
- CI is enabled for `chatgpt-write-test` so this branch can be evaluated without merging.

## Still required before Phase 1 is GREEN

1. GitHub Actions backend-tests PASS.
2. iOS simulator build PASS.
3. macOS build + Swift unit tests PASS.
4. Production mock-provider leakage review remains green.
5. Memory isolation/runtime-path regression suite remains green.
6. Voice lifecycle/stability regression suite remains green.
7. Real-device-only behavior stays explicitly DEVICE-ONLY; simulator success must not be promoted to device verification.

## Gate rule

Do not start broad Agents activation, cross-device control, TestFlight publishing, or merge-to-main while any Phase 1 CI job is failing or unknown.
