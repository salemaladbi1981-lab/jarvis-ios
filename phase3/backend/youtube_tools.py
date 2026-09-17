"""YouTube tools — read-only (بحث/تفريغ/تفاصيل) بنفس Grounded Tool Contract.

كل نتيجة تحمل video_id (لا اختراع فيديوهات). Read-only — لا confirmation.
"""
from youtube_provider import YouTubeProvider


YOUTUBE_TOOLS = [
    {
        "type": "function",
        "name": "youtube_search",
        "description": "Search YouTube for videos by a query. Each result carries video_id + title + channel + description. Use when the user asks to find videos or research a topic on YouTube.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "description": "max results (1-20, default 5)"},
        }, "required": ["query"]},
    },
    {
        "type": "function",
        "name": "youtube_transcript",
        "description": "Fetch the transcript (subtitles) of ONE YouTube video by video_id (from search results). Returns the full text for summarization. If no transcript is available, says so — never invents content.",
        "parameters": {"type": "object", "properties": {
            "video_id": {"type": "string", "description": "the 11-char video id from search results"},
        }, "required": ["video_id"]},
    },
    {
        "type": "function",
        "name": "youtube_details",
        "description": "Get metadata (title, channel, description, views, duration) of ONE YouTube video by video_id.",
        "parameters": {"type": "object", "properties": {
            "video_id": {"type": "string"},
        }, "required": ["video_id"]},
    },

    {
        "type": "function",
        "name": "youtube_play",
        "description": "Playback handoff: open a video in the official YouTube app on the user's iPhone. ALWAYS call youtube_search first to find a real video_id (e.g. the user says 'play the latest video from channel X'), then call youtube_play with that video_id. Returns a play_url the device opens. Do NOT call this without a real video_id from a search result.",
        "parameters": {"type": "object", "properties": {
            "video_id": {"type": "string", "description": "the 11-char video id from youtube_search results"},
        }, "required": ["video_id"]},
    },
    {
        "type": "function",
        "name": "youtube_my_channel",
        "description": "Get the user's OWN YouTube channel stats (title, subscribers, views, video count). Requires OAuth. Use when the user asks about their channel.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "youtube_my_subscriptions",
        "description": "List the channels the user is subscribed to. Requires OAuth.",
        "parameters": {"type": "object", "properties": {
            "limit": {"type": "integer"},
        }, "required": []},
    },
]


def get_youtube_provider():
    return YouTubeProvider()


def execute_youtube_tool(name, args, provider=None):
    provider = provider or get_youtube_provider()
    try:
        if name == "youtube_search":
            return {"ok": True, "videos": provider.search(args.get("query", ""), args.get("limit", 5))}

        if name == "youtube_transcript":
            vid = args.get("video_id", "")
            if not vid:
                return {"ok": False, "error": "video_id_required"}
            t = provider.transcript(vid)
            if not t:
                return {"ok": False, "error": "transcript_unavailable"}
            return {"ok": True, "transcript": t}

        if name == "youtube_details":
            vid = args.get("video_id", "")
            if not vid:
                return {"ok": False, "error": "video_id_required"}
            d = provider.details(vid)
            if not d:
                return {"ok": False, "error": "video_not_found"}
            return {"ok": True, "video": d}

        if name == "youtube_play":
            vid = args.get("video_id", "")
            if not vid:
                return {"ok": False, "error": "video_id_required"}
            title = ""
            try:
                d = provider.details(vid)
                if d:
                    title = d.get("title", "")
            except Exception:
                title = ""
            return {"ok": True, "video_id": vid, "title": title,
                    "play_url": "https://www.youtube.com/watch?v=" + vid}

        if name == "youtube_my_channel":
            import yt_channel
            ch = yt_channel.my_channel()
            if not ch:
                return {"ok": False, "error": "channel_not_found"}
            return {"ok": True, "channel": ch}

        if name == "youtube_my_subscriptions":
            import yt_channel
            return {"ok": True, "subscriptions": yt_channel.my_subscriptions(args.get("limit", 10))}

        return {"ok": False, "error": "unknown_tool"}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__}
