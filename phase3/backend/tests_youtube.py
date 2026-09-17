"""YouTube tools — deterministic tests (grounded contract, read-only)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtube_tools import YOUTUBE_TOOLS, execute_youtube_tool

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")


class FakeYT:
    def __init__(self):
        self.fail = False
    def search(self, query, limit=5):
        if self.fail: raise Exception("yt_down")
        return [{"video_id": "abc123", "title": "Test video", "channel": "Chan", "description": "desc"}]
    def details(self, video_id):
        if video_id == "abc123":
            return {"video_id": "abc123", "title": "Test", "channel": "Chan", "views": "100"}
        return None
    def transcript(self, video_id):
        if video_id == "abc123":
            return {"video_id": "abc123", "text": "hello world", "segments": 2, "truncated": False}
        return None


# A) الأدوات الثلاث
names = [t["name"] for t in YOUTUBE_TOOLS]
for n in ["youtube_search", "youtube_transcript", "youtube_details"]:
    check(f"tool defined: {n}", n in names)

# B) search يتطلب query + transcript يتطلب video_id
search_tool = [t for t in YOUTUBE_TOOLS if t["name"] == "youtube_search"][0]
check("youtube_search requires 'query'", "query" in search_tool["parameters"]["required"])
tr_tool = [t for t in YOUTUBE_TOOLS if t["name"] == "youtube_transcript"][0]
check("youtube_transcript requires video_id", "video_id" in tr_tool["parameters"]["required"])

prov = FakeYT()

# C) search → videos
r = execute_youtube_tool("youtube_search", {"query": "test"}, prov)
check("search returns videos", r.get("ok") and r["videos"][0]["video_id"] == "abc123")

# D) transcript → نص حقيقي
r = execute_youtube_tool("youtube_transcript", {"video_id": "abc123"}, prov)
check("transcript returns text", r.get("ok") and r["transcript"]["text"] == "hello world")

# E) transcript غير متاح → transcript_unavailable (لا اختراع)
r = execute_youtube_tool("youtube_transcript", {"video_id": "nonexistent"}, prov)
check("transcript unavailable → transcript_unavailable", r.get("ok") is False and r.get("error") == "transcript_unavailable")

# F) details → metadata
r = execute_youtube_tool("youtube_details", {"video_id": "abc123"}, prov)
check("details returns video", r.get("ok") and r["video"]["title"] == "Test")

# G) details غير موجود → video_not_found
r = execute_youtube_tool("youtube_details", {"video_id": "nonexistent"}, prov)
check("details missing → video_not_found", r.get("ok") is False and r.get("error") == "video_not_found")

# H) أداة مجهولة
r = execute_youtube_tool("not_a_tool", {}, prov)
check("unknown tool → unknown_tool", r.get("ok") is False and r.get("error") == "unknown_tool")

# I) realtime.py wiring
rt = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "realtime.py"), encoding="utf-8").read()
check("realtime.py registers youtube tools", "YOUTUBE_TOOLS" in rt)
check("realtime.py routes youtube_* calls", 'name.startswith("youtube_")' in rt)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
