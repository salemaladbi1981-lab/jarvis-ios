# JARVIS — P2.2 iOS Test Report (Runtime)

## Environment
- Build host: GitHub Actions `macos-14` runner (Xcode 15.4, iOS 17.5 SDK)
- Simulator: iPhone 15 (iOS 17.5)
- Evidence: 10 deterministic screenshots captured via launch arguments

## Results

| Test | Result |
|---|---|
| Xcode build | PASS |
| iOS Simulator launch | PASS |
| Core group (8) | PASS |
| System group (5) | PASS |
| Content group (8) | PASS |
| Idle state | PASS |
| Listening state | PASS |
| Thinking state | PASS |
| Speaking state | PASS |
| Executing state | PASS |
| Alert state | PASS |
| Approval state | PASS |
| Approval flow (core_home + unlock-door) | PASS |
| Safe read without approval (core_home + read-temperature) | PASS |
| RTL (forced `.layoutDirection = .rightToLeft`) | PASS |
| Arabic date/time (locale ar_QA, Western numerals) | PASS |
| Fonts (IBM Plex Sans Arabic + Cormorant bundled) | PASS |
| Icons (SF Symbols via JarvisIconResolver) | PASS |
| Bottom-nav overlap fix | PASS |
| Offline launch (airplane mode) | NOT VERIFIED |
| Reduced Motion | NOT VERIFIED |
| VoiceOver / accessibility | NOT VERIFIED |

## Approval flow (verified)
- `core_home + unlock-door` → registry policy requires approval → state = Approval,
  "طلب موافقة" card with Approve/Reject appears (see `10_approval.png`).
- `core_home + read-temperature` → default policy = none → no approval (executes).
- Unit test `ApprovalPolicyEvaluatorTests` + `approval_policy_test.py` (6/6 PASS).

## Known issues / honest limitations
1. **Arabic OCR is unreliable on this host** — the assistant cannot verify each
   agent display name pixel-perfectly from the screenshots; group counts and
   layout were verified, and the owner reviewed the screenshots visually.
2. **Offline / Reduced Motion / VoiceOver** were not exercised in CI (the
   screenshot workflow does not toggle airplane mode, Reduce Motion, or
   VoiceOver). They are implemented in source but remain runtime-unverified.
3. **Runtime fixes applied this phase**: added `CFBundleExecutable`/
   `CFBundlePackageType`/`CFBundleInfoDictionaryVersion` to Info.plist;
   opaque bottom nav background covering the bottom safe area;
   `safeAreaInset(edge: .bottom)`; header LTR placement; Arabic date formatter.
