"""Concept 2 Home regression — RootView -> HomeEntryView يحتوي النواة + المايك + الشريط.
يمنع الرجوع إلى HomeView القديم كجذر إنتاجي."""
import os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

root = open(os.path.join(ROOT, 'App/RootView.swift'), encoding='utf-8').read()
home = open(os.path.join(ROOT, 'Workspace/HomeEntryView.swift'), encoding='utf-8').read()

# 1) الجذر الإنتاجي = HomeEntryView (لا HomeView)
check("RootView.tabs → HomeEntryView (التبويب الرئيسي)", 'HomeEntryView(api: api)' in root)
check("RootView لا يرجع إلى HomeView القديم", 'HomeView(' not in root)

# 2) HomeEntryView يحتوي النواة السينمائية
check("HomeEntryView → JarvisHeroView (النواة)", 'JarvisHeroView(vm: voiceVM)' in home)

# 3) زر المايك البارز تحت النواة
check("HomeEntryView → JarvisMicControl (المايك)", 'JarvisMicControl(vm: voiceVM)' in home)

# 4) شريط الإدخال الدائم (composer)
check("HomeEntryView → WorkspaceComposerView (الشريط)", 'WorkspaceComposerView(' in home)
check("HomeEntryView → onMic موصول بـ toggleVoice", 'onMic: { voiceVM.toggleVoice() }' in home)

# 5) النواة/المايك مربوطان بصوت حقيقي (HomeViewModel) — لا fake
check("HomeEntryView → voiceVM = HomeViewModel()", '@StateObject private var voiceVM = HomeViewModel()' in home)

# 6) بيانات workspace محفوظة
check("المحادثات الأخيرة محفوظة", 'vm.conversations' in home)
check("المهام الجارية محفوظة", 'vm.activeTasks' in home)
check("التسليمات الأخيرة محفوظة", 'vm.deliveries' in home)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
