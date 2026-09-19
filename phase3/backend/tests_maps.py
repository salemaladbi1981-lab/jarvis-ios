"""Maps tools — deterministic tests (grounded contract, read-only)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from maps_tools import MAPS_TOOLS, execute_maps_tool

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")


class FakeMaps:
    def search(self, q):
        if not q: raise Exception("query_required")
        return {"query": q, "lat": 25.28, "lon": 51.53, "display_name": "Doha, Qatar"}
    def distance(self, o, d, mode="driving"):
        return {"origin": {"query": o}, "destination": {"query": d}, "distance_km": 10.5, "duration_minutes": 15.2, "mode": mode}
    def eta(self, o, d, mode="driving"):
        return {"origin": {"query": o}, "destination": {"query": d}, "duration_minutes": 15.2, "eta_text": "15.2 min", "mode": mode}
    def navigate(self, dest, mode="driving"):
        return {"destination": dest, "lat": 25.28, "lon": 51.53, "display_name": "Doha, Qatar",
                "maps_url": "https://www.google.com/maps/dir/?api=1&destination=25.28,51.53&travelmode=driving"}


prov = FakeMaps()

# A) الأدوات
names = [t["name"] for t in MAPS_TOOLS]
for n in ["maps_search", "maps_distance", "maps_eta", "maps_navigate"]:
    check(f"tool defined: {n}", n in names)

# B) search → lat/lon حقيقي
r = execute_maps_tool("maps_search", {"query": "Doha"}, prov)
check("search returns lat/lon", r.get("ok") and r["result"]["lat"] == 25.28)

# C) distance → distance_km + duration
r = execute_maps_tool("maps_distance", {"origin": "A", "destination": "B"}, prov)
check("distance returns km + minutes", r.get("ok") and r["result"]["distance_km"] == 10.5 and r["result"]["duration_minutes"] == 15.2)

# D) eta → eta_text
r = execute_maps_tool("maps_eta", {"origin": "A", "destination": "B"}, prov)
check("eta returns eta_text", r.get("ok") and r["result"]["eta_text"] == "15.2 min")

# E) navigate → maps_url + destination
r = execute_maps_tool("maps_navigate", {"destination": "Doha"}, prov)
check("navigate returns maps_url", r.get("ok") and r["maps_url"].startswith("https://www.google.com/maps/dir/"))
check("navigate carries destination", r["destination"] == "Doha")

# F) أداة مجهولة
r = execute_maps_tool("not_a_tool", {}, prov)
check("unknown tool → unknown_tool", r.get("ok") is False and r.get("error") == "unknown_tool")

# G) realtime.py wiring
rt = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "realtime.py"), encoding="utf-8").read()
check("realtime.py imports MAPS_TOOLS", "MAPS_TOOLS" in rt)
check("realtime.py routes maps_* calls", 'name.startswith("maps_")' in rt)
check("realtime.py sends navigation_handoff", "navigation_handoff" in rt)

# H) navigate URL: dir_action=navigate + origin غير محدد (موقع الجهاز تلقائيًا)
from maps_provider import build_navigate_url
u = build_navigate_url(25.28, 51.53, "driving")
check("navigate url has dir_action=navigate", "dir_action=navigate" in u)
check("navigate url leaves origin unset (device location)", "origin=" not in u)
check("navigate url carries destination", "destination=25.28,51.53" in u)
check("navigate url has travelmode", "travelmode=driving" in u)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
