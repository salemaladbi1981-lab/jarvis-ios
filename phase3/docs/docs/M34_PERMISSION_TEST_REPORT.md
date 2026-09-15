# JARVIS — M3.4 Permission Test Report

## States implemented (EventKit)
notDetermined / authorized / denied / restricted / unavailable.

## Behavior
- denied → structured `permission_denied`, no fake results, no prompt loop.
- notDetermined → `permission_required` (UI may request).
- unauthorized reads return structured error (no partial/mock data labeled real).

## Test status
- Permission logic (source) implemented: PASS.
- Real permission prompt/grant on device: PENDING (Apple runtime).
