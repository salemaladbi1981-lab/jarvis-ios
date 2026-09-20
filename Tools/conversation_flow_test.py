"""Conversation flow regression — POST /conversations decode + navigation + Enter + no-dup."""
import os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
BROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'phase3', 'backend')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

home = open(os.path.join(ROOT, 'Workspace/HomeEntryView.swift'), encoding='utf-8').read()
models = open(os.path.join(ROOT, 'Workspace/WorkspaceModels.swift'), encoding='utf-8').read()
composer = open(os.path.join(ROOT, 'Workspace/WorkspaceComposerView.swift'), encoding='utf-8').read()
main = open(os.path.join(BROOT, 'main.py'), encoding='utf-8').read()

# 1) auth/session: enrollment يربط api + token
check("EnrollmentManager يربط api بـ sessionToken", 'api = JarvisAPI(baseURL: baseURL, sessionToken: token)' in open(os.path.join(ROOT, 'Auth/EnrollmentManager.swift'), encoding='utf-8').read())
check("HomeEntryView يستخدم enrollment (api)", '@EnvironmentObject private var enrollment' in home)

# 2) POST /conversations success/failure + decode
check("ConversationEnvelope موجود", 'struct ConversationEnvelope: Codable' in models)
check("ConversationEnvelope يغلّف conversation", 'let conversation: Conversation' in models)
check("newConversation يفكك ConversationEnvelope (لا flat Conversation)", 'ConversationEnvelope = try await api.postObject("conversations"' in home)
check("backend يرجع {\"conversation\": ...} (shape match)", '"conversation": conv' in main)
check("newConversation يرجع Conversation? + خطأ مرئي", 'func newConversation() async -> Conversation?' in home and 'newConversationError' in home)

# 3) navigation success
check("زر بدء محادثة ينتقل (newConv = ConvID(id: c.id))", 'newConv = ConvID(id: c.id)' in home)

# 4) send button + Enter + no-dup
check("إرسال عبر sendMessage", 'onSend:' in composer and 'func sendMessage' in home)
check("Enter مربوط (.onSubmit + submitLabel .send)", '.onSubmit(onSend)' in composer and '.submitLabel(.send)' in composer)
check("no duplicate sends (isSending guard)", 'guard !isSending else { return }' in home)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
