#!/usr/bin/env python3
import os
import re
import sys

root = os.path.join(os.getcwd(), "docs")
pattern = re.compile(r"\[(.*?)\]\((.*?)\)")
broken = []

for dirpath, _, files in os.walk(root):
    for name in files:
        if not name.endswith(".md"):
            continue
        path = os.path.join(dirpath, name)
        with open(path, encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, 1):
                for _, target in pattern.findall(line):
                    if target.startswith("http"):
                        continue
                    abs_target = os.path.normpath(os.path.join(dirpath, target))
                    if not os.path.exists(abs_target):
                        broken.append((path, line_no, target, "missing"))

if broken:
    for entry in broken:
        print("BROKEN", *entry)
    sys.exit(1)

print("All links OK")
