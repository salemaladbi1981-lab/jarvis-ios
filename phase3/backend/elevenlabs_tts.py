"""ElevenLabs TTS bridge — sentence-buffered → PCM 24kHz.

نستقبل مقاطع نص OpenAI المتدفّقة، نجمّعها إلى جُمَل كاملة، ونولّد كل جملة كوحدة
واحدة متماسكة عبر نقطة /stream (نفس سلوك النموذج في العيّنة أحادية النداء = صوت ثابت).
هذا يمنع «تغيّر الصوت داخل الرد» الذي يسببه البثّ على مستوى الكلمة/المقطع.

output_format=pcm_24000 → PCM16 أحادي 24kHz little-endian = ما يتوقعه VoiceAudioEngine.
stdlib فقط (urllib في خيط منفصل) — لا تبعيات جديدة.
"""
import asyncio
import json
import re
import urllib.request

import config

# مفاتيح النماذج القابلة للاختيار (؟model=) → معرّف ElevenLabs.
MODEL_MAP = {
    "multilingual": "eleven_multilingual_v2",
    "turbo": "eleven_turbo_v2_5",
    "flash": "eleven_flash_v2_5",
}
DEFAULT_MODEL = "eleven_multilingual_v2"

_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream?output_format=pcm_24000"
# فواصل الجُمَل — عربية ولاتينية (نقطة/سؤال/تعجب/فاصلة عربية/سطر جديد).
_SENT_END = re.compile(r"[\.!\?؟،؛\n]+")
# حدّ أقصى للتخزين قبل الفلش القسري (جملة طويلة بلا فاصل).
_MAX_BUF = 220


def resolve_model(key: str | None) -> str:
    if key and key in MODEL_MAP:
        return MODEL_MAP[key]
    # نقبل أيضاً معرّف ElevenLabs الخام إن مُرِّر مباشرة.
    if key and key.startswith("eleven_"):
        return key
    return config.ELEVENLABS_MODEL if getattr(config, "ELEVENLABS_MODEL", "") else DEFAULT_MODEL


def _split_sentences(buf: str):
    """يعيد (جُمَل مكتملة, البقية غير المكتملة)."""
    out = []
    while True:
        m = _SENT_END.search(buf)
        if not m:
            break
        end = m.end()
        chunk = buf[:end].strip()
        if chunk:
            out.append(chunk)
        buf = buf[end:]
    # فلش قسري لو تضخّم المخزن بلا فاصل
    if len(buf) >= _MAX_BUF:
        out.append(buf.strip())
        buf = ""
    return out, buf


class ElevenLabsStreamer:
    """جلسة TTS لرد واحد. on_audio = async callable(pcm_bytes). يجمّع جُمَلاً ويولّدها بالتتابع."""

    def __init__(self, voice_id: str, on_audio, model: str | None = None):
        self.voice_id = voice_id
        self.on_audio = on_audio
        self.model = model or DEFAULT_MODEL
        self._buf = ""
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker = None
        self._loop = None
        self._aborted = False
        self.done = asyncio.Event()

    async def start(self):
        self._loop = asyncio.get_running_loop()
        self._worker = asyncio.create_task(self._run())

    async def feed(self, text: str):
        if self._aborted or not text:
            return
        self._buf += text
        sentences, self._buf = _split_sentences(self._buf)
        for s in sentences:
            await self._queue.put(s)

    async def finish(self):
        """لا مزيد من النص — نطرد البقية ثم علامة النهاية."""
        if self._aborted:
            return
        rest = self._buf.strip()
        self._buf = ""
        if rest:
            await self._queue.put(rest)
        await self._queue.put(None)

    async def _run(self):
        try:
            while not self._aborted:
                item = await self._queue.get()
                if item is None:
                    break
                await asyncio.to_thread(self._blocking_stream, item)
        except Exception as e:
            print(f"[EL-TTS] worker crashed {type(e).__name__}: {e}", flush=True)
        finally:
            self.done.set()

    def _blocking_stream(self, text: str):
        """نداء /stream متزامن في خيط؛ يمرّر مقاطع PCM إلى on_audio على حلقة asyncio."""
        if self._aborted:
            return
        url = _TTS_URL.format(voice_id=self.voice_id)
        body = json.dumps({
            "text": text,
            "model_id": self.model,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.85,
                               "style": 0.0, "use_speaker_boost": True},
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST", headers={
            "xi-api-key": config.ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/pcm",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                total = 0
                while not self._aborted:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    total += len(chunk)
                    fut = asyncio.run_coroutine_threadsafe(self.on_audio(chunk), self._loop)
                    fut.result()  # backpressure — لا نتجاوز سرعة الإرسال للعميل
                print(f"[EL-TTS] sentence ok status={resp.status} pcm_bytes={total} text_len={len(text)}", flush=True)
        except Exception as e:
            # فشل جملة واحدة لا يُسقط بقية الرد
            print(f"[EL-TTS] sentence FAILED {type(e).__name__}: {e} (text_len={len(text)})", flush=True)

    async def wait_done(self, timeout: float | None = 30.0):
        try:
            await asyncio.wait_for(self.done.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass

    async def abort(self):
        self._aborted = True
        self.done.set()
        if self._worker:
            self._worker.cancel()

    async def close(self):
        if self._worker:
            try:
                await self._worker
            except Exception:
                pass
