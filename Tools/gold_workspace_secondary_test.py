"""Regression guards for Gold cinematic migration on secondary workspace screens.

The assertions intentionally protect production delivery/task/attachment flows while
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

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
