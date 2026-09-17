"""V1 Physical Review fixes regression (source-level) — 4 issues:
1) Core motion perceptual gain  2) UI touch/scroll لا يوقف الصوت
3) AVAudioSession interruption  4) UNAVAILABLE مخفي من Production UI."""
import os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1
def read(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()

mt = read('Core/MotionTokens.swift')
core = read('Core/JarvisCoreView.swift')
wave = read('Core/WaveformView.swift')
vm = read('Home/HomeViewModel.swift')
home = read('Home/HomeView.swift')
qc = read('Home/QuickCommand.swift')
vae = read('Voice/VoiceAudioEngine.swift')
mac = read('macOS/MacHomeView.swift')
ipad = read('iPad/iPadLandscapeView.swift')

# 1) Core motion — perceptual mapping (RMS صغير → مرئي)
check("MotionTokens: Level.gain perceptual", 'enum Level' in mt and 'gain' in mt and 'func perceptual' in mt)
check("Core: uses perceptual (micP/outP)", 'micP' in core and 'outP' in core and 'Level.perceptual' in core)
check("Core: coreScale يستخدم micP/outP", 'listening * micP' in core and 'speaking * outP' in core)
check("Waveform: perceptual level", 'Level.perceptual' in wave)

# 2) UI touch/scroll لا يوقف الصوت
check("HomeViewModel: stopListening مرة واحدة فقط (في toggleVoice)", vm.count('stopListening') == 1)
check("HomeViewModel: لا disconnect في UI handlers", 'disconnect(' not in vm)
check("HomeViewModel: interrupt فقط في routeToolChain (grounding للبريد) لا في UI handlers", vm.count('.interrupt(') == 1 and 'voiceSession.interrupt()' in vm)
check("HomeViewModel: لا flush في UI handlers", 'flush(' not in vm)
check("HomeView: VoiceInputBar خارج الـ ScrollView (في safeAreaInset)",
      home.index('VoiceInputBar') > home.index('.safeAreaInset(edge: .bottom)'))

# 3) AVAudioSession interruption/route handling
check("VoiceAudioEngine: interruption observer", 'interruptionNotification' in vae and 'handleInterruption' in vae)
check("VoiceAudioEngine: shouldResume policy", 'shouldResume' in vae)
check("VoiceAudioEngine: route change observer", 'routeChangeNotification' in vae)
check("VoiceAudioEngine: resume بعد interruption", 'resumeAfterInterruption' in vae and 'engine.isRunning' in vae)
check("VoiceAudioEngine: لا flush على interruption (نحفظ playback)", 'no flush' in vae or 'preserving playback' in vae)

# 4) UNAVAILABLE مخفي
check("QuickCommand: productionCases (verified only)", 'productionCases' in qc and 'capabilityStatus == .verified' in qc)
for name, f in [("HomeView", home), ("MacHomeView", mac), ("iPadLandscapeView", ipad)]:
    check(f"{name}: productionCases بدل allCases", 'QuickCommand.productionCases' in f and 'QuickCommand.allCases' not in f)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
import sys
sys.exit(1 if FAIL else 0)
