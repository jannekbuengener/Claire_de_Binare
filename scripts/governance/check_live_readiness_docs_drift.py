#!/usr/bin/env python3
"""
Read-only guard for live-readiness documentation pointers.

This checker keeps the live-readiness docs honest about their canonical sources:
- README must declare the canonical sources and derived views.
- GO_NO_GO.md must remain a derived view, not a parallel state table.
- The latest LR-AUDIT-STATUS snapshot must be marked as historical.

Exit codes:
- 0: no drift
- 2: drift detected
- 1: execution error
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path("docs/live-readiness")
README_PATH = ROOT / "README.md"
GO_NO_GO_PATH = ROOT / "GO_NO_GO.md"
LR004_EVIDENCE_PATH = ROOT / "LR-004-EVIDENCE.md"
LR007_STATUS_PATH = ROOT / "LR-007-STATUS.md"
AUDIT_GLOB = "LR-AUDIT-STATUS-*.md"


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path.as_posix()}")
    return path.read_text(encoding="utf-8")


def latest_audit_snapshot(root: Path) -> Path:
    matches = sorted(root.glob(AUDIT_GLOB), key=lambda path: path.name)
    if not matches:
        raise FileNotFoundError(
            f"No audit snapshots found under {root.as_posix()}/{AUDIT_GLOB}"
        )
    return matches[-1]


def require_markers(path: Path, markers: list[str]) -> list[str]:
    text = read_text(path)
    missing = [marker for marker in markers if marker not in text]
    return [f"{path.as_posix()}: missing marker {marker!r}" for marker in missing]


def main() -> int:
    failures: list[str] = []

    failures.extend(
        require_markers(
            README_PATH,
            [
                "## Canonical Sources",
                "ROADMAP.yaml",
                "LR-TASKS.yaml",
                "LR-*-STATE.yaml",
                "## Derived Views",
                "GO_NO_GO.md",
                "LR-AUDIT-STATUS-*.md",
                "## Update Rule",
            ],
        )
    )
    failures.extend(
        require_markers(
            GO_NO_GO_PATH,
            [
                "abgeleitete Entscheidungsansicht",
                "ROADMAP.yaml",
                "LR-TASKS.yaml",
                "LR-*-STATE.yaml",
                "Do not edit task state in this file.",
            ],
        )
    )
    failures.extend(
        require_markers(
            LR004_EVIDENCE_PATH,
            [
                "Historical implementation snapshot only.",
                "Canonical task status lives in",
                "LR-004-STATE.yaml",
            ],
        )
    )
    failures.extend(
        require_markers(
            LR007_STATUS_PATH,
            [
                "Historical task snapshot only.",
                "This file is not the global live-readiness",
                "Global Verdict Source:",
                "LR-AUDIT-STATUS-*.md",
            ],
        )
    )

    audit_path = latest_audit_snapshot(ROOT)
    failures.extend(
        require_markers(
            audit_path,
            [
                "Historical snapshot only.",
                "LR-TASKS.yaml",
                "LR-*-STATE.yaml",
                "Do not edit task state here.",
            ],
        )
    )

    if failures:
        print("Live-readiness docs drift detected:")
        for failure in failures:
            print(f"- {failure}")
        return 2

    print(
        "Live-readiness docs pointers OK: "
        f"{README_PATH.as_posix()}, {GO_NO_GO_PATH.as_posix()}, "
        f"{LR004_EVIDENCE_PATH.as_posix()}, {LR007_STATUS_PATH.as_posix()}, "
        f"{audit_path.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
