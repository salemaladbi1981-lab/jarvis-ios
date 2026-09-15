# P2.2 — Font Packaging Check

All fonts bundled offline (no web dependency).

| Filename | Family | Weight | PostScript name (expected) | Info.plist | Used at |
|---|---|---|---|---|---|
| IBMPlexSansArabic-Regular.ttf | IBM Plex Sans Arabic | 400 | IBMPlexSansArabic-Regular | UIAppFonts | body/cards |
| IBMPlexSansArabic-Bold.ttf | IBM Plex Sans Arabic | 700 | IBMPlexSansArabic-Bold | UIAppFonts | title «جارفس» |
| CormorantGaramond-SemiBold.ttf | Cormorant Garamond | 600 | CormorantGaramond-SemiBold | UIAppFonts | JARVIS wordmark |

## Fallback
- Arabic fallback: Segoe UI / system-ui (per DESIGN-TOKENS typography).
- Display fallback: Georgia / serif.
- `.custom("IBMPlexSansArabic-Bold", ...)` and `.custom("CormorantGaramond-SemiBold", ...)`
  must match the bundled PostScript names. If the exact PostScript name differs
  on the target macOS, update the `.custom(...)` calls to match.

## Verification
- Font files present in `JARVIS/Assets/Fonts/` (3 .ttf, valid TrueType magic bytes).
- Registered in `Info.plist` → `UIAppFonts`.
- Offline: no Google Fonts / CDN URL anywhere in the source.
