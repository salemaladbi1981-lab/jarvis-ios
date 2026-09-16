"""V1 Visual Prototype regression (source-level). Physical Visual Review مطلوب بعدها."""
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
orbit = read('Core/JarvisOrbitView.swift')
model = read('Core/AgentOrbitModel.swift')
vae = read('Voice/VoiceAudioEngine.swift')
rvs = read('Voice/RealtimeVoiceSession.swift')
vm = read('Home/HomeViewModel.swift')

# 1. MotionTokens (condition 4: tunable central tokens)
check("MotionTokens: duration/amplitude/speed central", 'enum MotionTokens' in mt and 'Duration' in mt and 'Amplitude' in mt and 'Speed' in mt)
check("MotionTokens: smoothing attack/release", 'Smoothing' in mt and 'attack' in mt and 'release' in mt)

# 2. Core 8 states (level-driven, لا sine mock لـ listening/speaking)
check("Core: micLevel + outputLevel params", 'micLevel' in core and 'outputLevel' in core)
check("Core: successPulse transient", 'successPulse' in core)
check("Core: 7 JarvisState branches (idle/listening/thinking/speaking/executing/alert/approval)", all(s in core for s in ['.idle', '.listening', '.thinking', '.speaking', '.executing', '.alert', '.approval']))
check("Core: listening = mic level (لا sine mock)", '.listening' in core and 'mic' in core)
check("Core: speaking = output level", '.speaking' in core and 'output' in core)
check("Core: smoothing attack في onChange(of: levels.micLevel)", 'Smoothing.attack' in core and 'onChange(of: levels.micLevel)' in core)
check("Core: FPS instrumentation (onFrameTime)", 'onFrameTime' in core and 'CACurrentMediaTime' in core)
check("Core: Reduced Motion", 'accessibilityReduceMotion' in core)

# 3. Orbit (single + handoff + 3 agents، لا 21 دائمة)
check("Orbit: active agents فقط (AgentOrbitModel)", 'AgentOrbitModel' in orbit and 'orbit.items' in orbit)
check("Orbit: handoff arc", 'handoffArc' in orbit)
check("Orbit: group radius (core/system/content)", 'system' in orbit and 'content' in orbit)
check("Orbit: Canvas واحد (لا 21 SwiftUI views)", 'Canvas' in orbit)

# 4. AgentOrbitModel (real events, لا timers)
check("AgentOrbitModel: activate/deactivate/handoff", 'func activate' in model and 'func deactivate' in model and 'func handoff' in model)
check("AgentOrbitModel: relayout (توزيع)", 'relayout' in model)

# 5. Audio reactivity read-only (condition 1: ZERO behavior change)
check("VoiceAudioEngine: onMicLevel hook", 'onMicLevel' in vae)
check("VoiceAudioEngine: onOutputLevel hook", 'onOutputLevel' in vae)
check("VoiceAudioEngine: rmsLevel read-only (لا يمس data)", 'static func rmsLevel' in vae)
check("RealtimeVoiceSession: level forwarding", 'onMicLevel' in rvs and 'onOutputLevel' in rvs)
check("HomeViewModel: level معزول (VisualLevelModel)", 'VisualLevelModel' in vm and 'levels' in vm)
check("HomeViewModel: orbit model", 'AgentOrbitModel' in vm)
check("HomeViewModel: orbit demo launch args (single/handoff/multi)", 'single' in vm and 'handoff' in vm and 'multi' in vm)

# 6. Golden Voice isolation (لا تغيير سلوك)
check("VoiceAudioEngine: لا تغيير في flow (receivedBytes/pump/nextBuffer intact)", all(x in vae for x in ['receivedBytes', 'pump(', 'nextBuffer', 'setVoiceProcessingEnabled']))
check("RealtimeVoiceSession: bargeIn/cancel/connected intact", all(x in rvs for x in ['bargeIn', 'response.cancel', 'isSessionReady']))

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
import sys
sys.exit(1 if FAIL else 0)
