# JARVIS — M3.4 Personal Data Flow

## Scope
Only the fields needed to answer the request:
event title, start/end, all-day flag, calendar name (if needed), location
(only when available/needed); reminder title, due date, completion, list.

## Flow
1. EventKit reads on-device (no upload of full calendar).
2. Normalized typed models returned to the Orchestrator.
3. If sent to a reasoning/live service later: only minimum relevant fields,
   never unrelated events/reminders, documented per-request.
4. Audit logs metadata only, not content.

## Prohibited
No background harvesting, no persisting full calendars, no sending content to
unrelated external services.
