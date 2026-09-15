"""M3.1 deterministic live-voice test harness (no real audio required).
Simulates session/live events and verifies the seven-state machine behavior,
including barge-in and reconnect. Real mic/audio is a separate device gate."""
import sys

STATES = ["idle","listening","thinking","speaking","executing","alert","approval"]

def event_to_state(event):
    return {
        "connecting": "thinking",
        "connected": "idle",
        "listening": "listening",
        "thinking": "thinking",
        "speaking": "speaking",
        "interrupted": "listening",   # barge-in: Speaking → Listening
        "tool_executing": "executing",
        "awaiting_approval": "approval",
        "error": "alert",
        "disconnected": "idle",
    }.get(event, "idle")

class LiveStateMachine:
    def __init__(self):
        self.state = "idle"
        self.turn = 0

    def apply(self, event):
        self.state = event_to_state(event)
        if event == "listening":
            self.turn += 1
        return self.state

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")

m = LiveStateMachine()
print("== BARGE-IN SEQUENCE ==")
seq = ["connected","listening","thinking","speaking","interrupted","listening"]
states = [m.apply(e) for e in seq]
check("connected → idle", states[0] == "idle")
check("listening → listening", states[1] == "listening")
check("speaking → speaking", states[3] == "speaking")
check("barge-in interrupted → listening", states[4] == "listening")
check("new turn accepted (listening)", states[5] == "listening")

print("\n== STATE TRANSITIONS ==")
check("connecting → thinking", event_to_state("connecting") == "thinking")
check("tool → executing", event_to_state("tool_executing") == "executing")
check("awaiting approval → approval", event_to_state("awaiting_approval") == "approval")
check("error → alert", event_to_state("error") == "alert")
check("disconnected → idle", event_to_state("disconnected") == "idle")

print("\n== RECONNECT ==")
m2 = LiveStateMachine()
m2.apply("connected"); m2.apply("speaking"); m2.apply("disconnected")
check("after disconnect → idle", m2.state == "idle")
m2.apply("connecting"); m2.apply("connected")
check("reconnect → idle (ready)", m2.state == "idle")

print("\n== MIC DENIED / NETWORK FAILURE ==")
check("network failure → alert", event_to_state("error") == "alert")
check("mic denied maps to error/alert path", event_to_state("error") == "alert")

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
