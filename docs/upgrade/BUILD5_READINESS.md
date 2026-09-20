# Build 5 Readiness Gate

Date: 2026-09-20
Release branch under audit: `chatgpt-write-test`

## Current decision

**BUILD 5 NOT YET RELEASE-READY.**

The stability baseline is green in CI, but the release number remains Build 4 and the final Swift/meeting-foundation head must complete iOS + macOS CI before any Build 5 version bump or distribution action.

## Verified foundation

- Phase 1 stability gate has a fully green cumulative CI run (`#174`, run `35487993456`) covering backend, iOS build/simulator flows, real-contract screenshots, macOS build, Swift unit tests, macOS launch, and screenshots.
- Text chat transport now has explicit HTTP/auth/timeout/offline handling, SSE termination detection, send serialization, and retry deduplication.
- Enrollment/session transport verifies HTTP response, rejects an empty token, and verifies Keychain persistence before considering enrollment successful.
- Production launches no longer rely on synthetic provider data merely to appear healthy; demo data is gated behind explicit demo launch behavior.
- Phase 2 agent activation audit is complete. The repository now distinguishes declared agents from explicitly verified executions and does not claim broad automatic activation.
- Phase 3 meeting foundation contains policy/state/interfaces only. It does not implement microphone recording, stealth capture, or a platform bypass.

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
5. Final head: Swift unit tests PASS, including meeting consent/authorization policy tests.
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
- The remote comparison to `main` is ahead and not behind at the audit point; no merge was performed.
- No TestFlight publication was performed.
- No production secret was changed.
- No WhatsApp/LinkedIn integration was added.
- No cross-device control work was started.
- Local workstation cleanliness/stashes cannot be inferred from the remote GitHub branch and are not claimed here.

## Promotion rule

Only after the final-head CI and required real-device smoke checks pass should the release preparation commit bump iOS `CURRENT_PROJECT_VERSION` from 4 to 5. TestFlight upload and merge remain separate owner-approved actions.
