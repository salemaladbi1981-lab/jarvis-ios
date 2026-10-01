# Build 5 readiness — 2026-10-01

**Not yet approved for release.** Version remains **0.1.0 (4)**; no archive upload, version bump, main merge or TestFlight publication occurred.

The current work-branch code is `b00cb921b5995217ddd35e0b41ae80ae27d5e227`. See [the overnight report](../../Docs/overnight/OVERNIGHT_REPORT.md) for final CI results, commit ledger and exact file manifest.

Verified locally: 62 portable regression scripts; 36 shared Swift tests; 67 native iOS tests; 38 native Mac tests; clean committed iOS/Mac Release builds. A real Swift client completed authenticated conversation creation, decoding, loading, streamed memory-miss response and duplicate-free refresh against an isolated localhost backend. Simulator Home was inspected on iPhone 18 Pro and iPhone 17e.

Remaining release gates:

1. Deploy/verify matching backend session, request-receipt and memory-isolation changes with the client. Production deployment was not changed tonight.
2. Verify enrollment, expired sessions, chat Send/Return, offline/timeouts and retry against the deployed service on a physical iPhone.
3. Verify microphone permission, Bluetooth/speaker audio, manual-only interruption, red-error recovery, foreground/background and network reconnect on hardware.
4. Verify backend-owned workspace memory, legacy memory migration provenance and external Hermes isolation. The local suite does not certify a remote service's enforcement.
5. Both final-code CI runs passed: work-branch verification `36808580920` and builds/screenshots `36808580906`. Review the artifacts with the physical-device results before release.
6. Review preserved pre-existing local project/signing settings, then perform a separately authorized signed archive/version bump. Current checked-in iOS version is still Build 4.

Unavailable smart-home/security/media integrations remain visibly unavailable. Agents with unverified external tools remain conditional, and meeting capture/storage are contracts plus an honest UI skeleton. Those features must not be advertised as connected or executable. No production credentials, stored memory, git stash or protected-branch history were modified.
