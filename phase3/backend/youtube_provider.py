"""YouTube provider — بحث (Data API v3) + تفريغ (youtube-transcript-api).

Read-only. مفتاح الـ Data API في /opt/data/youtube_api_key.json (خارج الـ repo).
الـ transcript لا يحتاج مفتاحاً (youtube-transcript-api).
"""
import os, json, secrets, time, urllib.request, urllib.parse

YT_API_KEY = os.environ.get("YT_API_KEY", "")
YT_KEY_PATH = os.environ.get("YT_KEY_PATH", "/opt/data/youtube_api_key.json")
TRANSCRIPT_MAX = 15000  # حد أقصى لأحرف النص (حماية سياق)


def _api_key():
    if YT_API_KEY:
        return YT_API_KEY
    if os.path.exists(YT_KEY_PATH):
        d = json.load(open(YT_KEY_PATH))
        return d.get("api_key", "")
    return ""


def _get(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read())


class YouTubeProvider:
    provider_name = "youtube"

    def search(self, query, limit=5):
        key = _api_key()
        if not key:
            raise Exception("youtube_api_key_missing")
        url = "https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode({
            "part": "snippet", "q": query, "type": "video",
            "maxResults": min(limit, 20), "key": key})
        d = _get(url)
        out = []
        for item in d.get("items", []):
            vid = item.get("id", {}).get("videoId")
            if not vid:
                continue
            sn = item.get("snippet", {})
            out.append({
                "video_id": vid,
                "title": sn.get("title", ""),
                "channel": sn.get("channelTitle", ""),
                "description": (sn.get("description", "") or "")[:200],
            })
        return out

    def details(self, video_id):
        key = _api_key()
        if not key:
            raise Exception("youtube_api_key_missing")
        url = "https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode({
            "part": "snippet,contentDetails,statistics", "id": video_id, "key": key})
        d = _get(url)
        items = d.get("items", [])
        if not items:
            return None
        it = items[0]
        sn = it.get("snippet", {})
        return {
            "video_id": video_id,
            "title": sn.get("title", ""),
            "channel": sn.get("channelTitle", ""),
            "description": (sn.get("description", "") or "")[:300],
            "views": (it.get("statistics", {}) or {}).get("viewCount", ""),
            "duration": (it.get("contentDetails", {}) or {}).get("duration", ""),
        }

    def transcript(self, video_id):
        """يفرّغ الفيديو نصياً (بدون مفتاح). يعيد نصاً مقتطعاً + عدد المقاطع.

        متوافق مع youtube-transcript-api v1.x: api.fetch() يعيد snippets.
        """
        from youtube_transcript_api import YouTubeTranscriptApi
        try:
            api = YouTubeTranscriptApi()
            result = list(api.fetch(video_id))
            text = " ".join(seg.text for seg in result)
        except Exception:
            return None
        truncated = len(text) > TRANSCRIPT_MAX
        if truncated:
            text = text[:TRANSCRIPT_MAX]
        return {"video_id": video_id, "text": text, "segments": len(result), "truncated": truncated}


# --- إدخال مفتاح آمن (نموذج ويب بنافذة كود واحدة) ---
YT_INPUT_CODE_PATH = "/opt/data/yt_key_code.json"

def generate_key_code(ttl=1800):
    code = secrets.token_urlsafe(24)
    with open(YT_INPUT_CODE_PATH, "w", encoding="utf-8") as f:
        json.dump({"code": code, "expires_at": time.time() + ttl}, f)
    os.chmod(YT_INPUT_CODE_PATH, 0o600)
    return code

def consume_key_code(code):
    if not os.path.exists(YT_INPUT_CODE_PATH):
        return False
    d = json.load(open(YT_INPUT_CODE_PATH))
    if not code or d.get("code") != code:
        return False
    if time.time() > d.get("expires_at", 0):
        return False
    json.dump({"code": "", "expires_at": 0}, open(YT_INPUT_CODE_PATH, "w"))
    return True

def store_api_key(api_key):
    with open(YT_KEY_PATH, "w", encoding="utf-8") as f:
        json.dump({"api_key": api_key.strip()}, f, indent=2)
    os.chmod(YT_KEY_PATH, 0o600)
