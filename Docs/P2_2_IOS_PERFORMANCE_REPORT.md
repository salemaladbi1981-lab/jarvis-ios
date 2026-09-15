# JARVIS — P2.2 iOS Performance Report

## Status: NOT MEASURED

The runtime screenshots were produced on a GitHub Actions macOS runner via
headless `simctl` launch + screenshot. **No Instruments / Core Animation
profiling was attached to the CI workflow**, so the following are NOT MEASURED:

| Metric | Result |
|---|---|
| FPS — Idle | NOT MEASURED |
| FPS — Listening | NOT MEASURED |
| FPS — Thinking | NOT MEASURED |
| FPS — Speaking | NOT MEASURED |
| FPS — group transition | NOT MEASURED |
| FPS — vertical scroll | NOT MEASURED |
| Memory usage | NOT MEASURED |
| Startup time | NOT MEASURED |
| Obvious frame drops | NOT MEASURED |
| Reduced-motion behavior | NOT MEASURED |

## Why not measured
- The CI pipeline builds + launches + screenshots; it does not run Xcode
  Instruments or a frame-capture harness.
- No values are fabricated. Real FPS/memory measurement requires a local macOS
  session with Instruments (Core Animation template) or a Metal frame counter.

## Design choices made to protect performance (in source)
- Core/orbit/waveform use `Canvas` + `TimelineView(.animation)`; no SceneKit/RealityKit.
- Fixed particle count (15), ring count (4), waveform bars (40).
- `@Environment(\.accessibilityReduceMotion)` disables pulse/wobble and freezes motion.
- No video loops, no heavy shaders.
