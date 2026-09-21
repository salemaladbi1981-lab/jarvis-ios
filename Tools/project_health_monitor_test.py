"""Project Health Monitor regression checks."""
import os, subprocess, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PASS = FAIL = 0

def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

main = open(os.path.join(ROOT, 'phase3', 'backend', 'main.py'), encoding='utf-8').read()
health_snapshot = open(os.path.join(ROOT, 'phase3', 'backend', 'project_health.py'), encoding='utf-8').read()
config = open(os.path.join(ROOT, 'phase3', 'backend', 'config.py'), encoding='utf-8').read()
home = open(os.path.join(ROOT, 'JARVIS', 'Workspace', 'HomeEntryView.swift'), encoding='utf-8').read()
models = open(os.path.join(ROOT, 'JARVIS', 'Workspace', 'WorkspaceModels.swift'), encoding='utf-8').read()
pbx = open(os.path.join(ROOT, 'JARVIS.xcodeproj', 'project.pbxproj'), encoding='utf-8').read()

check("authenticated project health endpoint exists",
      '@app.get("/project/health")' in main and
      'Depends(get_user_id)' in main and
      'Depends(get_workspace)' in main)

check("health does not fabricate CI/build/test evidence",
      'project_health_mod.build_project_health(' in main and
      '"build_sha": build_sha' in health_snapshot and
      '"ci_status": ci["status"]' in health_snapshot and
      '"tests_status": ci["tests_status"]' in health_snapshot and
      '_text(env, "JARVIS_CURRENT_MILESTONE", "unknown")' in health_snapshot)

check("health reports real runtime blockers and approvals",
      'approval_store.list_pending(workspace_id)' in main and
      'kill_switch.engaged()' in main and
      '"task_failure"' in health_snapshot and
      '"ci_job"' in health_snapshot and
      '"owner_actions": len(owner_action_items)' in health_snapshot and
      '"blocker_items": blocker_items' in health_snapshot)

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

check("project health failure is isolated from workspace content",
      'let (c, t, d, h) = try await' not in home and
      '@Published var projectHealthError: String?' in home and
      'conversations = try await convs' in home and
      'let loadedTasks = try await tasks' in home and
      'deliveries = try await dels' in home and
      'projectHealth = try await health' in home)

check("project health has an independent retry path",
      'func refreshProjectHealth() async' in home and
      'Task { await vm.refreshProjectHealth() }' in home and
      'صحة جارفس غير متاحة' in home and
      'إعادة فحص الصحة' in home)

health_keys = ('JARVIS_CURRENT_PHASE', 'JARVIS_CURRENT_MILESTONE', 'JARVIS_NEXT_MILESTONE')
backend_dir = os.path.join(ROOT, 'phase3', 'backend')
probe = (
    'import os,sys; '
    f'sys.path.insert(0, {backend_dir!r}); '
    'import config; '
    'print("|".join(os.environ[k] for k in '
    + repr(health_keys) + '))'
)
clean_env = os.environ.copy()
for key in health_keys:
    clean_env.pop(key, None)
try:
    defaults = subprocess.check_output([sys.executable, '-c', probe], env=clean_env, text=True).strip()
except Exception:
    defaults = '<probe-failed>'

check("missing milestone metadata fails closed to unknown",
      'os.environ.setdefault(_health_key, "unknown")' in config and
      defaults == 'unknown|unknown|unknown')

override_env = clean_env.copy()
override_env.update({
    'JARVIS_CURRENT_PHASE': '4',
    'JARVIS_CURRENT_MILESTONE': 'Gold cinematic UI migration',
    'JARVIS_NEXT_MILESTONE': 'Meeting foundation',
})
try:
    explicit = subprocess.check_output([sys.executable, '-c', probe], env=override_env, text=True).strip()
except Exception:
    explicit = '<probe-failed>'

check("explicit deployment milestone metadata remains authoritative",
      explicit == '4|Gold cinematic UI migration|Meeting foundation')

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
