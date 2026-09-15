# JARVIS — Phase 3 SmartHome Platform Matrix

| Capability | iOS (HomeKit) | iPadOS (HomeKit) | macOS (HomeKit) | Matter | Home Assistant | Mock (CI) |
|---|---|---|---|---|---|---|
| Rooms/devices read | Supported | Supported | Supported | Supported | Bridge | ✅ |
| Lights on/off/level | Supported | Supported | Supported | Supported | Bridge | ✅ |
| Thermostat target | Supported | Supported | Supported | Supported | Bridge | ✅ |
| Blinds/curtains | Supported | Supported | Supported | Supported | Bridge | ✅ |
| Door/lock state read | Supported | Supported | Supported | Supported | Bridge | ✅ |
| Door/lock UNLOCK | approval | approval | approval | approval | approval | ✅ |

## Notes
- HomeKit availability differs per OS — do NOT assume iOS works unchanged on
  macOS; verify entitlements (com.apple.developer.homekit) per target.
- Lock/unlock and security-disabling always route through approval.
- Mock provider used in CI; real adapters behind SmartHomeProvider abstraction.

## Status
- Abstraction defined: PASS.
- Real HomeKit/Matter adapter: NOT IMPLEMENTED (deferred to M3.4/M3.5).
