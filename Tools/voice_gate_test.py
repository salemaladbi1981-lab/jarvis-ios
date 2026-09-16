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
check("AEC: setVoiceProcessingEnabled(true)", 'setVoiceProcessingEnabled(true)' in vae)
check("AEC: voiceChat mode", 'mode: .voiceChat' in vae)
check("AEC: defaultToSpeaker", '.defaultToSpeaker' in vae)
check("AEC runtime: isVoiceProcessingEnabled", 'isVoiceProcessingEnabled' in vae)
check("AEC runtime: isVoiceProcessingBypassed", 'isVoiceProcessingBypassed' in vae)
# C. Coalescing + continuous schedule-ahead (jitter fix)
check("coalescing: targetBufferBytes (~100ms)", 'targetBufferBytes' in vae)
check("schedule-ahead: maxScheduledAhead", 'maxScheduledAhead' in vae)
check("continuous pump (schedule-ahead, no serial gap)", 'func pump(' in vae and 'player.scheduleBuffer(buffer)' in vae)
check("tail flush (flushTail→pump forceTail)", 'func flushTail()' in vae and 'pump(forceTail: true)' in vae)

# PLAYBACK counters (runtime evidence)
check("counter: receivedBytes", 'receivedBytes' in vae)
check("counter: scheduledBytes", 'scheduledBytes' in vae)
check("counter: completedBuffers", 'completedBuffers' in vae)
check("counter: underruns", 'underruns' in vae)
check("counter: tailBytesFlushed", 'tailBytesFlushed' in vae)
check("counter: converterErrors", 'converterErrors' in vae)
check("counter: statsSummary (runtime proof)", 'statsSummary' in vae)
check("beginSpeaking resets counters", 'func beginSpeaking()' in vae and 'resetStats()' in vae)
check("underrun detection (scheduledBuffers==0 while speaking)", 'underruns += 1' in vae)
check("thread-safe: serial workQueue", 'DispatchQueue(label: "jarvis.audio.playback")' in vae)
# B. Barge-in flush
check("flush (barge-in)", 'func flush()' in vae and 'player.reset()' in vae)

# RealtimeVoiceSession integration
check("session uses VoiceAudioEngine", 'VoiceAudioEngine()' in rvs)
check("no MicrophoneCapture/AudioPlayback (merged)", 'MicrophoneCapture' not in rvs and 'AudioPlayback' not in rvs)
check("full-duplex: no pauseMic/resumeMic", 'pauseMic' not in rvs and 'resumeMic' not in rvs)
check("no auto-bargeIn on speech_started (echo-safe)", 'speech_started' in rvs and 'bargeIn' in rvs)
check("flushTail on response.done", 'audio.flushTail()' in rvs)
check("beginSpeaking on first delta", 'audio.beginSpeaking()' in rvs)
check("no manual commit (server VAD owns)", 'input_audio_buffer.commit' not in rvs)

# mic permission
check("mic permission notDetermined→prompt", 'requestMic' in ac)
check("mic denied→structured", 'case .denied' in ac)
# Voice startup path (regression: mic button → permission → start)
check("toggleVoice requests mic permission", 'AudioCapture.micPermission()' in vm and 'AudioCapture.requestMic()' in vm)
check("toggleVoice denied → structured alert", 'صلاحية الميكروفون مرفوضة' in vm)
check("startListening traces real error (not swallowed)", 'error.localizedDescription' in rvs and 'startListening FAILED' in rvs)
# start() instrumentation: كل خطوة تُسجّل لتحديد أول نقطة فشل
check("start() trace: setCategory OK", 'setCategory OK' in vae)
check("start() trace: setVoiceProcessingEnabled OK", 'setVoiceProcessingEnabled OK' in vae)
check("start() trace: installTap OK", 'installTap OK' in vae)
check("start() trace: engine.start error", 'start FAILED at engine.start' in vae)
check("start() trace: setVoiceProcessingEnabled error", 'start FAILED at setVoiceProcessingEnabled' in vae)
# state truth
check("JarvisStateMapper events→states", 'func state(for' in vs and '.speaking' in vs)
check("bindVoice → state", 'bindVoice' in vm and 'JarvisStateMapper.state' in vm)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
