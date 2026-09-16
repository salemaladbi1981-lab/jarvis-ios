"""Initial Viewport + Launch regression (source-level)."""
import os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1
def read(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()

home = read('Home/HomeView.swift')
core = read('Core/JarvisCoreView.swift')
adaptive = read('iPad/AdaptiveRootView.swift')
lt = read('Core/LaunchTiming.swift')

# 1. Core above the fold — scroll إلى الأعلى عند launch
check("defaultScrollAnchor(.top)", '.defaultScrollAnchor(.top)' in home)
check("scrollTo top عند cold launch (بدون -scrollBottom)", 'proxy.scrollTo("top", anchor: .top)' in home)
check("anchor id 'top' على أول عنصر (Header)", '.id("top")' in home)
check("-scrollBottom محصور للـ screenshot فقط", '"-scrollBottom"' in home and 'scrollTo("bottom"' in home)

# 2. Launch reset — لا scroll restoration قديم
check("scrollTo top يحدث في onAppear (يمنع restoration)", 'onAppear' in home and 'scrollTo("top"' in home)

# 3. Launch latency instrumentation
check("LaunchTiming helper", 'enum LaunchTiming' in lt and 'systemUptime' in lt)
check("home onAppear mark", 'home onAppear' in home)
check("adaptiveRoot onAppear mark", 'adaptiveRoot onAppear' in adaptive)
check("core first frame mark في onAppear (خارج render closure)", 'core onAppear' in core and 'onAppear' in core)
check("لا تعديل @State داخل Canvas render closure (crash fix)", 'didMarkFirstFrame' not in core)

# 4. Core أول عنصر بعد Header (وليس مدفوعاً للأسفل)
check("Core (JarvisHeroView) يلي Header مباشرة", 'HeaderView()' in home and 'JarvisHeroView(vm: vm)' in home)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
import sys
sys.exit(1 if FAIL else 0)
