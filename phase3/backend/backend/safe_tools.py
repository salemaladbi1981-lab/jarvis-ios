"""Legacy provider seams; no fabricated device or service state."""
def read_temperature(params):
    return {"ok": False, "error": "not_connected"}

def read_light_state(params):
    return {"ok": False, "error": "not_connected"}

def get_service_health(params):
    return {"ok": False, "error": "not_connected"}

def capability_status(params):
    return {"available": [], "unavailable": ["read-temperature", "read-light-state", "unlock-door", "calendar-write"]}
