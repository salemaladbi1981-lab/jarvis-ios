"""Static regression checks for native enrollment/session transport stability."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
enrollment = (root / "JARVIS/Auth/EnrollmentManager.swift").read_text(encoding="utf-8")
keychain = (root / "JARVIS/Auth/KeychainStore.swift").read_text(encoding="utf-8")

checks = {
    "enrollment has explicit timeout": "req.timeoutInterval = 30" in enrollment,
    "enrollment validates HTTP response": "guard let http = resp as? HTTPURLResponse" in enrollment,
    "enrollment distinguishes HTTP status": "enrollmentMessage(forHTTPStatus:" in enrollment,
    "enrollment distinguishes offline": ".notConnectedToInternet" in enrollment,
    "enrollment distinguishes timeout": ".timedOut" in enrollment,
    "enrollment distinguishes network loss": ".networkConnectionLost" in enrollment,
    "enrollment rejects empty returned token": "!token.isEmpty" in enrollment,
    "successful enrollment clears stale error": "error = nil\n            return true" in enrollment,
    "keychain save reports result": "static func save(_ value: String) -> Bool" in keychain,
    "keychain save verifies SecItemAdd": "SecItemAdd(attrs as CFDictionary, nil) == errSecSuccess" in keychain,
    "enrollment refuses success when keychain persistence fails": "guard KeychainStore.save(token) else" in enrollment,
}

failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(("PASS " if ok else "FAIL ") + name)
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("Failed:", ", ".join(failed))
    sys.exit(1)
