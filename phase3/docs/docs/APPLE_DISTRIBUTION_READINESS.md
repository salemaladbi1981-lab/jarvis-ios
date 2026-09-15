# JARVIS — Apple Distribution Readiness Audit

| Item | Status | Notes |
|---|---|---|
| Apple Developer Program (paid enrollment) | NEEDS OWNER ACTION | required for TestFlight/notarization |
| Bundle ID com.salemai.jarvis (iOS) | READY | in project |
| Bundle ID com.salemai.jarvis.mac (macOS) | READY | in project |
| Signing configuration (auto) | READY | CODE_SIGN_STYLE=Automatic |
| Provisioning | NEEDS CREDENTIAL | via Apple Developer account |
| Entitlements (HomeKit, mic, etc.) | NEEDS OWNER ACTION | must add per capability |
| App Store Connect / TestFlight | NEEDS OWNER ACTION | owner must create app record |
| Privacy usage descriptions (Cal/Rem/Mic) | NEEDS OWNER ACTION | NS*UsageDescription in Info.plist |
| Calendar permission description | NEEDS OWNER ACTION | NSCalendarsUsageDescription |
| Reminders permission description | NEEDS OWNER ACTION | NSRemindersUsageDescription |
| Microphone permission description | NEEDS OWNER ACTION | NSMicrophoneUsageDescription |
| App icons / assets | NEEDS OWNER ACTION | app icon not yet produced |
| Version/build numbers | READY | 0.1.0 / 1 |
| macOS signing/notarization | NEEDS OWNER ACTION | Developer ID + notarytool |
| Backend base URL config | READY | session/realtime endpoints |

## Summary
- Code/signing scaffolding: READY.
- Owner-gated items: Apple Developer enrollment, App Store Connect/TestFlight
  app record, entitlements, privacy descriptions, app icon, notarization.
