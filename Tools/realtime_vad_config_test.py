"""Realtime session.update VAD + transcription regression.
Device evidence (console-session5): with semantic_vad the server echoed
create_response:true in session.updated although the backend sent false, so it created
a response after every audio commit and JARVIS spoke unprompted. server_vad honours
create_response:false — the client asks for a response only after the on-device tools
have had their turn. Transcription must pin Arabic; language:null let whisper return
English noise for Arabic speech."""
import ast, os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'phase3', 'backend')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

src = open(os.path.join(ROOT, 'realtime.py'), encoding='utf-8').read()

def literal(key):
    """The dict literal assigned to inp["<key>"], parsed."""
    m = re.search(r'inp\[\s*"' + key + r'"\s*\]\s*=\s*(\{.*?\})\s*$', src, re.M | re.S)
    if not m: return None
    try: return ast.literal_eval(m.group(1))
    except (ValueError, SyntaxError): return None

td = literal('turn_detection')
tr = literal('transcription')

check("turn_detection is assigned a readable dict literal", isinstance(td, dict))
check("turn_detection type is server_vad (never semantic_vad)",
      isinstance(td, dict) and td.get('type') == 'server_vad')
check("create_response is False — the server must not answer on its own",
      isinstance(td, dict) and td.get('create_response') is False)
check("interrupt_response is False — nearby speech must not cancel playback",
      isinstance(td, dict) and td.get('interrupt_response') is False)
check("server_vad tuning is explicit (threshold + padding + silence)",
      isinstance(td, dict) and td.get('threshold') == 0.6
      and td.get('prefix_padding_ms') == 300 and td.get('silence_duration_ms') == 500)

check("transcription is assigned a readable dict literal", isinstance(tr, dict))
check("transcription language is pinned to Arabic",
      isinstance(tr, dict) and tr.get('language') == 'ar')
check("transcription model is whisper-1", isinstance(tr, dict) and tr.get('model') == 'whisper-1')

# Comments may still explain why semantic_vad was dropped; code must not use it.
code = '\n'.join(l.split('#', 1)[0] for l in src.split('\n'))
check("no semantic_vad left in executable code", 'semantic_vad' not in code)
check("session.update still uses the audio.input shape",
      'setdefault("audio", {}).setdefault("input", {})' in code)
check("session.update is still sent", '{"type": "session.update", "session": session}' in src)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
