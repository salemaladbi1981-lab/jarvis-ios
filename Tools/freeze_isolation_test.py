"""UI freeze root cause + level isolation regression (source-level)."""
import os, re
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1
def read(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()

vm = read('Home/HomeViewModel.swift')
core = read('Core/JarvisCoreView.swift')
vlm = read('Core/VisualLevelModel.swift')
hero = read('Core/JarvisHeroView.swift')

# 1. Root cause: الـ @Published micLevel/outputLevel أُزيل من HomeViewModel (كان يسبب HomeView كامل re-render)
check("لا @Published micLevel في HomeViewModel (عزل)", '@Published var micLevel' not in vm)
check("لا @Published outputLevel في HomeViewModel", '@Published var outputLevel' not in vm)
check("VisualLevelModel معزول (lightweight)", 'let levels = VisualLevelModel()' in vm)

# 2. RMS hooks → levels (وليس self.micLevel)
check("RMS hook → levels.setMicLevel", 'levels.setMicLevel' in vm and 'levels.setOutputLevel' in vm)

# 3. JarvisCoreView يراقب الـ model فقط (وليس params)
check("JarvisCoreView @ObservedObject levels", '@ObservedObject var levels' in core)
check("onChange(of: levels.micLevel)", 'onChange(of: levels.micLevel)' in core)

# 4. JarvisHeroView يمرر levels (وليس micLevel/outputLevel params)
check("JarvisHeroView يمرر levels", 'levels: vm.levels' in hero)

# 5. instrumentation (peak + publish count)
check("VisualLevelModel publish count", 'micPublishCount' in vlm and 'outputPublishCount' in vlm)
check("VisualLevelModel peak tracking", 'micLevelPeak' in vlm and 'outputLevelPeak' in vlm)
check("VisualLevelModel evidence()", 'func evidence()' in vlm)

# 6. frameTimeMs غير observable (لا re-render loop)
check("frameTimeMs غير @Published", '@Published var frameTimeMs' not in vm)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
import sys
sys.exit(1 if FAIL else 0)
