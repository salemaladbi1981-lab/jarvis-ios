# JARVIS — P2.2 iOS Build & Run Instructions

## What is included
An Xcode-ready project: `JARVIS.xcodeproj/` opens directly in Xcode.
No manual project reconstruction required.

## Environment
- macOS with Xcode 15+ (Swift 5.9+), iOS 17+ simulator/device.

## Build
1. Open `JARVIS.xcodeproj` in Xcode.
2. Select the `JARVIS` scheme, an iPhone simulator (e.g. iPhone 15).
3. Run (⌘R).

## Included automatically
- All Swift source files (target membership pre-configured).
- Bundled fonts (IBM Plex Sans Arabic 400/700, Cormorant Garamond 600).
- `AGENT-REGISTRY.json` + `DESIGN-TOKENS.json` as bundle resources.
- `Info.plist` with `UIAppFonts`, RTL, portrait, dark appearance.

## Demo interactions (P2.2 mock only)
- Swipe left/right on the hero → switch agent group (Core → System → Content).
- Tap Voice Input Bar → cycle the seven states.
- Tap Smart Home card → safe read (`read-temperature`, no approval).
- Tap Security card → sensitive action (`unlock-door`, approval card appears).

## Tests
- Unit tests (ApprovalPolicyEvaluator, HomeViewModel, AgentRegistry) run via
  Product → Test (⌘U) on macOS.
