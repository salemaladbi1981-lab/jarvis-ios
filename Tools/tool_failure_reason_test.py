"""Tool-failure reason regression.
Device+server evidence: telegram_search and jarvis_agent_lookup both returned ok=False
on hermes-new, JARVIS said "ما قدر أوصل", and no log on either side carried the reason —
_trace recorded only ok=False and a duration. The proxy must record the returned error
code (code only: never the query, the message text or any credential)."""
import os, re, sys
BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'phase3', 'backend')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

rt = open(os.path.join(BACKEND, 'realtime.py'), encoding='utf-8').read()
m = re.search(r'\n( *)reason = .*\n\s*_trace\("tool", f"end \{name\} ok=\{output\.get\(.ok.\)\}\{reason\}[^\n]*\n', rt)
check("the end-of-tool trace carries a reason slot", bool(m))
check("the reason comes from the tool's own error field", "output.get('error')" in rt or 'output.get("error")' in rt)
check("a successful tool logs no reason", 'if output.get("ok") else' in rt)
check("an unspecified failure still says so", "'unspecified'" in rt or '"unspecified"' in rt)
check("the duration is still logged", 'in {int((time.monotonic()-t0)*1000)}ms' in rt)
check("only the code is logged, never the payload",
      'output.get("result")' not in rt.split('reason =')[-1].split('\n')[0]
      and 'args' not in rt.split('reason =')[-1].split('\n')[0])
check("the raised-exception trace is still there", '{name} raised {type(e).__name__}' in rt)


def trace_line(output):
    """Mirror of the proxy's formatting."""
    reason = "" if output.get("ok") else f" error={output.get('error') or 'unspecified'}"
    return f"end tool ok={output.get('ok')}{reason} in 5ms"

check("failure with a code is explicit",
      trace_line({"ok": False, "error": "missing_query"}) == "end tool ok=False error=missing_query in 5ms")
check("failure without a code is labelled",
      trace_line({"ok": False}) == "end tool ok=False error=unspecified in 5ms")
check("success stays quiet", trace_line({"ok": True}) == "end tool ok=True in 5ms")

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
