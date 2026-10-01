"""Static regression checks for the shared JarvisAPI auth/HTTP transport contract."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
api = (root / "JARVIS/Workspace/JarvisAPI.swift").read_text(encoding="utf-8")

checks = {
    "single authenticated request path": 'func request(_ path:' in api,
    "whitespace sessions are rejected": 'guard !sessionToken.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else' in api,
    "session header centralized": 'forHTTPHeaderField: "X-Jarvis-Session"' in api,
    "workspace header centralized": 'forHTTPHeaderField: "X-Jarvis-Workspace"' in api,
    "explicit timeout": 'req.timeoutInterval = 90' in api,
    "only 2xx accepted": 'case 200..<300: return' in api,
    "typed HTTP errors": all('case '+c in api for c in ['401:', '403:', '500...599:']),
    "JSON validates response": 'try Self.validate(response)' in api,
    "failed downloads remove temporary file": 'FileManager.default.removeItem(at: url)' in api,
    "network failures are distinguished": all('.'+c in api for c in ['timedOut', 'notConnectedToInternet', 'networkConnectionLost']),
}

failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(("PASS " if ok else "FAIL ") + name)
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("Failed:", ", ".join(failed))
    sys.exit(1)
