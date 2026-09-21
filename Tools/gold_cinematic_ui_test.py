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

# 4) The staged Home header now uses explicit gold semantics rather than compatibility aliases.
check('Header location accent uses primary gold', 'JarvisColor.primary_gold' in header)
check('Header wordmark uses highlight gold', 'JarvisColor.highlight_gold' in header)
check('Header no longer uses legacy blue aliases', 'JarvisColor.primary_blue' not in header and 'JarvisColor.highlight_blue' not in header)
check('Header location/clock behavior is preserved', '@StateObject private var location = LocationManager()' in header and 'location.requestWhenNeeded()' in header and 'LiveClockView()' in header)

# 5) Migration must not replace production interaction/data paths.
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
