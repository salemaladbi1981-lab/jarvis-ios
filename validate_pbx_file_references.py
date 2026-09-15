#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resolve every PBXFileReference against the group hierarchy and confirm the
effective path exists on disk. Fails (non-zero) if any reference is invalid.
Run from the extracted project root (the folder containing JARVIS.xcodeproj).
"""
import os, re, sys

PBX = "JARVIS.xcodeproj/project.pbxproj"
s = open(PBX, encoding="utf-8").read()

# --- balanced-brace object parser ---
objects = {}
i = 0
head = re.compile(r'([0-9A-F]{24}) = \{')
while True:
    m = head.search(s, i)
    if not m:
        break
    uid = m.group(1)
    start = m.end()
    depth = 1
    j = start
    while depth > 0 and j < len(s):
        if s[j] == '{': depth += 1
        elif s[j] == '}': depth -= 1
        j += 1
    body = s[start:j-1]
    objects[uid] = body
    i = j

def f_str(body, name):
    mm = re.search(name + r' = "([^"]*)"', body)
    return mm.group(1) if mm else None

def f_list(body, name):
    mm = re.search(name + r' = \(([^)]*)\)', body)
    if not mm:
        return []
    return re.findall(r'([0-9A-F]{24})', mm.group(1))

# --- resolve main group ---
root = re.search(r'rootObject = ([0-9A-F]{24});', s).group(1)
main_group = f_str(objects[root], "mainGroup")

total = 0; resolved = 0; missing = []; invalid_paths = []

def walk(group_id, parts):
    global total, resolved
    body = objects[group_id]
    path = f_str(body, "path")
    newparts = list(parts)
    if path:
        newparts.append(path)
    for child in f_list(body, "children"):
        cb = objects[child]
        if '"PBXGroup"' in cb or 'PBXGroup' in cb.split(';')[0]:
            walk(child, newparts)
        elif 'PBXFileReference' in cb:
            total += 1
            st = f_str(cb, "sourceTree")
            if st == "BUILT_PRODUCTS_DIR":
                resolved += 1
                continue
            ref = f_str(cb, "path")
            if ref is None:
                missing.append("(null)")
                continue
            if "/" in ref:
                invalid_paths.append("/".join(newparts + [ref]))
                resolved += 1  # still count as checked
                continue
            full = "/".join(newparts + [ref])
            if os.path.exists(full):
                resolved += 1
            else:
                missing.append(full)

walk(main_group, [])

print(f"PBXFileReferences checked: {total}")
print(f"Resolved successfully: {resolved}")
print(f"Missing references: {len(missing)}")
print(f"Invalid group-relative paths: {len(invalid_paths)}")
for m in missing[:20]:
    print(f"  MISSING: {m}")
for p in invalid_paths[:20]:
    print(f"  INVALID: {p}")

sources_ok = s.count("PBXSourcesBuildPhase") >= 2
resources_ok = s.count("PBXResourcesBuildPhase") >= 2
test_ok = "com.apple.product-type.bundle.unit-test" in s
print(f"\nPBXSourcesBuildPhase: {'PASS' if sources_ok else 'FAIL'}")
print(f"PBXResourcesBuildPhase: {'PASS' if resources_ok else 'FAIL'}")
print(f"Test target membership: {'PASS' if test_ok else 'FAIL'}")

ok = len(missing) == 0 and len(invalid_paths) == 0 and sources_ok and resources_ok and test_ok
print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
