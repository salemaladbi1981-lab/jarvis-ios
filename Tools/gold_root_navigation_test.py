"""Regression guard for Gold migration at the production iOS root navigation shell.

The visual change must stay token-only: real tabs, deep links and notification routing
must remain intact while the legacy blue compatibility alias is removed from RootView.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "JARVIS" / "App" / "RootView.swift").read_text(encoding="utf-8")

PASS = FAIL = 0


def check(name: str, condition: bool) -> None:
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


check(
    "production TabView uses explicit cinematic highlight gold",
    ".tint(JarvisColor.highlight_gold)" in SOURCE,
)
check(
    "RootView no longer depends on legacy blue aliases",
    "JarvisColor.primary_blue" not in SOURCE and "JarvisColor.highlight_blue" not in SOURCE,
)
check(
    "all five production tabs are preserved",
    all(label in SOURCE for label in [
        'Label("الرئيسية", systemImage: "house.fill")',
        'Label("الدردشة", systemImage: "bubble.left.and.bubble.right.fill")',
        'Label("الوارد", systemImage: "tray.fill")',
        'Label("المهام", systemImage: "checklist")',
        'Label("التسليمات", systemImage: "doc.fill")',
    ]),
)
check(
    "deep-link router and destination mapping stay wired",
    ".onOpenURL { router.handle($0) }" in SOURCE
    and "case .conversation(let id): ConversationView" in SOURCE
    and "case .task(let id): TaskDetailView" in SOURCE
    and "case .delivery(let id): DeliveryDetailView" in SOURCE,
)
check(
    "notification cold-start and warm routing stay wired",
    "NotificationManager.shared.pendingDeepLink" in SOURCE
    and ".onChange(of: NotificationManager.shared.pendingDeepLink)" in SOURCE,
)
check(
    "production enrollment-backed API construction is preserved",
    "enrollment.api ?? JarvisAPI(baseURL: JarvisConfig.baseURL" in SOURCE,
)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
