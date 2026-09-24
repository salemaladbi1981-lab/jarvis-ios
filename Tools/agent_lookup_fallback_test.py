"""Agent-lookup regression.
Server evidence (hermes-new, /tmp/jarvis8000-final.log): jarvis_agent_lookup ran twice
and returned ok=False both times, and on the device JARVIS said it had no details about
المدرب "من السجل الرسمي". Reproduced offline: the only failing path is an empty or
missing query. A roster question deserves the roster, not an error."""
import os, sys
BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'phase3', 'backend')
sys.path.insert(0, BACKEND)
import agent_tools

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

run = lambda args: agent_tools.execute_agent_tool("jarvis_agent_lookup", args)
registry_count = len(agent_tools._load_registry().get("agents", []))

check("the bundled registry still has its agents", registry_count >= 21)

for args, label in (({}, "no arguments"), ({"query": ""}, "empty query"),
                    ({"query": "   "}, "whitespace query"), ({"agent_id": "sys_coach"}, "wrong argument name")):
    r = run(args)
    check(f"{label} returns the roster, not an error",
          r.get("ok") is True and r.get("error") is None and r.get("count") == registry_count)
    check(f"{label} lists agents with id, name and role",
          bool(r["matches"]) and all(m.get("id") and m.get("name") and m.get("role") for m in r["matches"]))

check("the roster is bounded", len(run({})["matches"]) <= 25)

named = run({"query": "المدرب"})
check("an Arabic name still matches exactly one agent",
      named["ok"] and named["count"] == 1 and named["matches"][0]["id"] == "sys_coach")
check("an id still matches", run({"query": "sys_coach"})["ok"] and run({"query": "sys_coach"})["count"] >= 1)
# The matcher is token-based and pre-dates this change: a multi-word query can match on a
# common token ("an"), so only a single nonsense token is a zero-match case.
check("a nonsense query returns zero matches without failing",
      run({"query": "zzzzq"})["ok"] is True and run({"query": "zzzzq"})["count"] == 0)
check("a query-less call is never mistaken for a nonsense query",
      run({})["count"] == registry_count and run({"query": "zzzzq"})["count"] == 0)
check("an unknown tool still fails closed",
      agent_tools.execute_agent_tool("nope", {}) == {"ok": False, "error": "unknown_tool"})
check("jarvis_agent itself still requires its arguments",
      agent_tools.execute_agent_tool("jarvis_agent", {}).get("ok") is False)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
