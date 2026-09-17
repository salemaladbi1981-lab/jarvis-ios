"""Instagram tools — read-only (profile/insights/recent media) بنفس Grounded Tool Contract.

كل نتيجة تحمل media_id أو أرقام حقيقية من Instagram Graph API (لا اختراع).
Read-only — لا confirmation ولا نشر.
"""
from instagram_provider import InstagramProvider

INSTAGRAM_TOOLS = [
    {
        "type": "function",
        "name": "instagram_profile",
        "description": "Read the owner's own Instagram Business account profile: username, followers_count, media_count. Use when the user asks about their Instagram account or follower count. Never invent numbers — return only what the API gives.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "instagram_insights",
        "description": "Read Instagram account insights (e.g. reach over the last 7 days). Valid metrics: reach, follower_count, profile_views, accounts_engaged, total_interactions, likes, comments, shares, saves, views. Use when the user asks about their reach/engagement/analytics. Never invent metrics.",
        "parameters": {"type": "object", "properties": {
            "metric": {"type": "string", "description": "insight metric (default 'reach')"},
            "period": {"type": "string", "description": "day/week (default 'day')"},
        }, "required": []},
    },
    {
        "type": "function",
        "name": "instagram_recent_media",
        "description": "List the owner's recent Instagram posts with media_id, caption, like_count, comments_count, timestamp, media_type. Use when the user asks about their latest posts. Each result carries a real media_id.",
        "parameters": {"type": "object", "properties": {
            "limit": {"type": "integer", "description": "max posts (1-25, default 5)"},
        }, "required": []},
    },
]


def get_instagram_provider():
    return InstagramProvider()


def execute_instagram_tool(name, args, provider=None):
    provider = provider or get_instagram_provider()
    try:
        if name == "instagram_profile":
            p = provider.profile()
            if not p.get("id"):
                return {"ok": False, "error": "profile_unavailable"}
            return {"ok": True, "profile": {
                "instagram_user_id": p.get("id"),
                "username": p.get("username", ""),
                "followers_count": p.get("followers_count", 0),
                "media_count": p.get("media_count", 0),
            }}

        if name == "instagram_insights":
            metric = args.get("metric", "reach")
            period = args.get("period", "day")
            d = provider.insights(metric=metric, period=period)
            data = d.get("data", [])
            if not data:
                return {"ok": False, "error": "insights_unavailable"}
            return {"ok": True, "metric": metric, "period": period, "insights": data}

        if name == "instagram_recent_media":
            items = provider.recent_media(args.get("limit", 5))
            out = []
            for it in items:
                out.append({
                    "media_id": it.get("id"),
                    "caption": (it.get("caption") or "")[:200],
                    "like_count": it.get("like_count", 0),
                    "comments_count": it.get("comments_count", 0),
                    "media_type": it.get("media_type", ""),
                    "timestamp": it.get("timestamp", ""),
                })
            return {"ok": True, "media": out}

        return {"ok": False, "error": "unknown_tool"}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__}
