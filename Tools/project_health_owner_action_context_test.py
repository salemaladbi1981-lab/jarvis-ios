"""Project Health owner actions must stay bound to their reviewed milestone context."""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "Tools" / "project_health_ci_metadata.py"
PLAN = ROOT / "docs" / "PROJECT-HEALTH-PLAN.json"
PASS = FAIL = 0


def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


spec = importlib.util.spec_from_file_location("project_health_ci_metadata", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
plan = json.loads(PLAN.read_text(encoding="utf-8"))

base = {
    "GITHUB_SHA": "abc1234",
    "GITHUB_RUN_ID": "35603375966",
    "GITHUB_RUN_NUMBER": "277",
    "GITHUB_SERVER_URL": "https://github.com",
    "GITHUB_REPOSITORY": "salemaladbi1981-lab/jarvis-ios",
    "GITHUB_REF_NAME": "chatgpt-overnight-2",
    "JARVIS_BACKEND_TEST_RESULT": "success",
    "JARVIS_IOS_RESULT": "success",
    "JARVIS_MAC_RESULT": "success",
}

fallback = module.build_metadata(base, plan_path=PLAN, generated_at="2026-09-23T18:00:00Z")
check("reviewed plan actions remain attached to their exact milestone context",
      fallback["owner_actions"] == plan["owner_actions"] and
      fallback["evidence"]["owner_actions"] == "version_controlled_plan")

diverged_env = dict(base)
diverged_env.update({
    "JARVIS_CURRENT_PHASE": "siri-foundation",
    "JARVIS_CURRENT_MILESTONE": "Siri App Intents hardening",
    "JARVIS_NEXT_MILESTONE": "Mac Operator foundation",
})
diverged = module.build_metadata(diverged_env, plan_path=PLAN, generated_at="2026-09-23T18:00:00Z")
check("repository milestone overrides suppress stale plan owner actions",
      diverged["evidence"]["milestones"] == "github_repository_variables" and
      diverged["owner_actions"] == [] and
      diverged["evidence"]["owner_actions"] == "unknown")

partial_env = dict(base)
partial_env["JARVIS_CURRENT_MILESTONE"] = "Deployment-owned milestone"
partial = module.build_metadata(partial_env, plan_path=PLAN, generated_at="2026-09-23T18:00:00Z")
check("mixed milestone context cannot inherit a reviewed-plan owner action",
      partial["evidence"]["milestones"] == "mixed" and
      partial["owner_actions"] == [] and
      partial["evidence"]["owner_actions"] == "unknown")

matching_env = dict(base)
matching_env.update({
    "JARVIS_CURRENT_PHASE": plan["phase"],
    "JARVIS_CURRENT_MILESTONE": plan["current_milestone"],
    "JARVIS_NEXT_MILESTONE": plan["next_milestone"],
})
matching = module.build_metadata(matching_env, plan_path=PLAN, generated_at="2026-09-23T18:00:00Z")
check("matching repository labels preserve reviewed action provenance",
      matching["evidence"]["milestones"] == "github_repository_variables" and
      matching["owner_actions"] == plan["owner_actions"] and
      matching["evidence"]["owner_actions"] == "version_controlled_plan")

with tempfile.TemporaryDirectory() as temp_dir:
    env_path = Path(temp_dir) / "project-health.env"
    module._write_env(env_path, diverged)
    env_text = env_path.read_text(encoding="utf-8")
check("runtime handoff cannot carry a stale plan action after milestone divergence",
      "JARVIS_OWNER_ACTIONS_JSON=[]" in env_text and
      "JARVIS_OWNER_ACTIONS_SOURCE=unknown" in env_text)

with tempfile.TemporaryDirectory() as temp_dir:
    incomplete_plan = Path(temp_dir) / "plan.json"
    incomplete_plan.write_text(json.dumps({
        "schema_version": 4,
        "phase": plan["phase"],
        "current_milestone": plan["current_milestone"],
        "owner_actions": plan["owner_actions"],
    }), encoding="utf-8")
    incomplete = module.build_metadata(base, plan_path=incomplete_plan, generated_at="2026-09-23T18:00:00Z")
check("incomplete reviewed planning context cannot authorize owner actions",
      incomplete["owner_actions"] == [] and
      incomplete["evidence"]["owner_actions"] == "unknown")

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
