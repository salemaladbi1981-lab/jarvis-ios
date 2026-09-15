"""M3.5 Live Voice Gate — regression (source-level). Physical mic/audio retest required."""
import sys, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")
def read(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()
mic = read('Voice/MicrophoneCapture.swift')
play = read('Voice/AudioPlayback.swift')
rvs = read('Voice/RealtimeVoiceSession.swift')
ac = read('Voice/AudioCapture.swift')
vs = read('Voice/VoiceSession.swift')
vm = read('Home/HomeViewModel.swift')

# mic capture REAL
check("MicrophoneCapture uses AVAudioEngine", 'AVAudioEngine' in mic)
check("MicrophoneCapture installTap (real PCM)", 'installTap' in mic)
check("MicrophoneCapture → 24kHz PCM16", '24000' in mic and 'pcmFormatInt16' in mic)
# playback REAL
check("AudioPlayback uses AVAudioPlayerNode", 'AVAudioPlayerNode' in play)
check("AudioPlayback enqueues PCM16", 'enqueue' in play and 'pcmFormatInt16' in play)
# session binding
check("RealtimeVoiceSession holds mic + playback", 'MicrophoneCapture()' in rvs and 'AudioPlayback()' in rvs)
check("sendAudio PCM16 base64", 'input_audio_buffer.append' in rvs)
check("onTranscript callback present", 'onTranscript' in rvs)
check("barge-in response.cancel present", 'response.cancel' in rvs)
# mic permission mapping
check("mic permission notDetermined→prompt path", 'requestMic' in ac)
check("mic denied→structured", 'case .denied' in ac)
# state truth
check("JarvisStateMapper maps events→7 states", 'func state(for' in vs and '.speaking' in vs)
check("HomeViewModel binds eventPublisher→state", 'bindVoice' in vm and 'JarvisStateMapper.state' in vm)
# voice → tool routing
check("toggleVoice starts real session", 'toggleVoice' in vm and 'connect(baseURL' in vm)
check("voice transcript routes calendar", 'routeVoiceTranscript' in vm and 'runCalendar' in vm)
check("voice transcript routes reminders", 'routeVoiceTranscript' in vm and 'runReminders' in vm)
check("unknown voice → sendText (not listening)", 'voiceSession.sendText(text)' in vm)
# production path not mock
check("uses RealtimeVoiceSession (not MockVoiceProvider)", 'RealtimeVoiceSession()' in vm)
# approval not bypassed
check("approval flow intact (requestAction)", 'requestAction' in vm and 'approval' in vm)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
