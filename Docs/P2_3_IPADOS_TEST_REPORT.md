# JARVIS — P2.3 iPadOS Test Report

## Environment
- Build host: GitHub Actions `macos-14` (Xcode 15.4, iOS 17.5 SDK)
- Simulator: iPad Pro 11-inch (4th gen), iPadOS 17.5
- Screenshots: 10 captured (5 portrait + 5 landscape-layout)

## Results

| Test | Result |
|---|---|
| Xcode build | PASS |
| iPad Simulator launch | PASS |
| Portrait single-column hierarchy | PASS |
| Portrait — Core group (8) | PASS |
| Portrait — System group (5) | PASS |
| Portrait — Content group (8) | PASS |
| Portrait — 7 states | PASS |
| Approval flow (unlock-door → approval / read-temperature → none) | PASS |
| Landscape two-zone LAYOUT | PASS (logic verified) |
| Landscape true orientation (width > height) | PENDING — requires manual Mac rotation |
| RTL (portrait) | PASS |
| Fonts / icons (bundled) | PASS |
| Bottom-nav safe area | PASS |
| Split View | NOT VERIFIED (CI automation cannot drive multitasking) |
| Offline launch | NOT VERIFIED |
| Reduced Motion | NOT VERIFIED |
| VoiceOver | NOT VERIFIED |

## Known issues / honest limitations
1. **Landscape orientation cannot be captured in headless CI.** The two-zone
   layout renders correctly (via `-landscape`), but the Simulator frame stays
   1668×2388 because headless `simctl`/`osascript`/`requestGeometryUpdate` all
   cannot rotate the device. True landscape (width>height) requires manual
   `Device → Rotate Right` on a local Mac.
2. Arabic OCR is unreliable on this host — agent names were verified by the
   owner visually, not pixel-automated.
3. Split View / offline / reduced-motion / VoiceOver not exercised in CI.
