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
from datetime import datetime
from pathlib import Path


def _timestamp_run_id() -> str:
    """Return YYYYMMDDHHMMSS using f-string formatting (no % chars)."""
    now = datetime.now()
    return (
        f"{now.year:04d}{now.month:02d}{now.day:02d}"
        f"{now.hour:02d}{now.minute:02d}{now.second:02d}"
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
