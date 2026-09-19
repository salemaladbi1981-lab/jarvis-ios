"""JARVIS media derivatives — image thumbnail / video poster / audio waveform / document metadata.

Deterministic (fixed params) + cacheable (under the file's own dir) + fail-safe
(no crash on corrupt/unsupported media; status = GENERATED / UNSUPPORTED / FAILED).
No shell interpolation — ffmpeg runs via subprocess with a list of args.
"""
from __future__ import annotations
import os, shutil, json, subprocess, wave, array
from pathlib import Path
import storage

THUMB_MAX = 256
POSTER_MAX = 640
WAVE_W, WAVE_H, WAVE_BUCKETS = 640, 120, 96
WAVE_COLOR = (212, 162, 78)  # warm gold — matches JARVIS accent

IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp", "heic"}
VIDEO_EXT = {"mp4", "mov", "m4v", "webm"}
AUDIO_EXT = {"mp3", "m4a", "wav", "aac", "ogg", "flac"}
DOC_EXT = {"pdf", "doc", "docx", "txt", "md", "rtf"}


def ext_of(filename: str) -> str:
    return Path(filename or "").suffix.lower().lstrip(".")


def kind_for(filename: str) -> str:
    e = ext_of(filename)
    if e in IMAGE_EXT:
        return "image"
    if e in VIDEO_EXT:
        return "video"
    if e in AUDIO_EXT:
        return "audio"
    if e in DOC_EXT:
        return "document"
    return "file"


def deriv_dir(file_id: str) -> str:
    d = os.path.join(storage.FILES_DIR, file_id, "derivatives")
    os.makedirs(d, exist_ok=True)
    return d


def _has_pil() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except Exception:
        return False


def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _st(d, key, status, ref=None):
    d[key] = {"status": status, "ref": ref}


def _ok(path: str) -> bool:
    return os.path.exists(path) and os.path.getsize(path) > 0


def _thumbnail_image(src: str, out: str) -> bool:
    try:
        from PIL import Image
        with Image.open(src) as im:
            im = im.convert("RGB")
            im.thumbnail((THUMB_MAX, THUMB_MAX))
            im.save(out, "PNG")
        return _ok(out)
    except Exception:
        return False


def _poster_video(src: str, out: str) -> bool:
    ff = shutil.which("ffmpeg")
    if not ff:
        return False
    try:
        r = subprocess.run(
            [ff, "-y", "-i", src, "-ss", "0", "-frames:v", "1",
             "-vf", f"scale='min({POSTER_MAX},iw)':-2", out],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30,
        )
        return r.returncode == 0 and _ok(out)
    except Exception:
        return False


def _waveform_wav(src: str, out: str) -> bool:
    """Pure-python WAV waveform (peak buckets) rendered via PIL — no ffmpeg."""
    try:
        from PIL import Image, ImageDraw
        with wave.open(src, "rb") as w:
            n, ch, sw = w.getnframes(), w.getnchannels(), w.getsampwidth()
            raw = w.readframes(n)
        samples = array.array("h")
        samples.frombytes(raw[: len(raw) - (len(raw) % 2)])
        step = max(1, len(samples) // WAVE_BUCKETS)
        buckets = []
        for i in range(0, len(samples), step):
            chunk = samples[i:i + step]
            if chunk:
                buckets.append(max(abs(min(chunk)), abs(max(chunk))))
        if not buckets:
            return False
        peak = max(buckets) or 1
        img = Image.new("RGB", (WAVE_W, WAVE_H), (12, 12, 16))
        dr = ImageDraw.Draw(img)
        bw = WAVE_W / WAVE_BUCKETS
        for i, b in enumerate(buckets):
            h = max(2, int((b / peak) * (WAVE_H - 4)))
            x0, x1 = int(i * bw), max(int(i * bw) + 1, int((i + 1) * bw) - 1)
            dr.rectangle([x0, WAVE_H - h, x1, WAVE_H], fill=WAVE_COLOR)
        img.save(out, "PNG")
        return _ok(out)
    except Exception:
        return False


def _waveform_audio(src: str, out: str) -> bool:
    if _waveform_wav(src, out):
        return True
    ff = shutil.which("ffmpeg")
    if not ff:
        return False
    try:
        r = subprocess.run(
            [ff, "-y", "-i", src, "-filter_complex",
             f"showwavespic=s={WAVE_W}x{WAVE_H}:colors=#d4a24e", "-frames:v", "1", out],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30,
        )
        return r.returncode == 0 and _ok(out)
    except Exception:
        return False


def _metadata_preview(file_rec: dict) -> str:
    meta = {
        "filename": file_rec.get("filename"),
        "mime_type": file_rec.get("mime_type"),
        "size": file_rec.get("size"),
        "media_kind": file_rec.get("media_kind"),
    }
    return json.dumps(meta, ensure_ascii=False)


def generate_all(file_rec: dict) -> dict:
    """Generate every applicable derivative (lazy, cached). Updates + returns file_rec."""
    d = file_rec.setdefault("derivatives", {})
    for k in ("preview", "thumbnail", "proxy", "transcript", "scene_index"):
        d.setdefault(k, {"status": "NOT_GENERATED", "ref": None})

    fid = file_rec["file_id"]
    src = file_rec.get("storage_ref", "")
    kind = file_rec.get("media_kind") or kind_for(file_rec.get("filename", ""))

    if not src or not os.path.exists(src):
        _st(d, "thumbnail", "FAILED")
        _st(d, "preview", "FAILED")
        for k in ("proxy", "transcript", "scene_index"):
            _st(d, k, "UNSUPPORTED")
        return file_rec

    dd = deriv_dir(fid)

    if kind == "image":
        out = os.path.join(dd, "thumbnail.png")
        if _ok(out):
            _st(d, "thumbnail", "GENERATED", out)
        else:
            ok = _thumbnail_image(src, out)
            _st(d, "thumbnail", "GENERATED" if ok else "UNSUPPORTED", out if ok else None)
        _st(d, "preview", "GENERATED", src)  # الأصل هو المعاينة (بلا تقليل)
    elif kind == "video":
        out = os.path.join(dd, "poster.jpg")
        if _ok(out):
            _st(d, "thumbnail", "GENERATED", out)
        else:
            ok = _poster_video(src, out)
            _st(d, "thumbnail", "GENERATED" if ok else "UNSUPPORTED", out if ok else None)
    elif kind == "audio":
        out = os.path.join(dd, "waveform.png")
        if _ok(out):
            _st(d, "thumbnail", "GENERATED", out)
        else:
            ok = _waveform_audio(src, out)
            _st(d, "thumbnail", "GENERATED" if ok else "UNSUPPORTED", out if ok else None)
        pout = os.path.join(dd, "preview.json")
        if not _ok(pout):
            with open(pout, "w", encoding="utf-8") as f:
                f.write(_metadata_preview(file_rec))
        _st(d, "preview", "GENERATED", pout)
    elif kind == "document":
        out = os.path.join(dd, "preview.json")
        if not _ok(out):
            with open(out, "w", encoding="utf-8") as f:
                f.write(_metadata_preview(file_rec))
        _st(d, "preview", "GENERATED", out)
    else:
        _st(d, "thumbnail", "UNSUPPORTED")
        _st(d, "preview", "UNSUPPORTED")

    for k in ("proxy", "transcript", "scene_index"):
        _st(d, k, "UNSUPPORTED")

    # persist the updated derivatives back to the index
    files = storage.load_files()
    if fid in files:
        files[fid]["derivatives"] = d
        storage.save_files(files)
    return file_rec
