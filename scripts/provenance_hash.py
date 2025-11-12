#!/usr/bin/env python3
import hashlib
import os
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "."

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

for dirpath, _, files in os.walk(path):
    for f in files:
        fp = os.path.join(dirpath, f)
        print(f"{fp}\t{sha256(fp)}")
