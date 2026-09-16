"""Regression: visual layers must not block touches; interactive controls must stay hit-testable."""
import sys, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")
def read(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()
core = read('Core/JarvisCoreView.swift')
wave = read('Core/WaveformView.swift')
hero = read('Core/JarvisHeroView.swift')
nav = read('Home/BottomNavBar.swift')
cards = read('Cards/Cards.swift')
check("JarvisCoreView (Canvas) allowsHitTesting(false)", '.allowsHitTesting(false)' in core)
check("WaveformView allowsHitTesting(false)", '.allowsHitTesting(false)' in wave)
check("JarvisHeroView visual ZStack allowsHitTesting(false)", '.allowsHitTesting(false)' in hero)
check("JarvisCoreView refresh 60fps (V1 visual)", '1.0 / 60.0' in core)
check("BottomNavBar buttons remain interactive", '.allowsHitTesting(false)' not in nav)
check("SmartHome/Security/Media cards remain interactive", '.allowsHitTesting(false)' not in cards)
print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
