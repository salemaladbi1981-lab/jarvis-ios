# JARVIS — Phase 3 Integration Matrix

| Integration | Type | Status | Notes |
|---|---|---|---|
| Realtime voice (OpenAI Realtime) | voice | scaffolded | needs OPENAI_API_KEY + device |
| SmartHome (HomeKit/Matter/HA) | read/control | abstraction only | M3.4/M3.5 |
| Calendar/Tasks | read/write | abstraction only | read-first |
| Media | read/control | mock only | M3.x |
| Weather | read | mock only | M3.x |
| Memory / context | session | scaffolded | durable prefs later |

## Capability-unavailable rule
If an integration does not exist, the Orchestrator returns
`capability_unavailable` — never pretends success.
