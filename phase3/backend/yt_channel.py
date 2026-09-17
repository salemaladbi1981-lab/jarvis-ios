"""YouTube channel (OAuth) — قراءة قناة المالك + الاشتراكات للـ personalization."""
import json, urllib.request, urllib.parse
import yt_oauth


def _get(path, params=None):
    token = yt_oauth._token()
    if not token:
        raise Exception("youtube_oauth_missing")
    url = "https://www.googleapis.com/youtube/v3/" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def my_channel():
    """قناة المالك: الاسم + المشتركين + المشاهدات + عدد الفيديوهات."""
    d = _get("channels", {"part": "snippet,statistics,contentDetails", "mine": "true"})
    items = d.get("items", [])
    if not items:
        return None
    it = items[0]
    sn = it.get("snippet", {})
    st = it.get("statistics", {})
    return {
        "channel_id": it.get("id", ""),
        "title": sn.get("title", ""),
        "description": (sn.get("description", "") or "")[:200],
        "subscribers": st.get("subscriberCount", "0"),
        "views": st.get("viewCount", "0"),
        "video_count": st.get("videoCount", "0"),
    }


def my_subscriptions(limit=10):
    """أحدث الاشتراكات (القنوات التي يتابعها المالك)."""
    d = _get("subscriptions", {"part": "snippet", "mine": "true", "maxResults": min(limit, 20),
                               "order": "relevance"})
    out = []
    for it in d.get("items", []):
        sn = it.get("snippet", {})
        out.append({
            "channel_id": sn.get("resourceId", {}).get("channelId", ""),
            "title": sn.get("title", ""),
        })
    return out
