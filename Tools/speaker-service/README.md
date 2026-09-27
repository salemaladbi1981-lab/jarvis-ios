# Owner-verified interruption — 0.1.3 (7)

The iOS candidate gate retains at most six seconds of PCM in memory. While playback is active, microphone audio is withheld from upstream. Two consecutive speaker matches at cosine threshold 0.80 trigger cancel/truncate and replay of the verified utterance. Manual interruption remains available. Missing service, short/silent audio, mismatches, timeouts and stale results fail closed.

The earliest candidate is 1.6 seconds, followed by another distinct window and network/inference time. Expect roughly two seconds or longer; short wake words can be rejected. This feature is not authentication and does not protect against replayed recordings.

The private worker runs on 127.0.0.1:18010 under jarvis-owner-voice.service. Main backend routes require the authenticated PRIMARY_USER_ID and PERSONAL workspace. Profiles and model weights live outside git at /opt/data/jarvis-speaker. Incoming candidate audio is never persisted by the worker. The original recording was not transferred to the server; only the derived profile was transferred.

Model: https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/wespeaker_en_voxceleb_resnet34_LM.onnx
API: https://github.com/k2-fsa/sherpa-onnx/blob/master/python-api-examples/speaker-identification.py

Validation 2026-09-28:
- 17 tests executing actual Swift event/candidate logic passed.
- 8 authenticated bridge tests passed; public unauthenticated status returned 401.
- Live worker rejected silence.
- Six of seven held-out two-second owner clips matched; one was rejected.
- Reducing gain to 15% preserves normalized scores. This is not a real whispering test.
- Two external comparison recordings were rejected; this is a smoke test, not a population benchmark.
- A 24 kHz PCM positive clip scored 0.881 against the enrolled reference.
- iPhone build/install passed. Live owner and nearby-speaker acceptance remains pending.

Run Tools/realtime_event_regression_test.py on macOS, and test_routes.py with the path to phase3/backend/speaker_routes.py in a FastAPI environment. Never commit recordings or owner profiles.
