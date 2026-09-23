#!/usr/bin/env python3
"""Regression: the default reviewed Project Health plan must resolve on case-sensitive CI."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "Tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "Tools"))

import project_health_ci_metadata as metadata  # noqa: E402


def main():
    expected = ROOT / "Docs" / "PROJECT-HEALTH-PLAN.json"
    assert metadata.DEFAULT_PLAN_PATH == expected, (
        f"default plan path casing drifted: {metadata.DEFAULT_PLAN_PATH!s}"
    )
    assert expected.is_file(), "reviewed Project Health plan is missing"

    plan = metadata._load_plan()
    assert plan.get("phase") == "project-health-production-handoff"
    assert plan.get("current_milestone")
    assert plan.get("next_milestone")
    actions = plan.get("owner_actions") or []
    assert actions, "default CI metadata lost reviewed owner actions"
    assert actions[0].get("type") == "production_handoff"
    print("project_health_plan_path_test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
