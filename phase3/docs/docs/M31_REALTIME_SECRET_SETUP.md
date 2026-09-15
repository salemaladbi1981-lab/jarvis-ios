# JARVIS — M3.1 Realtime Secret Setup

## Rule
The future realtime provider credential is a SERVER/ENVIRONMENT secret only.
Never: Swift, git, Telegram, screenshots, reports, logs.

## Required environment variable (backend)
- `OPENAI_API_KEY` (primary realtime provider, e.g. gpt-4o-realtime).
- Optional fallback: `OPENROUTER_API_KEY` (gpt-audio) if OpenRouter realtime is used.

## Where installed
On the JARVIS control-plane host, in the process environment / `.env` (gitignored).
Installed by the operator (never pasted into chat).

## Which process reads it
`phase3/backend/config.py` → `OPENAI_API_KEY`, consumed by `realtime.py`
(the WebSocket proxy to OpenAI Realtime). Nothing else reads it.

## Client authorization model
- Apple clients do NOT hold the provider key.
- Client calls `/session` → receives a short-lived `session_id`.
- Client opens `/realtime` WSS; the backend proxies using the server-side key.
- (Optional hardening) backend issues a short-lived, single-session JWT/bearer
  bound to the session_id; clients hold only that, never the provider key.

## Rotation / revocation
1. Rotate the env secret on the host.
2. Restart the control plane process.
3. Clients reconnect → new session (old sessions TTL-expire).
No client code change required.

## Verification (secret absence)
`tests.py` scans repo source for `sk-[A-Za-z0-9]{20,}` → 0 hits (PASS).
