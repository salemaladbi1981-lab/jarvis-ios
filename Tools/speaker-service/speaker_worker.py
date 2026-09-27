"""Private loopback speaker verification worker; never stores request audio."""
import json
import os
import threading
from pathlib import Path

import numpy as np
import sherpa_onnx
from fastapi import FastAPI, Request, HTTPException

ROOT = Path(os.environ.get("JARVIS_SPEAKER_ROOT", "/opt/data/jarvis-speaker"))
profile = json.loads((ROOT / "owner-profile.json").read_text())
reference = np.asarray(profile["reference"], dtype=np.float32)
reference /= np.linalg.norm(reference)
THRESHOLD = max(0.80, float(profile.get("threshold", 0.80)))
extractor = sherpa_onnx.SpeakerEmbeddingExtractor(
    sherpa_onnx.SpeakerEmbeddingExtractorConfig(
        model=str(ROOT / "model.onnx"), num_threads=2, provider="cpu"
    )
)
lock = threading.Lock()
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def verify_pcm(data: bytes) -> dict:
    # Fixed wire format: PCM16LE, mono, 24 kHz. Reject short/oversized clips.
    if len(data) < 76800 or len(data) > 153600 or len(data) % 2:
        return {"matched": False, "reason": "invalid_audio"}
    samples = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0
    frames = samples[:len(samples)//480*480].reshape(-1, 480)
    rms = np.sqrt(np.mean(frames * frames, axis=1))
    if np.mean(rms > 0.004) < 0.45:
        return {"matched": False, "reason": "insufficient_speech"}
    # Match enrollment preprocessing so changing volume alone does not change identity.
    samples = np.clip(samples * (0.10 / max(float(np.sqrt(np.mean(samples*samples))), 1e-6)), -1, 1)
    # Single inference at a time; reject excess load instead of queuing stale decisions.
    if not lock.acquire(blocking=False):
        return {"matched": False, "reason": "busy"}
    try:
        stream = extractor.create_stream()
        stream.accept_waveform(24000, samples)
        stream.input_finished()
        if not extractor.is_ready(stream):
            return {"matched": False, "reason": "insufficient_audio"}
        embedding = np.asarray(extractor.compute(stream), dtype=np.float32)
        norm = float(np.linalg.norm(embedding))
        if not np.isfinite(norm) or norm <= 0:
            return {"matched": False, "reason": "invalid_embedding"}
        similarity = float(np.dot(embedding / norm, reference))
        return {"matched": bool(similarity >= THRESHOLD), "score": round(similarity, 4)}
    finally:
        lock.release()


@app.get("/status")
def status():
    return {"enabled": True, "profile_version": profile["version"], "minimum_ms": 1600}


@app.post("/verify")
async def verify(request: Request):
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 153600:
            raise HTTPException(413, "audio_too_large")
    import asyncio
    return await asyncio.to_thread(verify_pcm, bytes(data))
