#!/usr/bin/env python3
"""
Read-only contract check for the Jules AI Reviewer workflow.

This keeps the workflow comment-only on pull_request, visible via PASS/FAIL
PR comments, and prevents drift into broader permissions or hidden triggers.
"""

from __future__ import annotations

import sys
from pathlib import Path

WORKFLOW_PATH = Path(".github/workflows/ai-review-router.yml")


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path.as_posix()}")
    return path.read_text(encoding="utf-8")


def require_markers(path: Path, markers: list[str]) -> list[str]:
    text = read_text(path)
    missing = [marker for marker in markers if marker not in text]
    return [f"{path.as_posix()}: missing marker {marker!r}" for marker in missing]


def forbid_markers(path: Path, markers: list[str]) -> list[str]:
    text = read_text(path)
    present = [marker for marker in markers if marker in text]
    return [f"{path.as_posix()}: forbidden marker {marker!r}" for marker in present]


def main() -> int:
    failures: list[str] = []

    failures.extend(
        require_markers(
            WORKFLOW_PATH,
            [
                "name: Jules AI Reviewer",
                "pull_request:",
                "ready_for_review",
                "workflow_dispatch:",
                "contents: read",
                "pull-requests: read",
                "issues: write",
                "<!-- jules-ai-review -->",
                "comment-only reviewer; no approve/merge rights",
                "Fork PR detected. This workflow stays on pull_request",
                "does not use pull_request_target",
                "AI_REVIEW: PASS|FAIL",
                "Top Issues:",
            ],
        )
    )
    failures.extend(
        forbid_markers(
            WORKFLOW_PATH,
            [
                "pull_request_target:",
                "schedule:",
                "pull-requests: write",
                "contents: write",
                "author_lc=",
                "gh pr merge",
                "approve_pull_request",
            ],
        )
    )

    if failures:
        print("Jules AI Reviewer workflow drift detected:")
        for failure in failures:
            print(f"- {failure}")
        return 2

    print(f"Jules AI Reviewer workflow OK: {WORKFLOW_PATH.as_posix()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
