# JARVIS — M3.4 Real Read Test Report

## Status
M3.4 Implementation: PASS (13 backend tests)
M3.4 Real Data Runtime: PENDING (requires Apple device + permission)

## Backend tests (tests_m34.py): 13 PASS / 0 FAIL
- Arabic/English routing (calendar.today / next_event / reminders.upcoming)
- unrelated request does not touch EventKit
- typed tool outputs
- mock clearly marked
- no write tool exposed
- all tools risk low
- no secret committed

## Real-data runtime (PENDING)
Requires a physical/local Apple runtime with Calendar/Reminders permission.
Procedure: grant permission → create harmless test entries → ask the read tool
→ compare structured result to source → confirm no write occurred.
Not fabricable in CI (no personal data / EventKit on Linux runner).
