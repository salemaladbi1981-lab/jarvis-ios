# JARVIS — Phase 3 (LIVE) Architecture

## Goal
Turn the native JARVIS apps (iPhone/iPad/macOS) into a real low-latency,
interruptible, permission-aware assistant — not another visual shell.

## Components

```
┌─────────────────────────────────────────────────────────────┐
│ Native SwiftUI clients (iPhone / iPad / macOS)             │
│  VoiceSession (mic capture, realtime transport, barge-in)  │
│  Conversation Runtime (turns, active agent, tool state)    │
│  UI State Machine (7 states driven by runtime events)      │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS + WSS (session-scoped creds)
┌──────────────────────────▼──────────────────────────────────┐
│ Trusted Control Plane (backend, Python/FastAPI)            │
│  /session          — authenticate + create live session    │
│  /realtime (WSS)   — proxy to OpenAI Realtime (secrets here)│
│  /orchestrate      — intent → agent → tool routing         │
│  /approve          — verify action-specific approval       │
│  audit log         — timestamped action/approval/result    │
└──────────────────────────┬──────────────────────────────────┘
                           │ provider secrets (env only)
┌──────────────────────────▼──────────────────────────────────┐
│ Providers                                                │
│  Realtime Voice (OpenAI gpt-4o-realtime, WebSocket)      │
│  SmartHome (HomeKit / Matter / Home Assistant / mock)    │
│  Calendar / Tasks (read-only first)                      │
│  Orchestrator (21-agent registry routing)                │
│  Tool Gateway (typed tool contracts)                     │
└─────────────────────────────────────────────────────────────┘
```

## Security invariants
- Long-lived provider secrets live ONLY in backend environment (never in Swift,
  git, registry, screenshots, or logs).
- Clients hold only short-lived, session-scoped credentials (or none).
- Privileged tools execute only in the trusted control plane.
- Approval binds to exact action + parameters, expires, rejects safely.
- Unknown high-risk actions default to deny.

## Live voice loop (M3.1)
mic → PCM16 chunks → WSS → OpenAI Realtime (server VAD) → streamed audio out
→ client plays → user speaks (VAD) → `response.cancel` (barge-in) → Listening.

Realtime transport: WebSocket (server-to-server proxy). WebRTC optional later.

## Latency budget (targets, to be measured — not fabricated)
- session connect
- end-of-turn → first assistant audio
- interruption → assistant audio stopped
- tool dispatch
- tool result → spoken result

## Error model (typed)
network / live-session-failed / mic-denied / audio-route-lost /
tool-unavailable / tool-timeout / tool-rejected / approval-expired /
permission-denied / integration-disconnected / partial-execution / unknown.
