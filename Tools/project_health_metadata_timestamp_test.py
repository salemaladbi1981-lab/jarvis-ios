"""Regression checks for strict Project Health CI freshness timestamps."""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "phase3" / "backend"
sys.path.insert(0, str(BACKEND))

import project_health_metadata

PASS = FAIL = 0


def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


def load_with_timestamp(timestamp):
    with tempfile.TemporaryDirectory() as td:
        handoff = Path(td) / "project-health.env"
        handoff.write_text(
            "JARVIS_CI_STATUS=success\n"
            f"JARVIS_CI_METADATA_GENERATED_AT={timestamp}\n",
            encoding="utf-8",
        )
        env = {}
        loaded = project_health_metadata.load_health_metadata(handoff, env)
        return loaded, env


loaded, env = load_with_timestamp("2026-09-22T16:22:47Z")
check(
    "canonical UTC CI timestamp is accepted",
    loaded and env.get("JARVIS_CI_METADATA_GENERATED_AT") == "2026-09-22T16:22:47Z",
)

loaded, env = load_with_timestamp("2026-09-22T16:22:47.123456Z")
check(
    "producer-compatible fractional UTC timestamp is accepted",
    loaded and env.get("JARVIS_CI_METADATA_GENERATED_AT") == "2026-09-22T16:22:47.123456Z",
)

for name, timestamp in (
    ("shape-only garbage timestamp is rejected", "garbageTZ"),
    ("impossible calendar timestamp is rejected", "2026-99-22T16:22:47Z"),
    ("non-UTC offset timestamp is rejected", "2026-09-22T19:22:47+03:00"),
    ("space-separated timestamp is rejected", "2026-09-22 16:22:47Z"),
    ("timestamp without seconds is rejected", "2026-09-22T16:22Z"),
):
    loaded, env = load_with_timestamp(timestamp)
    check(
        name,
        loaded
        and "JARVIS_CI_METADATA_GENERATED_AT" not in env
        and env.get("JARVIS_CI_STATUS") == "success",
    )

check(
    "empty freshness timestamp remains representable as missing evidence",
    project_health_metadata._valid_generated_at("") is True,
)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
