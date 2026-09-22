"""Regression: Project Health home card must surface actionable detail, not counts only."""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
home_path = os.path.join(ROOT, 'JARVIS', 'Workspace', 'HomeEntryView.swift')
home = open(home_path, encoding='utf-8').read()

PASS = FAIL = 0


def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


check(
    "health card renders real blocker items",
    'if let blockers = health.blockerItems, !blockers.isEmpty' in home
    and 'ForEach(blockers.prefix(3))' in home
    and 'projectHealthBlockerText(blocker)' in home
    and 'المعطلات الفعلية' in home,
)

check(
    "health card renders real owner action items",
    'if let actions = health.ownerActionItems, !actions.isEmpty' in home
    and 'ForEach(actions.prefix(3))' in home
    and 'projectHealthOwnerActionText(action)' in home
    and 'يتطلب تدخلك' in home,
)

check(
    "actionable lists stay bounded for a stable home screen",
    'ForEach(blockers.prefix(3))' in home
    and 'blockers.count - 3' in home
    and 'ForEach(actions.prefix(3))' in home
    and 'actions.count - 3' in home,
)

check(
    "blocker details distinguish CI, task, metadata, and kill-switch evidence",
    'case "task_failure"' in home
    and 'case "ci_job"' in home
    and 'case "ci_metadata"' in home
    and 'case "ci_evidence"' in home
    and 'case "kill_switch"' in home
    and 'case "task_evidence"' in home,
)

check(
    "owner action text uses only the sanitized model fields",
    'item.action' in home
    and 'item.agent' in home
    and 'item.taskId' in home
    and 'approvalId' not in home[home.find('private func projectHealthOwnerActionText'):home.find('private func projectHealthUnavailableCard')],
)

check(
    "Project Health detail rendering does not turn backend run URLs into direct controls",
    'blocker.runUrl' not in home
    and 'health.ciRunUrl' not in home,
)

print(f"\nproject health actionable UI: {PASS}/{PASS + FAIL} checks passed")
sys.exit(1 if FAIL else 0)
