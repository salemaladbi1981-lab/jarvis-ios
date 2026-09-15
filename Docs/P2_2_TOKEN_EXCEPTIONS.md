# P2.2 — Token Exceptions

Policy: literal values are allowed only for one-off geometry, math constants,
or values not represented in the token system. Everything else consumes a
generated token type.

## Verified: no hard-coded approved colors
`token_usage_check.py` confirms the views contain zero `Color(hex:)` literals —
all colors come from `JarvisColor.*`.

## Documented exceptions (allowed literals)

| Literal | Location | Reason |
|---|---|---|
| Font sizes (30, 16, 13, 15, 12, 11, 22, 20, 18, 14) | Home/Header/Cards | The approved `type_scale_px` values are `[min,max]` ranges (or desktop/mobile pairs), not single values; views pick one value from each range. Mapping ranges→single size is a documented interpretation. |
| `.opacity(0.9)`, `.opacity(0.7)`, `.opacity(0.5)`, `.opacity(0.45)` etc. on token colors | Home/Cards | Tonal variants of a token color not individually represented in the token set; base color still comes from `JarvisColor`. |
| Ring/particle geometry (0.42, 0.62, 0.72, 0.82, 0.90, 1.2 lineWidth, 2.5 bar width, 40 bars, 15 particles) | Core/Waveform | Pure drawing math / counts, not represented as tokens. |
| `size: 250` core diameter, `height: 320` hero | Core/Home | One-off layout geometry derived from the 220–280px approved core range. |
| `250 - 26` orbit radius inset | Orbit | Local geometry to keep chips inside the hero. |

## Result
Exceptions are minimal and every one is justified above. No approved color,
radius, spacing, motion, or icon-size token is re-typed as a literal.
