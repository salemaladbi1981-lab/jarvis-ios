#!/usr/bin/env python3
"""Regression guard: JARVIS Mac must present a normal foreground window."""
from pathlib import Path

src = Path("JARVIS/macOS/MacApp.swift").read_text(encoding="utf-8")

checks = {
    "macOS-only compilation": "#if os(macOS)" in src,
    "AppKit imported": "import AppKit" in src,
    "application delegate owns launch activation": "final class MacApplicationDelegate" in src and "applicationDidFinishLaunching" in src,
    "SwiftUI app installs delegate": "@NSApplicationDelegateAdaptor(MacApplicationDelegate.self)" in src,
    "regular activation policy": "NSApp.setActivationPolicy(.regular)" in src,
    "activation deferred until WindowGroup can create NSWindow": "DispatchQueue.main.async" in src,
    "foreground activation": "NSApp.activate(ignoringOtherApps: true)" in src,
    "key-capable window ordered front": "first(where: { $0.canBecomeKey })?.makeKeyAndOrderFront(nil)" in src,
    "activation not tied to view onAppear": ".onAppear" not in src,
    "no accessibility prompt": "AXIsProcessTrustedWithOptions" not in src,
    "no AppleEvent execution": "NSAppleScript" not in src and "AEDeterminePermissionToAutomateTarget" not in src,
}

failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if failed:
    raise SystemExit("mac window activation regression failed: " + ", ".join(failed))

print(f"mac window activation: {len(checks)}/{len(checks)} PASS")
