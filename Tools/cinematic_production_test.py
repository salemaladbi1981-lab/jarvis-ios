"""Regression guard for approved cinematic tokens and production Home composition."""
from pathlib import Path
import json
root = Path(__file__).resolve().parents[1]
swift = (root / 'JARVIS/DesignSystem/JarvisTokens.swift').read_text()
tokens = json.loads((root / 'JARVIS/Resources/DESIGN-TOKENS.json').read_text())['colors']
for name in ['bg_0', 'bg_1', 'primary_blue', 'highlight_blue', 'text_primary']:
    assert tokens[name] in swift, name
assert tokens['primary_blue'] == '#CDA968'
assert tokens['bg_0'] == '#080706'
home = (root / 'JARVIS/Workspace/HomeEntryView.swift').read_text()
assert home.index('.safeAreaInset') < home.index('.navigationDestination'), 'Composer belongs to Home content, not entire navigation stack'
for symbol in ['JarvisHeroView(vm: voiceVM,', 'JarvisMicControl(vm: voiceVM)', 'vm.conversations', 'vm.activeTasks', 'vm.deliveries']:
    assert symbol in home
core = (root / 'JARVIS/Core/JarvisCoreView.swift').read_text()
assert 'paused: reduceMotion || state == .idle' in core
assert 'idleBreath * sin' not in core
composer = (root / 'JARVIS/Workspace/WorkspaceComposerView.swift').read_text()
assert '.accessibilityLabel("إرسال الرسالة")' in composer
assert '.frame(width: 44, height: 44)' in composer
assert '.onSubmit { if !disabled && canSend' in composer
print('PASS: warm-gold palette, real-state motion, persistent composer, accessible controls, retained production sections')
