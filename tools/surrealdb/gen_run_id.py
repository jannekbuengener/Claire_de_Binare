"""Portable run-id generator for Makefile ``$(shell ...)`` use.

Usage (no arguments):
    python tools/surrealdb/gen_run_id.py
    → prints a YYYYMMDDHHMMSS timestamp.
      Uses integer formatting, not strftime % codes, so cmd.exe cannot
      misinterpret the output as environment-variable references.

Usage (one argument — path to snapshot.json):
    python tools/surrealdb/gen_run_id.py artifacts/context-intelligence/latest/snapshot.json
    → prints the ``run_id`` field from snapshot.json.

Both modes print exactly one line with no trailing whitespace beyond the newline,
making them safe for ``$(shell ...)`` capture in GNU Make.

Issue: #2587
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path


def _timestamp_run_id() -> str:
    """Return YYYYMMDDHHMMSS using f-string formatting (no % chars)."""
    t = time.localtime()
    return (
        f"{t.tm_year:04d}{t.tm_mon:02d}{t.tm_mday:02d}"
        f"{t.tm_hour:02d}{t.tm_min:02d}{t.tm_sec:02d}"
    )


def _run_id_from_snapshot(snapshot_path: str) -> str:
    """Read run_id from a snapshot.json produced by context_indexer."""
    data = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    return str(data["run_id"])


def main() -> None:
    if len(sys.argv) >= 2:
        print(_run_id_from_snapshot(sys.argv[1]))
    else:
        print(_timestamp_run_id())


if __name__ == "__main__":
    main()
