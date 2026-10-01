"""Guard production defaults and prevent reintroducing fabricated card fallbacks."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
vm = (root / 'JARVIS/Home/HomeViewModel.swift').read_text()
for provider in ['SmartHome', 'Security', 'Media']:
    assert f'{provider}Provider = Unavailable{provider}Provider()' in vm
    assert f'= Mock{provider}Provider()' not in vm
for file in ['Home/HomeView', 'iPad/iPadLandscapeView', 'macOS/MacHomeView']:
    text = (root / ('JARVIS/' + file + '.swift')).read_text()
    assert '?? SecurityStatus(' not in text
    assert '?? MediaTrack(' not in text
assert 'MemoryStore.seeded()' not in vm
assert 'case .idle: return "جاهز عندما تحتاجني"' in vm
print('PASS: production defaults, cards, idle status, and local memory isolation')
