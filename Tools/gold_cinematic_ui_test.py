"""Gold cinematic UI migration regression.

Keeps the visual migration token-driven so chat, voice, project-health and
workspace production wiring remain untouched while the approved gold identity
replaces the legacy cyan accent.
"""
import json
import os
import sys

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
JARVIS = os.path.join(REPO, 'JARVIS')
PASS = FAIL = 0


def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond:
        PASS += 1
    else:
        FAIL += 1


def read(path):
    with open(os.path.join(REPO, path), encoding='utf-8') as f:
        return f.read()


with open(os.path.join(JARVIS, 'Resources', 'DESIGN-TOKENS.json'), encoding='utf-8') as f:
    spec = json.load(f)

swift = read('JARVIS/DesignSystem/JarvisTokens.swift')
home = read('JARVIS/Workspace/HomeEntryView.swift')
header = read('JARVIS/Home/HeaderView.swift')
bottom_nav = read('JARVIS/Home/BottomNavBar.swift')
quick_suggestions = read('JARVIS/Home/QuickSuggestions.swift')
cards = read('JARVIS/Cards/Cards.swift')
composer = read('JARVIS/Workspace/WorkspaceComposerView.swift')
hero = read('JARVIS/Core/JarvisHeroView.swift')
colors = spec['colors']
glow = spec['glow']

# 1) Approved cinematic identity is explicit and source/generated tokens agree.
check('theme = gold_cinematic', spec.get('theme', {}).get('name') == 'gold_cinematic')
check('migration is accent foundation', spec.get('theme', {}).get('migration_stage') == 'accent-foundation')
check('primary gold source token', colors.get('primary_gold') == '#D8B45C')
check('highlight gold source token', colors.get('highlight_gold') == '#F1D48A')
check('Swift exposes canonical gold tokens', 'static let primary_gold = Color(hex: "#D8B45C")' in swift and 'static let highlight_gold = Color(hex: "#F1D48A")' in swift)

# 2) Legacy names remain compatibility aliases, not a second cyan palette.
check('legacy primary alias maps to gold', colors.get('primary_blue') == colors.get('primary_gold') and 'static let primary_blue = primary_gold' in swift)
check('legacy highlight alias maps to gold', colors.get('highlight_blue') == colors.get('highlight_gold') and 'static let highlight_blue = highlight_gold' in swift)
check('old cyan literals removed from generated palette', '#8EC5FF' not in swift and '#B8DFFF' not in swift)

# 3) Cinematic glow/orbit/icon roles migrated while semantic status colors stay intact.
check('core glow uses gold', glow['core_glow']['color'] == colors['primary_gold'])
check('active agent glow uses gold', glow['agent_active']['chip_border'] == colors['primary_gold'] and glow['agent_active']['node_color'] == colors['highlight_gold'])
check('icon style declares warm cinematic gold', 'warm cinematic gold' in spec['icons']['style'])
check('semantic success preserved', colors.get('success') == '#63D9A0')
check('semantic danger preserved', colors.get('danger') == '#FF6B6B')

# 4) Staged Home chrome uses explicit gold semantics rather than compatibility aliases.
check('Header location accent uses primary gold', 'JarvisColor.primary_gold' in header)
check('Header wordmark uses highlight gold', 'JarvisColor.highlight_gold' in header)
check('Header no longer uses legacy blue aliases', 'JarvisColor.primary_blue' not in header and 'JarvisColor.highlight_blue' not in header)
check('Header location/clock behavior is preserved', '@StateObject private var location = LocationManager()' in header and 'location.requestWhenNeeded()' in header and 'LiveClockView()' in header)
check('Bottom navigation active state uses highlight gold', 'selected == item.id ? JarvisColor.highlight_gold : JarvisColor.text_muted' in bottom_nav)
check('Bottom navigation no longer uses legacy blue aliases', 'JarvisColor.primary_blue' not in bottom_nav and 'JarvisColor.highlight_blue' not in bottom_nav)
check('Bottom navigation keeps four production destinations', all(token in bottom_nav for token in ['("home", "الرئيسية"', '("devices", "الأجهزة"', '("car", "السيارة"', '("more", "المزيد"']))

# 5) Voice-facing hero chrome is explicitly gold while behavior/status semantics stay intact.
check('Waveform status indicator uses primary gold', '.fill(JarvisColor.primary_gold)' in hero)
check('Active agent badge uses explicit primary gold', 'Text("ACTIVE AGENT")' in hero and 'JarvisColor.primary_gold.opacity(0.45)' in hero)
check('Mic listening/speaking/thinking states use primary gold', 'case .listening, .speaking, .thinking: return JarvisColor.primary_gold' in hero)
check('Mic idle state uses primary gold', 'default: return JarvisColor.primary_gold' in hero)
check('Hero no longer uses legacy blue alias', 'JarvisColor.primary_blue' not in hero and 'JarvisColor.highlight_blue' not in hero)
check('Mic interaction remains manual toggleVoice', 'Button(action: { vm.toggleVoice() })' in hero)
check('Mic state labels preserve interruption behavior', 'case .speaking: return "اضغط للمقاطعة"' in hero and 'case .listening: return "أنا أسمعك…"' in hero)
check('Semantic execution/error/approval colors stay distinct', 'case .executing: return JarvisColor.success' in hero and 'case .alert: return JarvisColor.danger' in hero and 'case .approval: return JarvisColor.warning_demo' in hero)

# 6) Quick suggestions adopt gold styling without changing typed command dispatch.
check('Suggestion chips use primary gold border', 'JarvisColor.primary_gold.opacity(0.24)' in quick_suggestions)
check('Suggestion chips use restrained gold glow', 'JarvisColor.primary_gold.opacity(0.07)' in quick_suggestions)
check('Suggestion chips no longer use legacy blue aliases', 'JarvisColor.primary_blue' not in quick_suggestions and 'JarvisColor.highlight_blue' not in quick_suggestions)
check('Suggestion typed command dispatch is preserved', '.onTapGesture { onTap(cmd) }' in quick_suggestions and 'let commands: [QuickCommand]' in quick_suggestions)
check('Suggestion accessibility button semantics preserved', '.accessibilityAddTraits(.isButton)' in quick_suggestions and '.accessibilityLabel("أمر: \\(cmd.label)")' in quick_suggestions)

# 7) Shared cards/media adopt gold chrome while retaining semantic status roles.
check('Shared card border uses primary gold', 'stroke(JarvisColor.primary_gold.opacity(0.18)' in cards)
check('Shared card glow is restrained gold', 'shadow(color: JarvisColor.primary_gold.opacity(0.05)' in cards)
check('Security icon accents use primary gold', '.foregroundColor(JarvisColor.primary_gold)' in cards)
check('Media artwork gradient uses primary gold', 'LinearGradient(colors: [JarvisColor.primary_gold, JarvisColor.bg_1]' in cards)
check('Media progress uses explicit primary gold', 'Capsule().fill(JarvisColor.primary_gold.opacity(0.15))' in cards and 'Capsule().fill(JarvisColor.primary_gold).frame(width: geo.size.width * 0.6' in cards)
check('Cards no longer use legacy blue aliases', 'JarvisColor.primary_blue' not in cards and 'JarvisColor.highlight_blue' not in cards)
check('Demo badge warning semantics preserved', '.foregroundColor(JarvisColor.warning_demo)' in cards and 'JarvisColor.warning_demo.opacity(0.12)' in cards)
check('Security success semantics preserved', '.foregroundColor(JarvisColor.success)' in cards)
check('Card production models preserved', 'let devices: [SmartDevice]' in cards and 'let status: SecurityStatus' in cards and 'let track: MediaTrack' in cards)

# 8) Workspace composer adopts gold shell without changing send/attachment/mic wiring.
check('Composer attach and mic accents use primary gold', 'Image(systemName: "plus.circle.fill")' in composer and 'Image(systemName: "mic.fill")' in composer and composer.count('JarvisColor.primary_gold') >= 4)
check('Composer send-ready accent uses highlight gold', 'canSend ? JarvisColor.highlight_gold : JarvisColor.text_muted' in composer)
check('Composer text field tint uses highlight gold', '.tint(JarvisColor.highlight_gold)' in composer)
check('Composer shell uses gold border and glow', 'stroke(JarvisColor.primary_gold.opacity(0.18)' in composer and 'shadow(color: JarvisColor.primary_gold.opacity(0.06)' in composer)
check('Composer preserves send callback paths', 'Button(action: onSend)' in composer and '.onSubmit(onSend)' in composer)
check('Composer preserves attachment and mic callbacks', 'Button(action: onAttach)' in composer and 'Button(action: onMic)' in composer)
check('Composer send gating preserves text-or-attachment rule', '!text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || hasAttachments' in composer and '.disabled(!canSend)' in composer)
check('Composer no longer depends on legacy blue aliases', 'JarvisColor.primary_blue' not in composer and 'JarvisColor.highlight_blue' not in composer)

# 9) Migration must not replace production interaction/data paths.
check('Home keeps cinematic hero', 'JarvisHeroView(vm: voiceVM)' in home)
check('Home keeps real microphone control', 'JarvisMicControl(vm: voiceVM)' in home and 'onMic: { voiceVM.toggleVoice() }' in home)
check('Home keeps project health monitor', 'projectHealthCard(health)' in home and 'api.getObject("project/health")' in home)
check('Home keeps real conversation creation', 'await vm.newConversation()' in home and 'ConversationView(api: api' in home)
check('Home keeps workspace composer', 'WorkspaceComposerView(' in home)
check('Home keeps App Intent voice handoff', 'voiceVM.handleAppIntentStart()' in home)
check('Home keeps background lifecycle guard', 'voiceVM.handleAppBackgrounded()' in home)
check('Hero behavior remains state-driven', 'vm.toggleVoice()' in hero and 'switch vm.state' in hero)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
