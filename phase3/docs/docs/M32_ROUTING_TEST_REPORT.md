# JARVIS — M3.2 Routing Test Report

Automated tests (tests.py) — 23 PASS / 0 FAIL.

| # | Case | Result |
|---|---|---|
| A | Direct conversational request (no tool) | PASS |
| B | Safe read → read-temperature (no approval) | PASS |
| C | Sensitive unlock-door → approval required (blocked) | PASS |
| D | Content request → content agent (no home tool) | PASS |
| E | Unavailable capability → structured, no fake success | PASS |
| F | Ambiguous request → no destructive guess | PASS |
| — | Malformed/unavailable tool → structured error | PASS |
