# JARVIS — M3.4 Real Read Test Report

## Status
M3.4 Implementation: PASS (13 backend tests)
M3.4 Real Data Runtime: PENDING — requires Apple device + user permission

## Provider-mode assertion (added this gate)
Every CalendarToolResult now carries `providerMode` ("real"/"mock") and
`providerName` ("AppleEventKitProvider"/"MockEventKitProvider").
A real-data test must show providerMode = real; mock results are never a real PASS.

## Backend tests (tests_m34.py): 13 PASS / 0 FAIL
Arabic/English routing, typed outputs, mock marked, no write tool, low risk,
no secret committed.

## Real-data proof (PENDING — owner checklist)
See M34_OWNER_CHECKLIST.md — six actions, everything else automated.
Required: Calendar event `JARVIS Runtime Test` + Reminder `JARVIS Reminder Test`
read via AppleEventKitProvider with permission, values match, no write.
