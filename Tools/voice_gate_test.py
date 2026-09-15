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
check("unknown voice → no action (no re-send, no listening)", 'voiceSession.sendText(text)' not in vm and 'state = .listening' not in vm)
# production path not mock
check("uses RealtimeVoiceSession (not MockVoiceProvider)", 'RealtimeVoiceSession()' in vm)
# approval not bypassed
check("approval flow intact (requestAction)", 'requestAction' in vm and 'approval' in vm)


# M3.5 loop regression (bug: assistant transcript re-routed → infinite loop)
rvs2 = read('Voice/RealtimeVoiceSession.swift')
vm2 = read('Home/HomeViewModel.swift')
check("assistant transcript.done does NOT call onTranscript", 'response.output_audio_transcript.done' in rvs2 and 'break' in rvs2)
check("direct conversation does NOT re-send text", 'voiceSession.sendText(text)' not in vm2)


# BUG#6: half-duplex (mic pause/resume) — يمنع echo/تداخل turn
check("full-duplex: no pauseMic on audio delta", 'pauseMic' not in rvs2)
check("barge-in: isSpeaking + bargeIn on speech_started", 'isSpeaking' in rvs2 and 'bargeIn' in rvs2 and 'speech_started' in rvs2)
import re as _re
_m = _re.search(r'private func handleAudio\(.*?\n    \}', rvs2, _re.DOTALL)
check("handleAudio no duplicate .speaking", _m is not None and 'eventPublisher.send(.speaking)' not in _m.group(0))


# BUG#6.2: mic.stop must NOT kill shared AVAudioSession (playback silence)
mic2 = read('Voice/MicrophoneCapture.swift')
play2 = read('Voice/AudioPlayback.swift')
def _stop_block(src, name):
    import re
    m = re.search(r'func stop\(\) \{.*?\n    \}', src, re.DOTALL)
    return m.group(0) if m else ''
_mic_stop = _stop_block(mic2, 'Mic')
_play_stop = _stop_block(play2, 'Play')
check("mic.stop does NOT deactivate AudioSession", 'setActive(false' not in _mic_stop)
check("playback.stop owns AudioSession deactivation", 'setActive(false' in _play_stop)


# BUG#6.3: repeated pause/resume must not crash (engine recreated, idempotent)
mic3 = read('Voice/MicrophoneCapture.swift')
check("engine is optional (recreated per start)", 'var engine: AVAudioEngine?' in mic3)
check("start creates fresh engine", 'let engine = AVAudioEngine()' in mic3)
check("start is idempotent (guard isRunning)", 'engine?.isRunning == true { return }' in mic3)
check("stop nils engine (clean state)", 'engine = nil' in mic3)


# M3.5 turn-integrity: 1 turn → 1 response → drained → resume (no echo loop)
rvs3 = read('Voice/RealtimeVoiceSession.swift')
mic4 = read('Voice/MicrophoneCapture.swift')
check("no resumeMic (full-duplex keeps mic on)", 'resumeMic' not in rvs3)
check("response.done clears isSpeaking", 'isSpeaking = false' in rvs3)
check("no manual commit (server VAD owns commit)", 'input_audio_buffer.commit' not in rvs3)
check("mic.start does NOT reconfigure AudioSession", 'session.setCategory' not in mic4)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
