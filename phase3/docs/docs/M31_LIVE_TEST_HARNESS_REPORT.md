# JARVIS — M3.1 Live Test Harness Report

## Deterministic state-machine harness (no audio) — 14 PASS / 0 FAIL

| Sequence | Result |
|---|---|
| connected → idle | PASS |
| listening → listening | PASS |
| speaking → speaking | PASS |
| barge-in (interrupted) → listening | PASS |
| new turn accepted after barge-in | PASS |
| connecting → thinking | PASS |
| tool → executing | PASS |
| awaiting approval → approval | PASS |
| error → alert | PASS |
| disconnected → idle | PASS |
| reconnect → idle | PASS |
| network failure → alert | PASS |
| mic denied → alert/error path | PASS |

## Coverage
session lifecycle, barge-in, reconnect, network failure, mic denied, tool call,
approval — all verified at state-machine level before real audio exists.
