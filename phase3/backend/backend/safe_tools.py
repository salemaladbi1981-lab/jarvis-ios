"""Safe (low-risk, read-only) demo tools — explicitly marked mock/demo."""
def read_temperature(params):
    return {"reading": "22°", "unit": "celsius", "mock": True}

def read_light_state(params):
    return {"device": params.get("device", "all"), "level": "35%", "mock": True}

def get_service_health(params):
    return {"services": [{"name": "orchestrator", "status": "ok"},
                         {"name": "realtime", "status": "unavailable"}], "mock": True}

def capability_status(params):
    return {"available": ["read-temperature", "read-light-state"],
            "unavailable": ["unlock-door", "calendar-write"], "mock": True}
