"""Device stability fixes regression (bugs 1-4):
1) typed chat → real conversation pipeline (not routeVoiceTranscript)
2) new conversation → visible error + logging (no silent catch{})
3) memory → backend single-brain (no MemoryStore.seeded)
4) voice single-brain (no local sendText dual-response) + error recovery."""
import os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

home = open(os.path.join(ROOT, 'Workspace/HomeEntryView.swift'), encoding='utf-8').read()
conv = open(os.path.join(ROOT, 'Workspace/ConversationView.swift'), encoding='utf-8').read()
vm = open(os.path.join(ROOT, 'Home/HomeViewModel.swift'), encoding='utf-8').read()

# 1) Typed chat → real conversation pipeline
check("typed chat لا يستدعي routeVoiceTranscript(", 'routeVoiceTranscript(' not in home)
check("typed chat ينشئ محادثة حقيقية (newConversation)", 'await vm.newConversation()' in home)
check("typed chat ينتقل لشاشة الدردشة (initialText)", 'newConv = ConvID(id: c.id, initialText: text)' in home)
check("ConversationView يقبل initialText ويرسله تلقائياً", 'initialText' in conv and 'await vm.send(t)' in conv)

# 2) New conversation → visible error + logging
check("newConversation يرجع Conversation? (لا ابتلاع)", 'func newConversation() async -> Conversation?' in home)
check("newConversation يسجّل الخطأ", 'print("[JARVIS-HOME] newConversation failed' in home)
check("newConversation يعرض الخطأ (newConversationError)", 'newConversationError' in home and 'if let nce = vm.newConversationError' in home)
check("لا catch {} صامت في newConversation", 'catch {}' not in home)

# 3) Memory → backend single-brain
check("لا MemoryStore.seeded في مسار الإنتاج", 'MemoryStore.seeded()' not in vm)
check("لا ensureMemory محلي", 'ensureMemory' not in vm)
check("لا memoryAnswer محلي", 'memoryAnswer' not in vm)

# 4) Voice single-brain + error recovery
check("لا sendText محلي (لا رد منافس)", 'voiceSession.sendText' not in vm)
check("معالج .error يسجّل رمز الخطأ", 'case .error(let code):' in vm and '[JARVIS-VOICE] error code' in vm)
check("استرداد تلقائي من الخطأ العابر", 'scheduleErrorRecovery' in vm and 'state = .idle' in vm)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
