"""The meeting entry is an honest skeleton, never an implicit recorder or fake store."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
home = (root / 'JARVIS/Workspace/HomeEntryView.swift').read_text()
model = (root / 'JARVIS/State/JarvisState.swift').read_text()
assert '.sheet(isPresented: $showMeetings)' in home
assert 'MeetingFoundationView()' in home
view = home.split('struct MeetingFoundationView: View')[1]
assert 'التقاط الاجتماعات غير متصل' in view
assert 'AVAudioRecorder' not in view and '.start(' not in view
assert 'protocol MeetingRecordStore' in model
assert 'func load(id: String, scope: MeetingScope)' in model
assert 'func save(_ record: MeetingRecord, scope: MeetingScope)' in model
print('PASS meeting entry, honest availability and scoped persistence contract')
