# JARVIS — P2.2 iOS Parity Report

## Important honesty note (read first)
This report is a **source-level design-to-code parity analysis**, NOT a
pixel-measured visual comparison. This build was authored on a Linux host with
**no Xcode / no iOS simulator**, so it was impossible to produce real iPhone
screenshots or run the app. The analysis compares the SwiftUI source against
the governing sources (MOBILE IMAGE A, DESIGN-TOKENS.json, AGENT-REGISTRY.json,
ICON-MAP.md, TYPOGRAPHY.md, approved Phase 1 Mobile). Every item below is
marked against the *intended* result encoded in code.

Legend: Exact / Equivalent / Different (each Different must justify).

## Parity table

| Area | Verdict | Note |
|---|---|---|
| Header (الدوحة + time + JARVIS) | Equivalent | Location + live clock + Cormorant wordmark; quiet, no chrome |
| Jarvis Core | Equivalent | Canvas + TimelineView: layered radial glow, intersecting rings (0/30/60/105°), deterministic particles; 250px ≤ 280px |
| Agent Orbit | Equivalent | 8/5/8 nodes, one group at a time, horizontal Arabic chips, even radial distribution |
| Title جارفس | Equivalent | IBM Plex Sans Arabic Bold 30px |
| Greeting | Equivalent | «مساء الخير يا دكتور.» + «كل شيء تحت السيطرة.» |
| Waveform | Equivalent | 40 bars, state-driven amplitude, TimelineView |
| Status line | Equivalent | state-driven (idle → «أنا أستمع إليك…») |
| Smart Home | Equivalent | 2×2 grid: الإضاءة 35% / المكيف 22° / الستائر مغلقة / التلفزيون مطفأ + تجريبي |
| Security | Equivalent | الأمان + جميع الأنظمة طبيعية + الأبواب مقفلة + الكاميرات تعمل + تجريبي |
| Media | Equivalent | Blinding Lights / The Weeknd + cover-art placeholder + progress + prev/play/next + تجريبي |
| Quick Suggestions | Equivalent | 5 Arabic chips, 2-column grid, no overflow |
| Voice Bar | Equivalent | glowing mic + «أنا أسمعك…» |
| Bottom Nav | Equivalent | 4 items (الرئيسية/الأجهزة/السيارة/المزيد), Home active |
| Typography | Equivalent | IBM Plex Sans Arabic 400/700 + Cormorant Garamond 600 (bundled offline) |
| Icons | Different | **SF Symbols used for the demo** (house, lock, mic, play, etc.). Justification: SF Symbols are visually equivalent for these generic utility/media glyphs per ICON-MAP.md allowance («if SF Symbol is visually equivalent, document it»). Custom SVG vectors not yet bundled — deferred until a macOS host is available to render/export them. |
| Colors | Equivalent | All from generated JarvisTokens (Color(hex:)) |
| Spacing/Radius | Equivalent | All from JarvisSpacing / JarvisRadius tokens |
| RTL | Equivalent | Forced `.layoutDirection = .rightToLeft`; all layouts use leading/trailing |

## Different items (with reasons)
1. **Icons** — SF Symbols (documented equivalence) instead of custom SVG. Reason:
   custom SVG export requires a macOS/Xcode host; visually-equivalent SF Symbols
   satisfy the demo while preserving the canonical icon IDs in ICON-MAP.md.

## Cannot-be-verified on this host
- Real iPhone screenshot parity vs MOBILE IMAGE A (requires simulator)
- Pixel-level alignment
