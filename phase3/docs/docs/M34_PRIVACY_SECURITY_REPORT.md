# JARVIS — M3.4 Privacy & Security Report

## Data minimization
- Fetch only requested scope (today / next / upcoming), no historical crawl.
- Normalize to typed models; no raw EventKit objects past provider boundary.

## Audit
- Audit metadata only (tool, provider mode, permission result, count, status).
- Do NOT audit full titles/notes/attendees/reminder bodies/locations.

## Tests
- No write tool exposed: PASS
- No secret committed: PASS
- All M3.4 tools risk low: PASS
- Mock explicitly flagged: PASS
