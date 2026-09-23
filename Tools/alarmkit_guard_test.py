"""AlarmKit compile-guard regression.
Policy: HomeViewModel must build on toolchains without an AlarmKit SDK (Xcode 15.4 CI)
and with it (Xcode 26+). Every AlarmKit symbol must sit inside #if canImport(AlarmKit).
Alarm behaviour itself is unchanged: iOS 26 availability gate + its fallback message."""
import os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

PATH = os.path.join(ROOT, 'Home/HomeViewModel.swift')
src = open(PATH, encoding='utf-8').read()
lines = src.split('\n')

# AlarmKit SDK symbols + the types that only exist inside the guard.
SYMBOLS = re.compile(r'\b(AlarmKit|AlarmMetadata|AlarmManager|AlarmButton|AlarmPresentation'
                     r'|AlarmAttributes|JarvisAlarmMetadata|JarvisAlarmScheduler)\b')
OPENS_GUARD = re.compile(r'^\s*#if\s+canImport\(AlarmKit\)\s*$')

unguarded = []          # (line number, text) for AlarmKit symbols outside the guard
stack = []              # one bool per open #if: does this branch sit under canImport(AlarmKit)?
for n, line in enumerate(lines, 1):
    s = line.strip()
    if s.startswith('#if'):
        opening = bool(OPENS_GUARD.match(line))
        stack.append(opening or any(stack))
        continue            # the guard line itself is not a use site
    if s.startswith('#elseif') or s.startswith('#else'):
        if stack:           # the fallback branch is NOT covered by this guard
            stack[-1] = any(stack[:-1])
        continue
    if s.startswith('#endif'):
        if stack: stack.pop()
        continue
    code = line.split('//', 1)[0]   # comments never reach the compiler
    if SYMBOLS.search(code) and not any(stack):
        unguarded.append((n, s))

check("every AlarmKit symbol in HomeViewModel.swift is inside #if canImport(AlarmKit)",
      not unguarded)
if unguarded:
    for n, s in unguarded:
        print(f"        unguarded line {n}: {s}")

check("guard brackets are balanced", stack == [])
check("AlarmKit import stays conditional", '#if canImport(AlarmKit)\nimport AlarmKit' in src)
check("scheduler type is declared under the guard",
      'private struct JarvisAlarmMetadata: AlarmMetadata {}' in src
      and 'enum JarvisAlarmScheduler {' in src)
check("scheduler is still reached only through the guarded call site",
      '#if canImport(AlarmKit)' in src and 'await JarvisAlarmScheduler.schedule(at: date)' in src)

# Behaviour must be untouched by the compile guard.
check("iOS 26 availability gate preserved", '@available(iOS 26.0, *)' in src
      and 'if #available(iOS 26.0, *) {' in src)
check("iOS 26 fallback message preserved", 'المنبه يتطلب iOS 26 أو أحدث' in src)
check("system verification before claiming success preserved",
      "$0.state == .scheduled" in src and 'تعذر التحقق من المنبه' in src)
check("grounded device reply for alarms preserved",
      'voiceSession.sendGroundedDeviceResult(userRequest: userRequest, result: result)' in src)
check("privacy string for AlarmKit is declared",
      'NSAlarmKitUsageDescription' in open(os.path.join(ROOT, 'Info.plist'), encoding='utf-8').read())

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
