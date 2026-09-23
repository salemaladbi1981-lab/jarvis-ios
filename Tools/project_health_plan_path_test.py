#!/usr/bin/env python3
"""Regression: default Project Health plan path must match repository case on Linux CI."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "Tools" / "project_health_ci_metadata.py"
spec = importlib.util.spec_from_file_location("project_health_ci_metadata", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

expected = ROOT / "Docs" / "PROJECT-HEALTH-PLAN.json"
assert module.DEFAULT_PLAN_PATH == expected, (module.DEFAULT_PLAN_PATH, expected)
assert expected.is_file(), expected

# Exercise the real default path rather than a test-injected plan path. This is
# the path used by the ubuntu-latest Project Health metadata job.
env = {
    "GITHUB_SHA": "0123456789abcdef0123456789abcdef01234567",
    "GITHUB_RUN_ID": "123456789",
    "GITHUB_RUN_NUMBER": "424",
    "GITHUB_REF_NAME": "chatgpt-overnight-2",
    "GITHUB_REPOSITORY": "salemaladbi1981-lab/jarvis-ios",
    "GITHUB_SERVER_URL": "https://github.com",
    "JARVIS_BACKEND_TEST_RESULT": "success",
    "JARVIS_IOS_RESULT": "success",
    "JARVIS_MAC_RESULT": "success",
    "JARVIS_IOS_BUILD_RESULT": "success",
    "JARVIS_MAC_BUILD_RESULT": "success",
    "JARVIS_MAC_TEST_RESULT": "success",
}
metadata = module.build_metadata(env=env, generated_at="2026-09-23T12:00:00Z")
assert metadata["phase"] == "project-health-production-handoff", metadata
assert metadata["current_milestone"].startswith("Project Health production handoff"), metadata
assert metadata["next_milestone"].startswith("Release readiness"), metadata
assert metadata["evidence"]["milestones"] == "version_controlled_plan", metadata
assert metadata["owner_actions"], metadata
assert metadata["evidence"]["owner_actions"] == "version_controlled_plan", metadata
print("project health default plan path: PASS")
