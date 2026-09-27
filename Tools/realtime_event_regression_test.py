"""Exercise the production Swift event handler with fake audio I/O, no network/device."""
from pathlib import Path
import subprocess, tempfile
root = Path(__file__).resolve().parents[1]
stubs = r'''
import Foundation
import Combine
enum JarvisState { case thinking, idle, listening, speaking, executing, approval, alert }
enum JarvisConfig { static var injectedSessionToken: String? = nil }
enum KeychainStore { static func load() -> String? { nil } }
enum JarvisAPIError: Error { case authentication }
final class VoiceAudioEngine {
    var onPCM: ((Data)->Void)?
    var onDiagnostics: ((String)->Void)?
    var onMicLevel: ((Double)->Void)?
    var onOutputLevel: ((Double)->Void)?
    var onPlaybackDrained: ((Int)->Void)?
    var currentGeneration = 0
    var playedDurationMs = 0
    var flushCount = 0
    static func rmsLevel(_ data: Data) -> Double? { 0.05 }
    func start() throws {}
    func stop() {}
    func beginSpeaking() { currentGeneration += 1 }
    func enqueueAudio(_ data: Data) {}
    func flushTail() {}
    func flush() { flushCount += 1; currentGeneration += 1 }
}
'''
checks = r'''
var failures = 0
func check(_ label: String, _ value: Bool) {
    print("\(value ? "PASS" : "FAIL") \(label)")
    if !value { failures += 1 }
}
func testAutoResponse() {
    let s = RealtimeVoiceSession()
    var thinking = 0
    let token = s.eventPublisher.sink { if case .thinking = $0 { thinking += 1 } }
    s.handleServer(#"{"type":"session.created"}"#)
    s.handleServer(#"{"type":"session.updated","session":{"audio":{"input":{"turn_detection":{"create_response":true}}}}}"#)
    s.requestResponse()
    s.stateQueue.sync {}
    check("server auto response does not request a duplicate", thinking == 0)
    s.handleServer(#"{"type":"session.updated","session":{"audio":{"input":{"turn_detection":{"create_response":false}}}}}"#)
    s.requestResponse()
    s.stateQueue.sync {}
    check("manual server still receives response request", thinking == 1)
    s.requestResponse()
    s.stateQueue.sync {}
    check("duplicate local request is suppressed while pending", thinking == 1)
    withExtendedLifetime(token) {}
}
func testTail() {
    let s = RealtimeVoiceSession()
    s.startListening()
    s.handleServer(#"{"type":"session.created"}"#)
    s.handleServer(#"{"type":"response.created","response":{"id":"r1"}}"#)
    s.handleServer(#"{"type":"response.output_audio.delta","response_id":"r1","delta":"AAAAAA=="}"#)
    s.handleServer(#"{"type":"response.done","response":{"id":"r1","status":"completed"}}"#)
    check("speaking remains active until local playback drains", s.isSpeaking)
    s.handleServer(#"{"type":"input_audio_buffer.speech_started"}"#)
    check("room speech does not discard unplayed response tail", s.audio.flushCount == 0)
    s.audio.onPlaybackDrained?(s.audio.currentGeneration)
    s.stateQueue.sync {}
    check("matching playback completion clears speaking", !s.isSpeaking)
    s.interrupt()
    check("explicit interruption still flushes playback", s.audio.flushCount == 1)
}
func testErrors() {
    let s = RealtimeVoiceSession()
    var errors = 0
    let token = s.eventPublisher.sink { if case .error = $0 { errors += 1 } }
    s.handleServer(#"{"type":"session.created"}"#)
    s.handleServer(#"{"type":"error","error":{"code":"conversation_already_has_active_response"}}"#)
    check("active response conflict does not disconnect microphone", errors == 0)
    s.handleServer(#"{"type":"error","error":{"code":"response_cancel_not_active"}}"#)
    check("cancel after generation finished is nonfatal", errors == 0)
    s.handleServer(#"{"type":"error","error":{"code":"invalid_api_key"}}"#)
    check("unexpected provider errors remain visible", errors == 1)
    withExtendedLifetime(token) {}
}
func testOwnerGate() {
    var gate = OwnerVoiceCandidate()
    let speech = Data(repeating: 1, count: 76800)
    gate.append(speech, level: 0.05)
    let (_, epoch) = gate.nextClip()!
    check("only one verification may be in flight", gate.nextClip() == nil)
    check("one speaker match cannot interrupt", gate.complete(matched: true, epoch: epoch) == nil)
    gate.append(Data(repeating: 1, count: 24000), level: 0.05)
    let (_, secondEpoch) = gate.nextClip()!
    check("two consecutive matches replay complete utterance", gate.complete(matched: true, epoch: secondEpoch)?.count == 100800)
    gate.append(speech, level: 0.05)
    let (_, staleEpoch) = gate.nextClip()!
    gate.reset()
    check("stale verification cannot interrupt a new turn", gate.complete(matched: true, epoch: staleEpoch) == nil)
    gate.append(speech, level: 0.05)
    let (_, e1) = gate.nextClip()!
    _ = gate.complete(matched: true, epoch: e1)
    gate.append(Data(repeating: 1, count: 24000), level: 0.05)
    let (_, e2) = gate.nextClip()!
    check("mismatch clears previous confirmation", gate.complete(matched: false, epoch: e2) == nil && gate.confirmations == 0)
    gate.append(Data(repeating: 0, count: 16800), level: 0)
    check("silence clears candidate audio", gate.buffer.isEmpty)
    gate.append(Data(repeating: 0, count: 96000), level: 0)
    check("silence never starts verification", gate.nextClip() == nil)
}
testAutoResponse()
testTail()
testErrors()
testOwnerGate()
if failures > 0 { exit(1) }
'''
source = stubs
for name in ["SessionEventParser.swift", "SessionGuardState.swift", "VoiceSession.swift", "RealtimeVoiceSession.swift"]:
    # Only expose access for testing; execute original method bodies unchanged.
    source += "\n" + (root/"JARVIS"/"Voice"/name).read_text().replace("private ", "")
source += "\n" + checks
with tempfile.TemporaryDirectory(prefix="jarvis-voice-regression-") as directory:
    p = Path(directory)
    (p/"main.swift").write_text(source)
    subprocess.run(["xcrun","swiftc","-swift-version","5",str(p/"main.swift"),"-o",str(p/"checks")], check=True)
    result = subprocess.run([str(p/"checks")])
    raise SystemExit(result.returncode)
