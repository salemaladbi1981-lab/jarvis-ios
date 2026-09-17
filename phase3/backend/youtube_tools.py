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

        return {"ok": False, "error": "unknown_tool"}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__}
