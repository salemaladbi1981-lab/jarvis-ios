# P2.2 — Icon Parity

Resolver: `JarvisIconResolver.symbol(for:)` maps canonical ICON-MAP.md IDs →
native SF Symbols (visually equivalent). Priority: custom vector > equivalent
SF Symbol > documented fallback.

| Canonical ID | Asset used (SF Symbol) | Verdict | Reason |
|---|---|---|---|
| nav.home | house.fill | Equivalent | standard home glyph |
| nav.devices | square.grid.2x2.fill | Equivalent | device grid |
| nav.car | car.fill | Equivalent | car glyph |
| nav.more | ellipsis | Equivalent | more menu |
| home.light | lightbulb.fill | Equivalent | light bulb |
| home.ac | snowflake | Equivalent | AC/snowflake |
| home.curtains | curtains.closed | Equivalent | closed curtains |
| home.tv | tv.fill | Equivalent | TV |
| sec.shield | shield.fill | Equivalent | security shield |
| sec.camera | video.fill | Equivalent | camera |
| sec.lock | lock.fill | Equivalent | locked door |
| media.previous | backward.fill | Equivalent | previous track |
| media.play | play.fill | Equivalent | play |
| media.next | forward.fill | Equivalent | next track |
| util.location | location.fill | Equivalent | location pin |
| util.mic | mic.fill | Equivalent | microphone |
| util.waveform | waveform | Equivalent | audio waveform |
| util.alert | exclamationmark.triangle.fill | Equivalent | warning |

## Notes
- All mappings are documented SF-Symbol equivalents; no custom SVG was
  required for the demo because the generic utility/media glyphs are visually
  equivalent. Custom vectors remain the canonical source for any icon that
  diverges (none in this set).
- No emoji. No mixed icon packs.
