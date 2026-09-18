"""Voice stability (iOS source-level) — barge-in truncate + item tracking + played duration."""
import os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1
def read(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()

session = read('Voice/RealtimeVoiceSession.swift')
engine = read('Voice/VoiceAudioEngine.swift')
parser = read('Voice/SessionEventParser.swift')

check("barge-in sends conversation.item.truncate", "conversation.item.truncate" in session)
check("truncate cuts only unplayed audio (audio.playedDurationMs)", "audio.playedDurationMs" in session)
check("tracks current output item id", "currentOutputItemID" in session)
check("tracks content_index", "currentContentIndex" in session)
check("handles response.output_item.done", "response.output_item.done" in session)
check("resets item on response.created", "currentOutputItemID = nil" in session)
check("VoiceAudioEngine exposes playedDurationMs", "playedDurationMs" in engine)
check("SessionEventParser exposes fieldInt", "fieldInt" in parser)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
import sys
sys.exit(0 if FAIL == 0 else 1)
