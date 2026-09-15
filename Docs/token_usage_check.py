#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Detect hard-coded approved design values in SwiftUI views.
Views must consume generated tokens (JarvisColor.*, JarvisSpacing.*, etc.),
not raw literals. Run: python3 token_usage_check.py
"""
import os, re, sys

views_dir = "JARVIS"
violations = []

# colors that have a token
token_hex = {
    "#050A12": "JarvisColor.bg_0",
    "#08101A": "JarvisColor.bg_1",
    "#8EC5FF": "JarvisColor.primary_blue",
    "#B8DFFF": "JarvisColor.highlight_blue",
    "#F5F8FF": "JarvisColor.text_primary",
    "#63D9A0": "JarvisColor.success",
    "#F0B25F": "JarvisColor.warning_demo",
    "#FF6B6B": "JarvisColor.danger",
}

for root, _, files in os.walk(views_dir):
    for f in files:
        if not f.endswith(".swift"):
            continue
        p = os.path.join(root, f)
        if "JarvisTokens.swift" in p:
            continue  # skip the token definition file itself
        s = open(p, encoding="utf-8").read()
        for hexv, token in token_hex.items():
            if f'Color(hex: "{hexv}")' in s:
                violations.append(f"{p}: {hexv} → use {token}")

print("== Hard-coded token colors in views ==")
if violations:
    for v in violations:
        print(f"  FAIL  {v}")
    print(f"\nRESULT: {len(violations)} violations")
    sys.exit(1)
else:
    print("  PASS  no hard-coded approved colors in views (all via JarvisColor)")
    print("\nRESULT: PASS")
    sys.exit(0)
