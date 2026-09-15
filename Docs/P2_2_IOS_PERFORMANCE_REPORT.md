# JARVIS — P2.2 iOS Performance Report

## Status: NOT MEASURED (blocked by environment)

This build was authored on a **Linux host with no Xcode / no iOS simulator**,
so it is impossible to honestly measure iOS runtime performance here.

Per the project's honesty principle, no FPS/memory/startup figures are
fabricated. The following measurements are **required on macOS/Xcode** and are
listed as pending, not as results:

| Metric | Target | Measured |
|---|---|---|
| Average FPS (idle) | 60 | NOT MEASURED |
| Average FPS (listening/thinking/speaking mock) | 60 | NOT MEASURED |
| Average FPS (group transition) | 60 | NOT MEASURED |
| Average FPS (scroll) | 60 | NOT MEASURED |
| Worst visible frame drop | none | NOT MEASURED |
| Memory | — | NOT MEASURED |
| Startup time | — | NOT MEASURED |
| Reduced-motion behavior | reduced | NOT MEASURED |

## Design choices made to protect performance (in code)
- Core/orbit/waveform use `TimelineView(.animation)` + `Canvas` (no SceneKit/RealityKit).
- Particle count fixed at 15; ring count fixed at 4; bar count fixed at 40.
- Reduced Motion: `@Environment(\.accessibilityReduceMotion)` disables pulse/wobble
  and freezes timeline-driven motion (see JarvisCoreView / WaveformView).
- Idle core pulse is a low-cost sin() scale, not a shader or video loop.

## How to complete this report
Run on macOS with Xcode Instruments (Core Animation / Time Profiler), record the
values above, and replace the "NOT MEASURED" cells.
