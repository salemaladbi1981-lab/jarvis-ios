"""Chat error-handling regression: status-aware errors, workspace header, timeout, retry dedup."""
import os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0

def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

vm = open(os.path.join(ROOT, 'Workspace/ChatViewModel.swift'), encoding='utf-8').read()

check("chat sends workspace header", 'X-Jarvis-Workspace' in vm and 'api.workspace' in vm)
check("chat has explicit request timeout", 'req.timeoutInterval = 60' in vm)
check("HTTP response status checked before stream", 'response as? HTTPURLResponse' in vm and '!(200..<300).contains' in vm)
check("401 has session-expired message", 'case 401:' in vm and 'انتهت جلسة جارفس' in vm)
check("403 has permission message", 'case 403:' in vm and 'صلاحية' in vm)
check("5xx has server message", 'case 500...599:' in vm and 'الخادم يواجه مشكلة مؤقتة' in vm)
check("offline/network loss classified", '.notConnectedToInternet' in vm and '.networkConnectionLost' in vm)
check("timeout classified", '.timedOut' in vm)
check("host/DNS failures classified", '.cannotConnectToHost' in vm and '.dnsLookupFailed' in vm)
check("send re-entry blocked", 'guard !trimmed.isEmpty, !isSending else { return }' in vm)
check("retry does not append duplicate user message", 'performSend(last, appendUserMessage: false)' in vm)
check("normal send appends user message", 'performSend(text, appendUserMessage: true)' in vm)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
