# JARVIS — M3.4 EventKit Architecture

## Components
- `AppleEventKitProvider` (Swift, EventKit) — real read-only provider, normalizes
  EKEvent/EKReminder into typed `CalendarEvent`/`ReminderItem`.
- `CalendarTools` — typed tools calendar.today / calendar.next_event /
  reminders.upcoming, provider-injected (real or mock).
- `MockCalendarProvider` — explicit mock for CI (mode: mock).
- Backend Orchestrator routes Arabic/English intents to the correct tool id.

## Flow
User request → Orchestrator route → tool id → client CalendarTools (EventKit
or mock) → structured result → UI state → response.

## Read-only
No write methods exist in M3.4 (no create/edit/delete/complete).
