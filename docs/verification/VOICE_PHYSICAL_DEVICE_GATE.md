# JARVIS Voice Physical Device Gate

A capability is not REAL until it passes the required real-device checks.

## Required matrix
- iPhone unlocked / locked.
- Siri invocation.
- Shortcut invocation.
- Action Button invocation if enabled.
- No headset.
- AirPods.
- Shokz.
- Microphone permission granted / denied.
- Network available / unavailable.
- Manual interruption during JARVIS speech.
- Route switch while active.
- Sensitive action requiring approval/authentication.

## Result states
IMPLEMENTED -> TESTED -> PHYSICAL_DEVICE_VERIFIED

Never promote a lock-screen, headset, Siri, or background voice capability directly from CI/simulator to verified.

## Pass criteria
- Correct audio input/output route.
- No duplicate response.
- No stuck listening/speaking state.
- No false claim of background availability.
- Sensitive actions remain gated.
- Recovery path is visible and understandable when iOS blocks the requested behavior.
