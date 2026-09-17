"""Instagram tools — deterministic tests (grounded contract, read-only)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from instagram_tools import INSTAGRAM_TOOLS, execute_instagram_tool

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")


class FakeIG:
    def profile(self):
        return {"id": "17841415116553176", "username": "salem", "followers_count": 99000, "media_count": 120}
    def insights(self, metric="reach", period="day"):
        return {"data": [{"name": metric, "period": period, "values": [{"value": 5000}]}]}
    def recent_media(self, limit=5):
        return [{"id": "18000000000000001", "caption": "Hi", "like_count": 100, "comments_count": 5, "timestamp": "2026-09-01", "media_type": "IMAGE"}]


prov = FakeIG()

# A) الأدوات
names = [t["name"] for t in INSTAGRAM_TOOLS]
for n in ["instagram_profile", "instagram_insights", "instagram_recent_media"]:
    check(f"tool defined: {n}", n in names)

# B) profile → أرقام حقيقية
r = execute_instagram_tool("instagram_profile", {}, prov)
check("profile returns real data", r.get("ok") and r["profile"]["username"] == "salem" and r["profile"]["followers_count"] == 99000)
check("profile carries instagram_user_id", r["profile"].get("instagram_user_id") == "17841415116553176")

# C) insights → metric + data
r = execute_instagram_tool("instagram_insights", {"metric": "reach"}, prov)
check("insights returns data", r.get("ok") and r["metric"] == "reach" and len(r["insights"]) == 1)

# D) recent_media → media_id حقيقي
r = execute_instagram_tool("instagram_recent_media", {"limit": 3}, prov)
check("recent_media returns real media_id", r.get("ok") and r["media"][0]["media_id"] == "18000000000000001")

# E) أداة مجهولة
r = execute_instagram_tool("not_a_tool", {}, prov)
check("unknown tool → unknown_tool", r.get("ok") is False and r.get("error") == "unknown_tool")

# F) realtime.py wiring
rt = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "realtime.py"), encoding="utf-8").read()
check("realtime.py imports INSTAGRAM_TOOLS", "INSTAGRAM_TOOLS" in rt)
check("realtime.py routes instagram_* calls", 'name.startswith("instagram_")' in rt)

# G) config.py mentions instagram tools
cfg = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.py"), encoding="utf-8").read()
check("config.py mentions instagram_profile", "instagram_profile" in cfg)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
