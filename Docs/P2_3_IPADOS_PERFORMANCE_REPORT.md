# JARVIS — P2.3 iPadOS Performance Report

## Status: NOT MEASURED

| Metric | Result |
|---|---|
| FPS — Idle | NOT MEASURED |
| FPS — Listening | NOT MEASURED |
| FPS — Thinking | NOT MEASURED |
| FPS — Speaking | NOT MEASURED |
| FPS — group switching | NOT MEASURED |
| FPS — portrait scroll | NOT MEASURED |
| FPS — landscape layout | NOT MEASURED |
| Memory usage | NOT MEASURED |
| Startup time | NOT MEASURED |
| Frame drops | NOT MEASURED |

## Why not measured
CI builds + launches + screenshots only; no Instruments / frame harness attached.
No values fabricated.

## Source-level performance protections
- Shared Canvas + TimelineView core/orbit/waveform (no SceneKit/RealityKit).
- Fixed particle (15), ring (4), waveform (40) counts.
- Reduce-motion disables pulse/wobble.
- AdaptiveRootView reuses shared components (no duplicated heavy views).
