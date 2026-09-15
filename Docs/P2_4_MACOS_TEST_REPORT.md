# JARVIS — P2.4 macOS Test Report

## Environment
- Build host: GitHub Actions `macos-14` (Xcode 15.4, macOS 14.5 SDK)
- Target: Native macOS app (SwiftUI), deployment target macOS 14
- Screenshots: 9 captured at 1920×1080

## Results

| Test | Result |
|---|---|
| macOS Xcode build | PASS |
| macOS app bundle produced | PASS (JARVIS Mac.app) |
| macOS app launch | PASS |
| Three-zone layout (left nav+cards / center hero / right) | PASS |
| Core group (8) | PASS |
| System group (5) | PASS |
| Content group (8) | PASS |
| Idle / Listening / Thinking / Speaking / Executing / Alert / Approval | PASS |
| Approval flow (unlock-door → approval / read-temperature → none) | PASS |
| RTL (forced right-to-left) | PASS |
| Fonts / icons (bundled) | PASS |
| Resizable window | NOT VERIFIED (fixed min-size capture) |
| Offline launch | NOT VERIFIED |
| Reduced Motion | NOT VERIFIED |
| VoiceOver | NOT VERIFIED |
| FPS / memory / startup | NOT MEASURED |

## Known issues / honest limitations
1. macOS screenshots are full-desktop captures (1920×1080) via `screencapture`;
   the app window renders correctly but window-specific capture isn't automated.
2. Offline / reduced-motion / VoiceOver / profiling deferred to Apple QA.
