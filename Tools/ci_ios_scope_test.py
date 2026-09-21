"""Regression guard for focused primary iOS CI validation.

Primary CI intentionally validates iPhone build/screenshots + real-contract flow.
iPad visual validation is deferred to a separate later pass so it cannot block
the current device-validation milestone.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/ios-build.yml").read_text(encoding="utf-8")

checks = [
    ("iOS build remains required", "Build iOS app" in WORKFLOW),
    ("iPhone screenshots remain required", "Boot iPhone + P5 screenshots" in WORKFLOW),
    ("real-contract screenshots remain required", "Real-contract screenshots" in WORKFLOW),
    ("iPad screenshot step is deferred", "Boot iPad (extra) + screenshots" not in WORKFLOW),
    ("iPad simulator is absent from primary workflow", "iPad Pro (11-inch) (4th generation)" not in WORKFLOW),
]

failed = []
for name, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + name)
    if not ok:
        failed.append(name)

print(f"\nprimary iOS CI scope: {len(checks)-len(failed)}/{len(checks)} checks passed")
sys.exit(1 if failed else 0)
