"""Instagram Graph API provider (Meta) — read-only: profile / insights / recent media.

الـ credentials في /opt/data/.env (META_ACCESS_TOKEN + IG_USER_ID) — لا tokens في repo.
Read-only + grounded: كل نتيجة تحمل media_id حقيقي أو أرقام حقيقية من الـ API.
"""
import os, json, datetime, urllib.request, urllib.parse

BASE = "https://graph.facebook.com/v25.0"
_VALID_USER_METRICS = {
    "reach", "follower_count", "profile_views", "accounts_engaged",
    "total_interactions", "likes", "comments", "shares", "saves", "replies",
    "views", "content_views",
}


def _token():
    return os.environ.get("META_ACCESS_TOKEN", "")


def _ig_id():
    return os.environ.get("IG_USER_ID", "")


def _get(path, params):
    params["access_token"] = _token()
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())


class InstagramProvider:
    provider_name = "instagram"

    def _check(self):
        if not _token() or not _ig_id():
            raise Exception("instagram_credentials_missing")

    def profile(self):
        self._check()
        return _get(f"/{_ig_id()}", {"fields": "id,username,followers_count,media_count"})

    def insights(self, metric="reach", period="day"):
        self._check()
        metric = metric if metric in _VALID_USER_METRICS else "reach"
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        since = now - 7 * 86400
        return _get(f"/{_ig_id()}/insights",
                    {"metric": metric, "period": period, "since": since, "until": now})

    def recent_media(self, limit=5):
        self._check()
        d = _get(f"/{_ig_id()}/media",
                 {"fields": "id,caption,like_count,comments_count,timestamp,media_type",
                  "limit": min(max(int(limit or 5), 1), 25)})
        return d.get("data", [])
