"""Maps provider — geocode (Nominatim) + routing (OSRM). stdlib only، بلا مفتاح.

location/place search + distance + ETA + Google Maps navigation URL.
Read-only + grounded: كل نتيجة تحمل lat/lon أو مسافة/زمن حقيقية من المصدر.
"""
import json, time, urllib.request, urllib.parse

USER_AGENT = "JARVIS/1.0 (contact: salem@salemai.com)"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
OSRM_BASE = "https://router.project-osrm.org/route/v1"
PROFILES = {"driving": "driving", "walking": "foot", "cycling": "bike"}
_NOMINATIM_DELAY = 1.0  # ToS: max 1 req/s


def _get(url, params=None, timeout=15):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def build_navigate_url(lat, lon, mode="driving"):
    """يبني رابط Google Maps للتنقل الفعلي (turn-by-turn).

    - origin غير محدد → تطبيق الخرائط يستخدم موقع الجهاز تلقائيًا (لا نطلب نقطة بداية).
    - dir_action=navigate → فتح ملاحة فورية، لا مجرد خريطة.
    """
    travel = "driving" if mode == "driving" else ("walking" if mode == "walking" else "bicycling")
    return (f"https://www.google.com/maps/dir/?api=1"
            f"&destination={lat},{lon}&travelmode={travel}&dir_action=navigate")


class MapsProvider:
    provider_name = "maps"

    def _geocode(self, query):
        time.sleep(_NOMINATIM_DELAY)
        d = _get(NOMINATIM, {"q": query, "format": "json", "limit": 1, "addressdetails": 1})
        if not d:
            raise Exception("place_not_found")
        r = d[0]
        return {
            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
            "display_name": r.get("display_name", query),
        }

    def search(self, query):
        if not query:
            raise Exception("query_required")
        g = self._geocode(query)
        return {"query": query, "lat": g["lat"], "lon": g["lon"],
                "display_name": g["display_name"]}

    def _route(self, origin, destination, mode):
        profile = PROFILES.get(mode, "driving")
        o = self._geocode(origin)
        d = self._geocode(destination)
        url = f"{OSRM_BASE}/{profile}/{o['lon']},{o['lat']};{d['lon']},{d['lat']}?overview=false&steps=false"
        data = _get(url)
        if data.get("code") != "Ok" or not data.get("routes"):
            raise Exception("route_unavailable")
        route = data["routes"][0]
        return {
            "origin": {"query": origin, "display_name": o["display_name"], "lat": o["lat"], "lon": o["lon"]},
            "destination": {"query": destination, "display_name": d["display_name"], "lat": d["lat"], "lon": d["lon"]},
            "distance_km": round(route.get("distance", 0) / 1000, 2),
            "duration_minutes": round(route.get("duration", 0) / 60, 1),
            "mode": mode,
        }

    def distance(self, origin, destination, mode="driving"):
        return self._route(origin, destination, mode)

    def eta(self, origin, destination, mode="driving"):
        r = self._route(origin, destination, mode)
        r["eta_text"] = f"{r['duration_minutes']} min"
        return r

    def navigate(self, destination, mode="driving"):
        """Google Maps navigation URL (يفتح تطبيق الخرائط على iPhone).
        origin غير محدد → الخرائط تستخدم موقع الجهاز؛ dir_action=navigate → ملاحة فعلية."""
        g = self._geocode(destination)
        maps_url = build_navigate_url(g["lat"], g["lon"], mode)
        return {
            "destination": destination,
            "lat": g["lat"],
            "lon": g["lon"],
            "display_name": g["display_name"],
            "maps_url": maps_url,
        }
