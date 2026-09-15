"""M3.5 Live Voice Gate — regression (source-level). Physical retest required."""
import sys, os, re
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")
def read(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()

vae = read('Voice/VoiceAudioEngine.swift')
rvs = read('Voice/RealtimeVoiceSession.swift')
ac = read('Voice/AudioCapture.swift')
vs = read('Voice/VoiceSession.swift')
vm = read('Home/HomeViewModel.swift')

# A. Shared full-duplex graph
check("shared engine: AVAudioEngine", 'AVAudioEngine' in vae)
check("shared engine: AVAudioPlayerNode", 'AVAudioPlayerNode' in vae)
check("input tap (installTap)", 'installTap' in vae)
check("24kHz PCM16", '24000' in vae and 'pcmFormatInt16' in vae)
# AEC via voice-processing mode
check("AEC: voiceChat mode", 'mode: .voiceChat' in vae)
check("AEC: defaultToSpeaker", '.defaultToSpeaker' in vae)
# C. Coalescing (jitter fix)
check("coalescing: targetBufferBytes", 'targetBufferBytes' in vae)
check("coalescing: drainQueue merge", 'collected.count < targetBufferBytes' in vae)
check("continuous scheduling (completion→drain)", 'self.drainQueue()' in vae)
# B. Barge-in flush
check("flush (barge-in)", 'func flush()' in vae and 'player.reset()' in vae)

# RealtimeVoiceSession integration
check("session uses VoiceAudioEngine", 'VoiceAudioEngine()' in rvs)
check("no MicrophoneCapture/AudioPlayback (merged)", 'MicrophoneCapture' not in rvs and 'AudioPlayback' not in rvs)
check("full-duplex: no pauseMic/resumeMic", 'pauseMic' not in rvs and 'resumeMic' not in rvs)
check("barge-in: isSpeaking + bargeIn on speech_started", 'isSpeaking' in rvs and 'bargeIn' in rvs and 'speech_started' in rvs)
check("barge-in flushes audio", 'audio.flush()' in rvs)
check("no manual commit (server VAD owns)", 'input_audio_buffer.commit' not in rvs)

# mic permission
check("mic permission notDetermined→prompt", 'requestMic' in ac)
check("mic denied→structured", 'case .denied' in ac)
# state truth
check("JarvisStateMapper events→states", 'func state(for' in vs and '.speaking' in vs)
check("bindVoice → state", 'bindVoice' in vm and 'JarvisStateMapper.state' in vm)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
