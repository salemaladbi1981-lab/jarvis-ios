# Build 5 Readiness Gate

Date: 2026-09-20
Release branch under audit: `chatgpt-write-test`

## Current decision

**BUILD 5 NOT YET RELEASE-READY.**

The cumulative stability/agent/meeting baseline through commit `59e8db996c20d9b88fc601afb3652273f48a12cb` is fully green in CI run `#180` (`35490108787`). A later shared meeting-session lifecycle commit (`4e16a55f1a145e25496485c7a68c0c50a8e999b7`) adds only deterministic state-policy plumbing plus regression tests; that newer head must also pass iOS + macOS CI before any Build 5 version bump or distribution action.

## Verified foundation

- Phase 1 stability gate is green in cumulative CI.
- CI run `#180` (`35490108787`) passed all three jobs on commit `59e8db996c20d9b88fc601afb3652273f48a12cb`: backend tests, iOS build/simulator flows including real-contract screenshots, and macOS build/Swift tests/screenshots.
- Text chat transport has explicit HTTP/auth/timeout/offline handling, SSE termination detection, send serialization, and retry deduplication.
- Enrollment/session transport verifies HTTP response, rejects an empty token, and verifies Keychain persistence before considering enrollment successful.
- Production launches no longer rely on synthetic provider data merely to appear healthy; demo data is gated behind explicit demo launch behavior.
- Phase 2 agent activation audit is complete. The repository distinguishes declared agents from explicitly verified executions and does not claim broad automatic activation.
- Phase 3 meeting foundation contains policy/state/interfaces only. It does not implement microphone recording, stealth capture, or a platform bypass.
- Shared meeting lifecycle policy prevents a future meeting session from jumping directly from idle/authorization-wait into active, and maps incomplete live-capture authorization to `awaitingAuthorization` rather than pretending the session is ready.

## Build/version metadata

Generated iOS project settings currently declare:

- `MARKETING_VERSION = 0.1.0`
- `CURRENT_PROJECT_VERSION = 4`

Do **not** change `CURRENT_PROJECT_VERSION` to 5 until the final release candidate head passes the release gate below.

## Final Build 5 release gate

1. Final `chatgpt-write-test` head: backend tests PASS.
2. Final head: iOS build PASS.
3. Final head: iPhone/iPad simulator and real-contract screenshot workflow PASS.
4. Final head: macOS build PASS.
5. Final head: Swift unit tests PASS, including meeting consent/authorization and lifecycle-policy tests.
6. No production mock-provider regression.
7. No unresolved auth/session/chat blocker.
8. Physical-device smoke test for the release-critical iPhone flows.
9. Device-only voice claims remain explicitly unverified until tested on real hardware.
10. Owner explicitly approves merge/version bump/distribution.

## Device-only / external gates

The following must not be inferred from simulator or CI success:

- iPhone locked-screen voice behavior.
- Siri/App Intent behavior on the owner device.
- AirPods and Shokz microphone/output routing.
- Bluetooth route switching during a live session.
- Real microphone lifecycle/background transitions.
- Any future authorized live meeting capture implementation.

## Agent activation release risk

The current specialist-agent execution boundary is request-level. Native Hermes per-agent tool allowlisting is not available/proven. Therefore:

- declared profile tool labels are not executable-tool proof;
- broad automatic specialist routing remains disabled;
- consequential agents/actions remain behind their existing approval/tool-guard boundaries;
- no Build 5 readiness claim depends on broad agent auto-activation.

## Release hygiene

- Work remains isolated to `chatgpt-write-test`.
- No merge to `main` was performed.
- No TestFlight publication was performed.
- No production secret was changed.
- No WhatsApp/LinkedIn integration was added.
- No cross-device control work was started.
- Local workstation cleanliness/stashes cannot be inferred from the remote GitHub branch and are not claimed here.

## Promotion rule

Only after the final-head CI and required real-device smoke checks pass should the release preparation commit bump iOS `CURRENT_PROJECT_VERSION` from 4 to 5. TestFlight upload and merge remain separate owner-approved actions.
