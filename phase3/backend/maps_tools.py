"""Maps tools — location/place search + distance + ETA + Google Maps navigation handoff.

بنفس Grounded Tool Contract: كل نتيجة تحمل lat/lon أو مسافة/زمن حقيقيين (لا اختراع).
Read-only — التنقل handoff يفتح تطبيق الخرائط (لا تنفيذ دفع/حجز).
"""
from maps_provider import MapsProvider

MAPS_TOOLS = [
    {
        "type": "function",
        "name": "maps_search",
        "description": "Search for a place/address and get its coordinates (geocode). Returns lat, lon, display_name. Use when the user asks where a place is or for its location. Never invent coordinates.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"},
        }, "required": ["query"]},
    },
    {
        "type": "function",
        "name": "maps_distance",
        "description": "Road distance (km) and travel time (minutes) between two places. Modes: driving (default), walking, cycling. Returns distance_km + duration_minutes. Use when the user asks how far or how long between two places.",
        "parameters": {"type": "object", "properties": {
            "origin": {"type": "string"},
            "destination": {"type": "string"},
            "mode": {"type": "string", "description": "driving | walking | cycling (default driving)"},
        }, "required": ["origin", "destination"]},
    },
    {
        "type": "function",
        "name": "maps_eta",
        "description": "Estimated travel duration (ETA) between two places. Returns duration_minutes + eta_text. Use when the user asks 'how long to reach X' or the estimated arrival time.",
        "parameters": {"type": "object", "properties": {
            "origin": {"type": "string"},
            "destination": {"type": "string"},
            "mode": {"type": "string"},
        }, "required": ["origin", "destination"]},
    },
    {
        "type": "function",
        "name": "maps_navigate",
        "description": "Open Google Maps turn-by-turn navigation to a destination on the user's iPhone (navigation handoff). Returns a maps_url the device opens. Use when the user says 'navigate to X' / 'take me to X' / 'directions to X'.",
        "parameters": {"type": "object", "properties": {
            "destination": {"type": "string"},
            "mode": {"type": "string", "description": "driving (default) | walking | cycling"},
        }, "required": ["destination"]},
    },
]


def get_maps_provider():
    return MapsProvider()


def execute_maps_tool(name, args, provider=None):
    provider = provider or get_maps_provider()
    try:
        if name == "maps_search":
            return {"ok": True, "result": provider.search(args.get("query", ""))}

        if name == "maps_distance":
            r = provider.distance(args.get("origin", ""), args.get("destination", ""), args.get("mode", "driving"))
            return {"ok": True, "result": r}

        if name == "maps_eta":
            r = provider.eta(args.get("origin", ""), args.get("destination", ""), args.get("mode", "driving"))
            return {"ok": True, "result": r}

        if name == "maps_navigate":
            r = provider.navigate(args.get("destination", ""), args.get("mode", "driving"))
            return {"ok": True, "result": r, "maps_url": r["maps_url"], "destination": r["destination"]}

        return {"ok": False, "error": "unknown_tool"}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__}
