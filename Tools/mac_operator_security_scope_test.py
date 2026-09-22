"""Regression: Mac Operator must retain the picker URL that carries security-scope provenance."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "JARVIS" / "App" / "DeepLinkTarget.swift").read_text(encoding="utf-8")

PASS = FAIL = 0


def check(name: str, condition: bool) -> None:
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


adapter = SOURCE.split("actor UserSelectedFileMacOperatorAdapter", 1)[1].split(
    "/// Permission state is obtained by the service", 1
)[0]
execute = adapter.split("func execute(_ authorization", 1)[1]

check(
    "adapter retains original user-selected URL beside exact path proof",
    "private var selectedPaths: Set<String> = []" in adapter
    and "private var selectedURLsByPath: [String: URL] = [:]" in adapter,
)

check(
    "registration keys the original picker URL by standardized exact path",
    "selectedPaths.insert(url.standardizedFileURL.path)" in adapter
    and "selectedURLsByPath[url.standardizedFileURL.path] = url" in adapter,
)

check(
    "revoking selections clears both authorization proof and retained scoped URLs",
    "selectedPaths.removeAll()" in adapter
    and "selectedURLsByPath.removeAll()" in adapter,
)

check(
    "execution requires both exact-path proof and its retained original URL",
    "let path = URL(fileURLWithPath: request.target).standardizedFileURL.path" in execute
    and "selectedPaths.contains(path)" in execute
    and "let selectedURL = selectedURLsByPath[path]" in execute,
)

check(
    "security scoped access and metadata read use retained picker URL",
    "selectedURL.startAccessingSecurityScopedResource()" in execute
    and "selectedURL.stopAccessingSecurityScopedResource()" in execute
    and "selectedURL.resourceValues(forKeys:" in execute,
)

check(
    "executor does not reconstruct a plain URL and use it as the security scoped resource",
    "let url = URL(fileURLWithPath: request.target).standardizedFileURL" not in execute
    and "url.startAccessingSecurityScopedResource()" not in execute
    and "url.resourceValues(forKeys:" not in execute,
)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
