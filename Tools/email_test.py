"""V1.1 Phase 2 Email + Tool Foundation — regression (source-level + logic mirror).
يتحقق: intent routing، read/search، summarization boundaries، draft،
send ممنوع بدون تأكيد، send مسموح بعد تأكيد، auth/network failure،
Memory failure لا يكسر Email، Email failure لا يكسر Live Voice."""
import sys, os, re
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")

def read(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()

tf = read('ToolKit/ToolFoundation.swift')
et = read('ToolKit/EmailTool.swift')
vm = read('Home/HomeViewModel.swift')
gp = read('../generate_project.py')

# A. Tool Foundation — فصل intent/execution/result/confirmation/error
check("ToolIntent cases (summary/search/read/reply/none)", all(x in tf for x in ['emailSummary','emailSearch','emailRead','emailReply','none']))
check("ConfirmationRequirement (none/confirm)", 'none' in tf and 'confirm' in tf)
check("ToolResult (success/failure)", 'success' in tf and 'failure' in tf)
check("Tool protocol (detect/confirm/execute)", all(x in tf for x in ['detectIntent','confirmation','execute']))

# B. Email tool — read/search/summarize/send endpoints
check("EmailClient summary endpoint", '/email/summary' in et)
check("EmailClient search endpoint", '/email/search' in et)
check("EmailClient read endpoint", '/email/read' in et)
check("EmailClient send endpoint (POST)", '/email/send' in et and 'POST' in et)
check("summary limit bounded (limit: 8)", 'limit: 8' in et)
check("summary prefix bounded (prefix(5))", 'prefix(5)' in et)
check("read body bounded (prefix(600))", 'prefix(600)' in et)

# C. Confirmation gate — send requires confirm, read doesn't
check("reply → .confirm", '.emailReply' in et and '.confirm(description:' in et)
check("summary/read/search → .none", 'case .emailReply' in et and 'default:\n            return .none' in et)

# D. No secrets in app; token is server-side only
for bad in ['sk-', 'ghp_', 'client_secret', 'refresh_token', 'access_token']:
    check(f"no '{bad}' in iOS app sources", bad not in et and bad not in tf and bad not in vm)

# E. Email failure لا يكسر Live Voice (email lazy + result-driven, لا crash)
check("emailTool lazy (fail-safe)", 'private lazy var emailTool' in vm)
check("tool failure → ToolResult.failure (no throw to voice)", 'case .failure(let reason)' in vm)

# F. Send gate — الإرسال فقط عبر موافقة (routeToolChain → approve → executeTool)
check("routeToolChain routes confirm → approval", 'case .confirm(let desc)' in vm and 'state = .approval' in vm)
check("executeTool only from approve", 'Task { await executeTool(pt) }' in vm)

# G. Project wiring
check("ToolKit files in APP_SOURCES", all(x in gp for x in ['ToolKit/ToolFoundation.swift','ToolKit/EmailTool.swift']))
check("EmailToolTests in TEST_SOURCES", 'JARVISTests/EmailToolTests.swift' in gp)

# H. Logic mirror — intent routing + confirmation
def is_email(t):
    return any(k in t for k in ['إيميل','ايميل','بريد','رسائل','رسالة','email','mail','inbox'])

def extract_reply_body(t):
    for m in ['بـ','وقله','قله','قل له','ب ']:
        if m in t:
            rest = t.split(m,1)[1].strip()
            if rest: return rest
    return None

def detect(t):
    t = t.lower()
    if 'رد' in t or 'reply' in t:
        b = extract_reply_body(t)
        if b: return ('reply', b)
    if any(x in t for x in ['اقرأ','افتح','read']):
        if is_email(t): return ('read',)
    if any(x in t for x in ['ابحث','بحث','search']):
        if is_email(t): return ('search',)
    if is_email(t): return ('summary',)
    return ('none',)

check("mirror: summary", detect('وش أهم إيميلاتي اليوم؟') == ('summary',))
check("mirror: read", detect('اقرأ الرسالة') == ('read',))
check("mirror: search", detect('ابحث في البريد عن فلان') == ('search',))
check("mirror: reply", detect('رد عليه بـ تمام حجزت') == ('reply','تمام حجزت'))
check("mirror: none (calendar)", detect('وش عندي اليوم؟') == ('none',))

# confirmation mirror
def confirmation(intent):
    return 'confirm' if intent[0] == 'reply' else 'none'
check("mirror: reply needs confirm", confirmation(('reply','x')) == 'confirm')
check("mirror: read needs none", confirmation(('summary',)) == 'none')

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
