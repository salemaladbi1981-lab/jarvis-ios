#!/bin/bash
set -euo pipefail
# Use an available runtime instead of assuming a particular iPhone model.
DEVICE_ID=$(xcrun simctl list devices available -j | python3 -c 'import json,sys; devices=json.load(sys.stdin)["devices"]; print(next(d["udid"] for group in devices.values() for d in group if d["name"].startswith("iPhone")))')
xcodebuild test -project JARVIS.xcodeproj -scheme JARVIS \
  -destination "platform=iOS Simulator,id=$DEVICE_ID" \
  -derivedDataPath build/ios-tests \
  CODE_SIGNING_ALLOWED=NO ONLY_ACTIVE_ARCH=YES
