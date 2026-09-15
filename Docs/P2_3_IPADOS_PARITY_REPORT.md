# JARVIS — P2.3 iPadOS Parity Report

## Basis
Runtime screenshots from iPad Pro 11-inch Simulator (portrait single-column,
landscape two-zone layout). Honest note: landscape was captured in a portrait
frame (CI cannot rotate the simulator), so landscape is "layout-verified" but
not "orientation-verified".

Legend: Exact / Equivalent / Different.

| Area | Verdict | Note |
|---|---|---|
| Header (Doha left / JARVIS right) | Equivalent | shared header |
| Hero (core + orbit) | Equivalent | shared JarvisHeroView |
| Orbit (8/5/8) | Equivalent | shared registry + orbit |
| Arabic title جارفس | Equivalent | IBM Plex Sans Arabic Bold |
| Greeting | Equivalent | shared |
| Waveform / status | Equivalent | shared, state-driven |
| Smart Home | Equivalent | 2×2, 35%/22°/مغلقة/مطفأ |
| Security | Equivalent | shield/lock/camera |
| Media | Equivalent | Blinding Lights + cover + controls |
| Quick Suggestions | Equivalent | 5 chips |
| Voice Input Bar | Equivalent | mic + «أنا أسمعك…» |
| Bottom Navigation | Equivalent | 4 items + safe area |
| Typography | Equivalent | bundled offline |
| Icons | Equivalent | SF Symbols via resolver |
| RTL | Equivalent | portrait verified |
| Portrait layout | Equivalent | single-column, wide cards (iPhone-derived) |
| Landscape layout | Equivalent | two-zone Hero + cards (logic verified) |
| Landscape orientation | Different | still portrait frame in CI — needs manual rotation |
| Split View | NOT VERIFIED | not automatable in CI |

## Different items
1. **Landscape orientation** — layout correct but frame not rotated in CI.
   Correction: manual `Cmd+Right` on local Mac. Not a code defect.
