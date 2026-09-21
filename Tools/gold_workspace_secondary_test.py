"""Regression guards for Gold cinematic migration on secondary workspace screens.

The assertions intentionally protect production delivery/task/attachment/inbox/conversation flows while
requiring the remaining secondary workspace chrome to use explicit gold tokens.
"""
import os
import sys

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PASS = FAIL = 0


def read(path):
    with open(os.path.join(REPO, path), encoding='utf-8') as f:
        return f.read()


def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond:
        PASS += 1
    else:
        FAIL += 1


deliveries = read('JARVIS/Workspace/DeliveriesView.swift')
details = read('JARVIS/Workspace/DetailViews.swift')
preview = read('JARVIS/Workspace/AttachmentPreviewBar.swift')
menu = read('JARVIS/Workspace/AttachmentMenu.swift')
inbox = read('JARVIS/Workspace/InboxView.swift')
tasks = read('JARVIS/Workspace/TasksView.swift')
conversations = read('JARVIS/Workspace/ConversationListView.swift')

# Deliveries: gold accents, real API/download/share path unchanged.
check('Deliveries icon uses primary gold', 'foregroundColor(JarvisColor.primary_gold)' in deliveries)
check('Deliveries open action uses highlight gold', 'Button("فتح") { Task { await vm.open(d) } }' in deliveries and 'foregroundColor(JarvisColor.highlight_gold)' in deliveries)
check('Deliveries loading indicator uses gold tint', 'ProgressView().tint(JarvisColor.primary_gold)' in deliveries)
check('Deliveries keeps real GET endpoint', 'let rows = try await api.get("/deliveries")' in deliveries)
check('Deliveries keeps real download endpoint', 'api.download("/deliveries/\\(d.id)/download")' in deliveries)
check('Deliveries keeps system share sheet', 'UIActivityViewController(activityItems: [tmp]' in deliveries)
check('Deliveries has no legacy blue aliases', 'JarvisColor.primary_blue' not in deliveries and 'JarvisColor.highlight_blue' not in deliveries)

# Task/delivery details: gold navigation accents, polling and semantic statuses intact.
check('Task detail accents are explicit gold', details.count('JarvisColor.highlight_gold') >= 4)
check('Detail views have no legacy blue aliases', 'JarvisColor.primary_blue' not in details and 'JarvisColor.highlight_blue' not in details)
check('Task polling remains wired', 'vm.startPolling(taskId)' in details and 'vm.stopPolling()' in details)
check('Task polling still uses backend reload', 'do { task = try await api.getObject("tasks/\\(id)") }' in details)
check('Delivery detail still uses backend reload', 'do { delivery = try await api.getObject("deliveries/\\(id)") }' in details)
check('Task to conversation navigation preserved', 'ConversationView(api: api, conversationId: conv)' in details)
check('Delivery to task navigation preserved', 'TaskDetailView(api: api, taskId: task)' in details)
check('Semantic success/danger/warning colors preserved', 'return JarvisColor.success' in details and 'return JarvisColor.danger' in details and 'return JarvisColor.warning_demo' in details)

# Attachment preview: gold shell, remove/data/fallback behavior unchanged.
check('Attachment preview border uses primary gold', 'stroke(JarvisColor.primary_gold.opacity(0.25)' in preview)
check('Attachment fallback icon uses primary gold', 'foregroundColor(JarvisColor.primary_gold)' in preview)
check('Attachment preview has no legacy blue aliases', 'JarvisColor.primary_blue' not in preview and 'JarvisColor.highlight_blue' not in preview)
check('Attachment remove callback preserved', 'AttachmentThumb(att: att) { onRemove(att.id) }' in preview and 'Button(action: onRemove)' in preview)
check('Attachment image decode path preserved', 'UIImage(data: data)' in preview)
check('Attachment kind icons preserved', all(x in preview for x in ['case "video"', 'case "audio"', 'case "scan"']))

# Attachment menu: gold tile treatment, all seven production callbacks intact.
check('Attachment menu icon uses primary gold', 'foregroundColor(JarvisColor.primary_gold)' in menu)
check('Attachment menu tile border uses primary gold', 'stroke(JarvisColor.primary_gold.opacity(0.18)' in menu)
check('Attachment menu keeps plain button interaction', 'Button(action: action)' in menu and '.buttonStyle(.plain)' in menu)
check('Attachment menu has no legacy blue aliases', 'JarvisColor.primary_blue' not in menu and 'JarvisColor.highlight_blue' not in menu)
check('Attachment menu preserves all callbacks', all(x in menu for x in [
    'onPickPhotos', 'onPickVideos', 'onPickFiles', 'onCameraPhoto',
    'onCameraVideo', 'onScanDocument', 'onRecordAudio'
]))
check('Attachment menu preserves seven entry points', menu.count('attachItem(') == 8)  # declaration + 7 calls

# Inbox: migrate only interaction chrome; keep semantic attention colors and real navigation/API paths.
check('Inbox loading indicator uses primary gold', 'ProgressView()' in inbox and '.tint(JarvisColor.primary_gold)' in inbox)
check('Inbox navigation tint uses highlight gold', '.tint(JarvisColor.highlight_gold)' in inbox)
check('Inbox has no legacy blue aliases', 'JarvisColor.primary_blue' not in inbox and 'JarvisColor.highlight_blue' not in inbox)
check('Inbox semantic approval/failure/completion colors preserved', all(x in inbox for x in [
    'case .approval, .action: return JarvisColor.warning_demo',
    'case .failed: return JarvisColor.danger',
    'case .completed, .delivery: return JarvisColor.success'
]))
check('Inbox keeps real backend load', 'items = try await api.getArray("inbox")' in inbox)
check('Inbox keeps task/delivery/conversation navigation', all(x in inbox for x in [
    'TaskDetailView(api: api, taskId: taskId)',
    'DeliveryDetailView(api: api, deliveryId: deliveryId)',
    'ConversationView(api: api, conversationId: convId)'
]))

# Tasks list: gold shell only; backend state and semantic job colors remain authoritative.
check('Tasks loading and navigation chrome are gold', 'ProgressView().tint(JarvisColor.primary_gold)' in tasks and '.tint(JarvisColor.highlight_gold)' in tasks)
check('Task cards use restrained gold border and glow', 'stroke(JarvisColor.primary_gold.opacity(0.14)' in tasks and 'shadow(color: JarvisColor.primary_gold.opacity(0.04)' in tasks)
check('Tasks has no legacy blue aliases', 'JarvisColor.primary_blue' not in tasks and 'JarvisColor.highlight_blue' not in tasks)
check('Tasks keeps real backend load', 'items = try await api.getArray("tasks")' in tasks)
check('Tasks semantic job colors preserved', all(x in tasks for x in [
    'case "succeeded", "ready", "complete": return JarvisColor.success',
    'case "failed": return JarvisColor.danger',
    'case "running", "processing": return JarvisColor.warning_demo',
    'case "cancelled": return JarvisColor.text_muted'
]))
check('Tasks still displays backend error text as danger', 'task.lastError' in tasks and 'foregroundColor(JarvisColor.danger)' in tasks)

# Conversations list: cinematic gold shell while preserving real conversation API + navigation.
check('Conversations replace default List chrome with ScrollView cards', 'ScrollView {' in conversations and 'LazyVStack(spacing: JarvisSpacing.sm)' in conversations and '\n                    List {' not in conversations)
check('Conversation cards use gold border and restrained glow', 'stroke(JarvisColor.primary_gold.opacity(0.14)' in conversations and 'shadow(color: JarvisColor.primary_gold.opacity(0.04)' in conversations)
check('Conversation empty state uses gold card shell', 'stroke(JarvisColor.primary_gold.opacity(0.18)' in conversations and 'JarvisColor.bg_0.ignoresSafeArea()' in conversations)
check('Conversation navigation tint uses highlight gold', '.tint(JarvisColor.highlight_gold)' in conversations)
check('Conversations have no legacy blue aliases', 'JarvisColor.primary_blue' not in conversations and 'JarvisColor.highlight_blue' not in conversations)
check('Conversation navigation remains value-based and real', 'NavigationLink(value: conversation.id)' in conversations and 'ConversationView(api: api, conversationId: id)' in conversations)
check('Conversations keep real backend load', 'conversations = try await api.getArray("conversations")' in conversations)
check('New conversation keeps real backend create and local insertion', 'api.postObject("conversations", body: [:])' in conversations and 'conversations.insert(c, at: 0)' in conversations)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
