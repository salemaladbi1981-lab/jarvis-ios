# JARVIS — P2.2 iOS Closure Summary

## Completed
- Native SwiftUI Home built (single-screen, approved hierarchy)
- Xcode build: PASS (GitHub Actions macOS runner)
- Simulator launch: PASS (iPhone 15, iOS 17.5)
- Core (8) / System (5) / Content (8) groups verified
- Seven states verified (idle→approval)
- Approval flow verified (core_home + unlock-door → approval; read-temperature → no approval)
- Bottom-navigation overlap resolved (opaque + safeAreaInset)
- Arabic date/time corrected (ar_QA, Western numerals)
- Header placement corrected (Doha left / JARVIS right)
- RTL forced right-to-left
- 10 runtime screenshots captured (Screenshots/)

## Remaining / Known Issues
- Offline (airplane mode), Reduced Motion, and VoiceOver are implemented in
  source but not exercised in CI — runtime-unverified.
- FPS / memory / startup not measured (no Instruments in CI).
- Custom SVG icons deferred (SF Symbol equivalents in use).

## Deferred to Phase 3
- Real voice engine (STT/LLM/TTS)
- Real Home Assistant
- Real Calendar
- Real media provider
- Live weather
- Cross-device sync

## Next Phase
**P2.3 — Native macOS Home**

## Roadmap scope note
Current personal-device roadmap: **iPhone → iPad → Mac**. Windows is removed
from the active plan.
