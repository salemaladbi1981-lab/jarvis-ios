#!/usr/bin/env python3
"""P5 real-contract screenshots: backend حقيقي + seed عبر الدوال الفعلية + فتح التطبيق عليه."""
import subprocess, os, json, time, sys, glob

def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r

def backend_env(tmp):
    # كل مسارات الـbackend إلى RUNNER_TEMP (لا وصول لـ/opt/data)
    os.environ['JARVIS_STORAGE_ROOT'] = os.path.join(tmp, 'jarvis-storage')
    os.environ['JARVIS_SESSIONS'] = os.path.join(tmp, 'jarvis-sessions.json')
    os.environ['JARVIS_APPROVAL_PATH'] = os.path.join(tmp, 'jarvis-approvals.json')
    os.environ['JARVIS_AUDIT_PATH'] = os.path.join(tmp, 'jarvis-audit.jsonl')
    os.environ['JARVIS_AGENT_AUDIT'] = os.path.join(tmp, 'jarvis-agent-audit.jsonl')
    os.environ['JARVIS_AGENT_STATE'] = os.path.join(tmp, 'jarvis-agent-state.json')
    os.environ['JARVIS_ENROLL'] = os.path.join(tmp, 'jarvis-enroll.json')
    os.environ['JARVIS_KILL_SWITCH'] = os.path.join(tmp, 'jarvis-kill-switch.json')
    os.environ['JARVIS_MEMORY_DIR'] = os.path.join(tmp, 'memories')
    os.environ['JARVIS_MEMORY_ROOT'] = os.path.join(tmp, 'memories')
    os.environ['JARVIS_BOOTSTRAP_KEY'] = 'ci-bootstrap-key'
    os.environ['CI_SEED_OUT'] = os.path.join(tmp, 'jarvis_ci_seed.json')

def main():
    root = os.getcwd()
    app = sys.argv[1] if len(sys.argv) > 1 else ''
    device = sys.argv[2] if len(sys.argv) > 2 else 'iPhone 15'
    tmp = os.environ.get('RUNNER_TEMP', '/tmp')
    if not app:
        found = glob.glob('build/**/JARVIS.app', recursive=True)
        app = found[0] if found else ''

    sh('python3 -m pip install --quiet --disable-pip-version-check fastapi uvicorn pydantic websockets')
    backend_env(tmp)

    os.chdir('phase3/backend')
    seed_r = sh('python3 ci_seed.py')
    print('seed stdout:', seed_r.stdout[-500:])
    if seed_r.stderr:
        print('seed stderr:', seed_r.stderr[-1500:])
    seed_path = os.environ['CI_SEED_OUT']
    seed = json.load(open(seed_path))
    token = seed['session_token']
    conv = seed['conversation_id']
    task = seed['task_id']
    delivery = seed['delivery_id']
    print(f'seeded token={token} conv={conv} task={task} delivery={delivery}')

    backend = subprocess.Popen(['python3', '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'],
                               stdout=open(os.path.join(tmp, 'backend.log'), 'w'), stderr=subprocess.STDOUT)
    ready = False
    for _ in range(30):
        r = sh('curl -s http://127.0.0.1:8000/health')
        if 'ok' in (r.stdout or '') or r.stdout.strip():
            ready = True
            break
        time.sleep(1)
    print('backend ready' if ready else 'backend NOT ready (continuing)')

    os.chdir(root)
    sh(f'xcrun simctl boot "{device}"')
    sh(f'xcrun simctl install "{device}" "{app}"')

    def shot(name, *args):
        sh(f'xcrun simctl terminate "{device}" com.salemai.jarvis')
        time.sleep(2)
        cmd = f'xcrun simctl launch "{device}" com.salemai.jarvis -- -baseURL http://127.0.0.1:8000 -sessionToken {token} {" ".join(args)}'
        sh(cmd)
        time.sleep(7)
        sh(f'xcrun simctl io "{device}" screenshot {name}.png')

    shot('real_home', '-tab', 'home')
    shot('real_chat', '-tab', 'chat')
    shot('real_inbox', '-tab', 'inbox')
    shot('real_tasks', '-tab', 'tasks')
    shot('real_deliveries', '-tab', 'deliveries')

    # deep links — cold-start via -deepLink launch arg (opens the specific item; bypasses iOS 17.4 "Open in JARVIS?" prompt)
    shot('deep_conversation', '-deepLink', f'jarvis://conversation/{conv}')
    shot('deep_task', '-deepLink', f'jarvis://task/{task}')
    shot('deep_delivery', '-deepLink', f'jarvis://delivery/{delivery}')

    # URL-scheme proof (warm openurl → system routes to JARVIS; prompt is iOS security, not app code)
    sh(f'xcrun simctl launch "{device}" com.salemai.jarvis -- -baseURL http://127.0.0.1:8000 -sessionToken {token} -tab home')
    time.sleep(6)
    sh(f'xcrun simctl openurl "{device}" "jarvis://conversation/{conv}"')
    time.sleep(3)
    sh(f'xcrun simctl io "{device}" screenshot deep_scheme.png')

    # notifications proof — permission flow + scheduling (deep-link in userInfo)
    shot('notif_permission', '-requestNotifications', '-showNotifications')
    shot('notif_scheduled', '-scheduleNotification', f'jarvis://delivery/{delivery}', '-showNotifications')

    print('SCREENSHOTS:')
    for p in sorted(glob.glob('*.png')):
        print(' ', p)
    backend.terminate()

if __name__ == '__main__':
    main()
