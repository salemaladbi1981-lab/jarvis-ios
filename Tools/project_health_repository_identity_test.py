"""Regression checks for Project Health GitHub repository identity plumbing."""
from pathlib import Path
import importlib.util
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "Tools" / "project_health_ci_metadata.py"
spec = importlib.util.spec_from_file_location("project_health_ci_metadata", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

env = {
    "GITHUB_SHA": "a" * 40,
    "GITHUB_RUN_ID": "123456",
    "GITHUB_RUN_NUMBER": "412",
    "GITHUB_REF_NAME": "chatgpt-overnight-2",
    "GITHUB_SERVER_URL": "https://github.com",
    "GITHUB_REPOSITORY": "salemaladbi1981-lab/jarvis-ios",
}
meta = module.build_metadata(env=env, generated_at="2026-09-23T03:00:00Z")
assert meta["ci_repository"] == "salemaladbi1981-lab/jarvis-ios"
assert meta["ci_run_url"] == "https://github.com/salemaladbi1981-lab/jarvis-ios/actions/runs/123456"
assert meta["evidence"]["run"] == "github_actions"

with tempfile.TemporaryDirectory() as td:
    out = Path(td) / "project-health.env"
    module._write_env(out, meta)
    text = out.read_text(encoding="utf-8")
    assert "JARVIS_CI_REPOSITORY=salemaladbi1981-lab/jarvis-ios\n" in text

bad = dict(env, GITHUB_REPOSITORY="not a repo")
bad_meta = module.build_metadata(env=bad, generated_at="2026-09-23T03:00:00Z")
assert bad_meta["ci_repository"] == ""
assert bad_meta["ci_run_url"] == ""
assert bad_meta["evidence"]["run"] == "unknown"
print("project health repository identity: 7/7 PASS")
