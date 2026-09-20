"""Project Health Monitor regression checks."""
import os, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PASS = FAIL = 0

def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

main = open(os.path.join(ROOT, 'phase3', 'backend', 'main.py'), encoding='utf-8').read()
home = open(os.path.join(ROOT, 'JARVIS', 'Workspace', 'HomeEntryView.swift'), encoding='utf-8').read()
models = open(os.path.join(ROOT, 'JARVIS', 'Workspace', 'WorkspaceModels.swift'), encoding='utf-8').read()
pbx = open(os.path.join(ROOT, 'JARVIS.xcodeproj', 'project.pbxproj'), encoding='utf-8').read()

check("authenticated project health endpoint exists",
      '@app.get("/project/health")' in main and
      'Depends(get_user_id)' in main and
      'Depends(get_workspace)' in main)

check("health does not fabricate CI/build/test evidence",
      'JARVIS_BUILD_SHA' in main and
      '"ci_status": os.getenv("JARVIS_CI_STATUS", "unknown")' in main and
      '"tests_status": os.getenv("JARVIS_TESTS_STATUS", "unknown")' in main)

check("health reports real runtime blockers and approvals",
      'approval_store.list_pending(workspace_id)' in main and
      'kill_switch.engaged()' in main and
      '"tasks_failed": failed' in main and
      '"owner_actions": pending_approvals' in main)

check("health model is compiled through existing shared workspace source",
      'struct ProjectHealth: Codable' in models and
      'let currentMilestone: String?' in models and
      'let ownerActions: Int?' in models and
      'WorkspaceModels.swift' in pbx)

check("health model does not rely on an unregistered standalone source",
      'ProjectHealth.swift' not in pbx)

check("home loads project health endpoint",
      'api.getObject("project/health")' in home and
      '@Published var projectHealth: ProjectHealth?' in home)

check("home displays project health card",
      'صحة جارفس' in home and
      'health.blockers' in home and
      'health.ownerActions' in home and
      'health.currentMilestone' in home and
      'health.nextMilestone' in home)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
