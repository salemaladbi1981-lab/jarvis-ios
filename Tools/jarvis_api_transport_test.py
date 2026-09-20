"""Static regression checks for the shared JarvisAPI auth/HTTP transport contract."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
api = (root / "JARVIS/Workspace/JarvisAPI.swift").read_text(encoding="utf-8")

checks = {
    "requests are built through one authenticated path": "private func makeRequest" in api,
    "empty session fails before transport": "guard !sessionToken.isEmpty else" in api,
    "session header is centralized": 'forHTTPHeaderField: "X-Jarvis-Session"' in api,
    "workspace header is centralized": 'forHTTPHeaderField: "X-Jarvis-Workspace"' in api,
    "API requests have explicit timeout": "requestTimeout: TimeInterval = 45" in api and "req.timeoutInterval = Self.requestTimeout" in api,
    "HTTP responses use one validator": "private func validate(_ response: URLResponse)" in api,
    "validator rejects non-2xx": "guard (200..<300).contains(http.statusCode) else" in api,
    "GET validates response": "func get(_ path: String)" in api and "try validate(response)" in api,
    "download validates response before returning file": "let http = try validate(response)" in api,
    "typed array uses shared request path": "func getArray<T: Decodable>" in api and "let req = try makeRequest(path)" in api,
    "typed object uses shared request path": "func getObject<T: Decodable>" in api,
    "raw data uses shared request path": "func fetchData(_ path: String)" in api,
    "POST object uses shared request path": "func postObject<U: Decodable>" in api and 'method: "POST"' in api,
    "HTTP failures preserve JarvisAPI status-code contract": 'NSError(domain: "JarvisAPI", code: http.statusCode' in api,
}

failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(("PASS " if ok else "FAIL ") + name)
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("Failed:", ", ".join(failed))
    sys.exit(1)
