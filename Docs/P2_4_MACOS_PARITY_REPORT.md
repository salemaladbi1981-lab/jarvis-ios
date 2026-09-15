# JARVIS — P2.4 macOS Parity Report

## Basis
Runtime screenshots (1920×1080) of the native macOS app, compared against the
approved cinematic desktop direction. Shared SwiftUI components reused from
iPhone/iPad.

Legend: Exact / Equivalent / Different.

| Area | Verdict | Note |
|---|---|---|
| Left zone (nav + Smart Home + Security + Media) | Equivalent | sidebar + cards |
| Center zone (JARVIS + core + orbit + title + waveform + voice) | Equivalent | shared components |
| Right zone (contextual) | Equivalent | minimal, no invented live data |
| Core / orbit renderer | Equivalent | shared JarvisCoreView/Orbit |
| Arabic title جارفس | Equivalent | IBM Plex Sans Arabic Bold |
| Greeting / waveform / status | Equivalent | shared |
| Smart Home / Security / Media | Equivalent | 2×2 / status / track |
| Quick Suggestions | Equivalent | 5 chips |
| Voice Input Bar | Equivalent | mic + «أنا أسمعك…» |
| Typography | Equivalent | bundled offline |
| Icons | Equivalent | SF Symbols via resolver |
| Colors / spacing | Equivalent | generated tokens |
| RTL | Equivalent | forced right-to-left |
| Resizable window | Equivalent | native window, min 1000×640 |

## Different items
None flagged. Right zone is intentionally minimal (no invented live data).
