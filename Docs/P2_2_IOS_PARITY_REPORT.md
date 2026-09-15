# JARVIS — P2.2 iOS Parity Report (Runtime)

## Basis
Runtime screenshots from iPhone 15 Simulator (see `Screenshots/`), compared
against MOBILE IMAGE A. The owner visually reviewed the screenshot set and
accepted it. Honest note: the assistant cannot visually compare against
MOBILE IMAGE A directly (no vision on this host); verdicts below reflect the
accepted runtime build + owner review + source-to-token fidelity.

Legend: Exact / Equivalent / Different.

| Area | Verdict | Note |
|---|---|---|
| Header placement (Doha left / JARVIS right) | Equivalent | fixed via internal LTR |
| Doha/date placement | Equivalent | left, matches reference |
| JARVIS wordmark | Equivalent | Cormorant Garamond 600, right side |
| Arabic date/time | Equivalent | Arabic locale ar_QA, Western numerals |
| Core | Equivalent | Canvas + rings + particles + bloom |
| Orbit | Equivalent | 8/5/8 one group at a time |
| Agent chips | Equivalent | dark fill + cyan border, horizontal labels |
| Arabic title جارفس | Equivalent | IBM Plex Sans Arabic Bold |
| Greeting | Equivalent | «مساء الخير يا دكتور.» + subtitle |
| Waveform | Equivalent | state-driven bars |
| Status line | Equivalent | state-driven |
| Smart Home | Equivalent | 2×2 grid 35%/22°/مغلقة/مطفأ + تجريبي |
| Security | Equivalent | shield/lock/camera + تجريبي |
| Media | Equivalent | Blinding Lights + cover + progress + controls + تجريبي |
| Quick Suggestions | Equivalent | 5 chips, 2 columns |
| Voice Input Bar | Equivalent | glowing mic + «أنا أسمعك…» |
| Bottom Navigation | Equivalent | 4 items, Home active, opaque + safe area |
| Typography | Equivalent | IBM Plex Sans Arabic + Cormorant |
| Icons | Equivalent | SF Symbols (documented in P2_2_ICON_PARITY.md) |
| Colors | Equivalent | all from JarvisColor tokens |
| Spacing | Equivalent | all from JarvisSpacing/JarvisRadius |
| RTL | Equivalent | forced right-to-left |
| Scrolling / safe-area | Equivalent | safeAreaInset bottom, content clears nav |

## Different items
None currently flagged as requiring correction. Icons use documented SF-Symbol
equivalents rather than custom SVG (accepted, documented in ICON_PARITY.md).
