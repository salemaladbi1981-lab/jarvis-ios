"""Project Health client plumbing regression checks."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODELS = (ROOT / "JARVIS" / "Workspace" / "WorkspaceModels.swift").read_text(encoding="utf-8")
HOME = (ROOT / "JARVIS" / "Workspace" / "HomeEntryView.swift").read_text(encoding="utf-8")

checks = []

def check(name, condition):
    checks.append((name, bool(condition)))
    print(("  PASS  " if condition else "  FAIL  ") + name)

check(
    "client decodes detailed CI identity, freshness, and per-job status",
    all(token in MODELS for token in (
        "let ciRunId: String?",
        "let ciRunNumber: String?",
        "let ciRunUrl: String?",
        "let ciBranch: String?",
        "let ciMetadataGeneratedAt: String?",
        "let ciMetadataState: String?",
        "let ciMetadataAgeSeconds: Int?",
        "let ciJobs: [String: String]?",
    )),
)

check(
    "client decodes task states, sanitized blockers, owner actions, and evidence",
    all(token in MODELS for token in (
        "let taskStates: [String: Int]?",
        "let ownerActionItems: [ProjectHealthOwnerAction]?",
        "let blockerItems: [ProjectHealthBlocker]?",
        "let evidence: [String: String]?",
    )),
)

check(
    "project health blocker model is owner-safe",
    "struct ProjectHealthBlocker: Codable" in MODELS
    and "let runUrl: String?" in MODELS
    and "let error:" not in MODELS.split("struct ProjectHealthBlocker: Codable", 1)[1].split("struct ProjectHealthOwnerAction", 1)[0],
)

owner_action_section = MODELS.split("struct ProjectHealthOwnerAction: Codable", 1)[1].split("struct ProjectHealth: Codable", 1)[0]
check(
    "owner action model cannot decode approval params or payloads",
    "params" not in owner_action_section
    and "payload" not in owner_action_section
    and "let approvalId: String?" in owner_action_section
    and "let action: String?" in owner_action_section,
)

check(
    "CI display carries run identity, failing job, and grounded build identity",
    "ciRunNumber" in MODELS
    and "failedCIJobs" in MODELS
    and 'let build = buildDisplay.map { " • \\($0)" } ?? ""' in MODELS
    and 'return "CI أخضر\\(run)\\(build)"' in MODELS
    and 'return "CI فاشل\\(run) • \\(failedJob)\\(build)"' in MODELS,
)

check(
    "CI display keeps build identity visible for stale, running, and unavailable states",
    'return "CI قديم\\(run)\\(build)"' in MODELS
    and 'return "CI يعمل\\(run)\\(build)"' in MODELS
    and 'return "CI غير متاح\\(build)"' in MODELS,
)

check(
    "CI display refuses to present stale or invalid-timestamp metadata as green",
    'metadataState == "stale"' in MODELS
    and 'return "CI قديم\\(run)\\(build)"' in MODELS
    and 'metadataState == "unknown", ciMetadataGeneratedAt?.isEmpty == false' in MODELS
    and 'return "CI غير موثوق\\(run)\\(build)"' in MODELS,
)

check(
    "build display is grounded in server-provided branch and SHA",
    "var buildDisplay: String?" in MODELS
    and "String(buildSha.prefix(8))" in MODELS
    and "ciBranch" in MODELS,
)

check(
    "production home still fetches authenticated project health instead of mock health",
    'api.getObject("project/health")' in HOME
    and "MockProjectHealth" not in HOME
    and "projectHealthCard(health)" in HOME,
)


check(
    "client uses honest legacy /health fallback when /project/health is unavailable",
    'LegacyRuntimeHealth' in MODELS
    and 'static func legacyRuntime' in MODELS
    and 'legacy_backend_fallback' in MODELS
    and 'nsError.domain == "JarvisAPI", nsError.code == 404' in HOME
    and 'api.getObject("health")' in HOME
    and 'projectHealth = .legacyRuntime(legacy)' in HOME,
)

failed = [name for name, ok in checks if not ok]
print(f"\n== RESULT: {len(checks) - len(failed)} PASS / {len(failed)} FAIL ==")
if failed:
    print("Failed checks:")
    for name in failed:
        print(" -", name)
    sys.exit(1)
