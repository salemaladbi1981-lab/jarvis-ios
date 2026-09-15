# JARVIS — P2.2 iOS Test Report

## Build status
**NOT COMPILED** — this host is Linux (no Xcode). The SwiftUI project cannot be
built or run here. Compilation must be performed on macOS/Xcode 15+.
An Xcode-ready project (`JARVIS.xcodeproj`) is now included for direct opening.

## Added in this pass (source-level, verified here)
- `ApprovalPolicyEvaluatorTests` (Swift) + `approval_policy_test.py` (Python):
  6/6 PASS — core_home+unlock-door, core_home+read-temperature,
  core_guardian+disable-camera, core_dealmaker+financial-commitment,
  sys_server+destructive-config, unknown→fail-safe.
- `token_usage_check.py`: PASS — no hard-coded approved colors in views.
- Provider wiring: HomeViewModel initializes with mock providers (unit test).

## What WAS verified here (logic-level, from the P2.1 foundation)
The shared foundation tests run on this host and pass (these cover the registry,
tokens, and state model that the iOS app consumes):

| Test | Result |
|---|---|
| token_parity_test.py (115 fields) | PASS (115/115, 0 failed, 0 missing) |
| registry_decode_test.py (21 agents, 3 groups) | PASS (0 failures) |
| state_parity_test.py (7 states) | PASS (7/7) |

## What was NOT verified here (requires macOS/Xcode/simulator)
- Xcode build success
- offline (airplane-mode) launch
- RTL visual correctness
- all 3 agent groups rendering
- all 7 state transitions visually
- approval mock flow
- scrolling
- reduced-motion behavior
- VoiceOver labels
- screenshot parity vs MOBILE IMAGE A

## Known issues / risks (honest)
1. **SF Symbol names** (`house.fill`, `square.grid.2x2.fill`, `car.fill`,
   `waveform`, `ellipsis`, `shield.fill`, `video.fill`, `lock.fill`, etc.)
   should be verified on Xcode — if any symbol is renamed in the target iOS
   version it must be corrected.
2. **Font PostScript names** (`IBMPlexSansArabic-Bold`,
   `CormorantGaramond-SemiBold`) must be confirmed against the actual bundled
   .ttf files; adjust the `.custom(...)` calls if they differ.
3. **`JarvisMotion` / `JarvisRadius` / `JarvisSpacing`** are referenced in views
   as bare members of the generated enums; if Xcode's target membership is
   missing for `JarvisTokens.swift` the build will fail — ensure it is added to
   the app target.
