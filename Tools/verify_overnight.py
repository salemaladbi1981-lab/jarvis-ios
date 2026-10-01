#!/usr/bin/env python3
"""Portable offline regression gate; only temporary storage and test providers.

Run with the backend test environment's Python. Live/provider-dependent test
scripts are intentionally excluded and must be verified separately on deployment.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BACKEND_TESTS = '''tests_realtime_tools tests_multi_email tests_microsoft tests_telegram tests_youtube
 tests_derivatives tests_owner_negative tests_workspace_http tests_security tests_chat tests_chat_retry
 tests_chat_http tests_inbox tests_conversation tests_worker tests_tg_handoff tests_auth tests_workspace
 tests_memory_isolation tests_memory_production tests_production_providers tests_agent_activation
 tests_tool_guard tests_approval_audit tests_config_language tests_enrollment tests_capabilities
 tests_phaseD tests_upload_auth tests_voice_stability tests_instagram tests_maps'''.split()


def main():
    output = ROOT / 'build/overnight'
    output.mkdir(parents=True, exist_ok=True)
    results = []
    with tempfile.TemporaryDirectory(prefix='jarvis-verification-') as tmp:
        env = {k: v for k, v in os.environ.items() if not k.startswith('JARVIS_') and not any(s in k for s in ('API_KEY', 'API_SERVER_KEY', 'TOKEN', 'SECRET'))}
        for key, name in {'STORAGE_ROOT': 'storage', 'SESSIONS': 'sessions.json', 'APPROVAL_PATH': 'approvals.json',
                          'AUDIT_PATH': 'audit.jsonl', 'AGENT_AUDIT': 'agent-audit.jsonl', 'AGENT_STATE': 'agents.json',
                          'ENROLL': 'enroll.json', 'KILL_SWITCH': 'kill.json', 'MEMORY_DIR': 'memories',
                          'MEMORY_ROOT': 'memories', 'USER_MEMORY': 'USER.md', 'STATE_DB': 'state.db'}.items():
            env['JARVIS_' + key] = str(Path(tmp) / name)
        env['PYTHONPYCACHEPREFIX'] = str(Path(tmp) / 'pycache')
        scripts = [ROOT / 'phase3/backend' / (name + '.py') for name in BACKEND_TESTS]
        scripts += sorted((ROOT / 'Tools').glob('*_test.py'))
        for script in scripts:
            try:
                result = subprocess.run([sys.executable, str(script)], cwd=script.parent, env=env,
                                        capture_output=True, text=True, timeout=180)
                code, log = result.returncode, result.stdout + result.stderr
            except subprocess.TimeoutExpired:
                code, log = 124, 'Test exceeded 180 seconds.'
            (output / (script.stem + '.log')).write_text(log)
            results.append({'script': str(script.relative_to(ROOT)), 'passed': code == 0, 'exit_code': code})
            print(('PASS ' if code == 0 else 'FAIL ') + str(script.relative_to(ROOT)), flush=True)
    (output / 'portable-results.json').write_text(json.dumps(results, indent=2) + '\n')
    print(f'{sum(r["passed"] for r in results)}/{len(results)} scripts passed')
    return 0 if all(r['passed'] for r in results) else 1

if __name__ == '__main__': sys.exit(main())
