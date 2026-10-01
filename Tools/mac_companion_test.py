"""Shared production architecture and Mac navigation regression guard."""
from pathlib import Path
root = Path(__file__).resolve().parents[1] / 'JARVIS'
app = (root / 'macOS/MacApp.swift').read_text()
mac = (root / 'macOS/MacHomeView.swift').read_text()
adaptive = (root / 'iPad/AdaptiveRootView.swift').read_text()
home = (root / 'Workspace/HomeEntryView.swift').read_text()
assert 'EnrollmentManager(baseURL: JarvisConfig.baseURL)' in app
assert '.environmentObject(enrollment)' in app
assert 'enrollment.isEnrolled || isPreview' in app
for view in ['HomeEntryView', 'ConversationListView', 'InboxView', 'TasksView', 'DeliveriesView']:
    assert view+'(api: api)' in mac, view
assert 'NavigationSplitView' in mac
assert 'iPadLandscapeView()' not in adaptive
assert 'RootView()' in adaptive
assert '.onDisappear { voiceVM.handleAppBackgrounded() }' in home
print('PASS: enrolled Mac workspace, functional destinations, shared cinematic Home, voice lifecycle cleanup, iPad production route')
