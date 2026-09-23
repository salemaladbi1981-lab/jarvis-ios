"""Regression: CI handoff cannot inject owner actions without reviewed provenance."""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "phase3" / "backend"
sys.path.insert(0, str(BACKEND))

from project_health_metadata import load_health_metadata


def load(lines, explicit=None):
    env = dict(explicit or {})
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "project-health.env"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        accepted = load_health_metadata(path, env)
    return accepted, env


ACTION = 'JARVIS_OWNER_ACTIONS_JSON=[{"type":"production_handoff","action":"Connect production host"}]'

accepted, env = load([ACTION])
assert not accepted
assert "JARVIS_OWNER_ACTIONS_JSON" not in env

accepted, env = load([
    ACTION,
    "JARVIS_OWNER_ACTIONS_SOURCE=unknown",
])
assert not accepted
assert "JARVIS_OWNER_ACTIONS_JSON" not in env

accepted, env = load([
    ACTION,
    "JARVIS_OWNER_ACTIONS_SOURCE=version_controlled_plan",
])
assert accepted
assert env["JARVIS_OWNER_ACTIONS_SOURCE"] == "version_controlled_plan"
assert "Connect production host" in env["JARVIS_OWNER_ACTIONS_JSON"]

accepted, env = load(
    [
        ACTION,
        "JARVIS_OWNER_ACTIONS_SOURCE=version_controlled_plan",
    ],
    explicit={"JARVIS_OWNER_ACTIONS_SOURCE": "unknown"},
)
assert not accepted
assert env["JARVIS_OWNER_ACTIONS_SOURCE"] == "unknown"
assert "JARVIS_OWNER_ACTIONS_JSON" not in env

# CI-only metadata remains usable; provenance is required only when the artifact
# contributes owner-facing actions.
accepted, env = load([
    "JARVIS_CI_STATUS=success",
    "JARVIS_CI_RUN_ID=35850821291",
    "JARVIS_CI_RUN_NUMBER=421",
])
assert accepted
assert env["JARVIS_CI_STATUS"] == "success"

print("project health owner-action provenance handoff: PASS")
