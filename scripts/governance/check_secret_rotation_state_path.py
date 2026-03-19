#!/usr/bin/env python3
"""
Read-only guard for secret rotation state path drift.

This keeps `.rotation_state.json` anchored under the canonical secrets path and
prevents a quiet fallback to the repo-local `tools/secrets/.rotation_state.json`.

Exit codes:
- 0: no drift
- 2: drift detected
- 1: execution error
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_PATH = Path("tools/secrets/Rotate-Secrets.ps1")
README_PATH = Path("tools/secrets/README.md")
EVIDENCE_PATH = Path("tools/secrets/EVIDENCE.md")
GITIGNORE_PATH = Path(".gitignore")


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
            SCRIPT_PATH,
            [
                "Rotation state: $SECRETS_PATH/.rotation_state.json",
                "$script:STATE_PATH = Join-Path $manifest.canonical_secrets_path '.rotation_state.json'",
                "$oldStatePath = Join-Path $PSScriptRoot '.rotation_state.json'",
                "Move-Item $oldStatePath $script:STATE_PATH -Force",
                "repo-local file is ignored",
            ],
        )
    )
    failures.extend(
        forbid_markers(
            SCRIPT_PATH,
            [
                "Using old state path as fallback",
                "$script:STATE_PATH = $oldStatePath",
                "Copy-Item $oldStatePath $script:STATE_PATH -Force",
            ],
        )
    )
    failures.extend(
        require_markers(
            README_PATH,
            [
                "Rotation state path:",
                "$SECRETS_PATH/.rotation_state.json",
                "tools/secrets/.rotation_state.json",
                "migration-only",
                "does not use the repo-local path as an active fallback",
            ],
        )
    )
    failures.extend(
        require_markers(
            EVIDENCE_PATH,
            [
                "$SECRETS_PATH/.rotation_state.json",
                "tools/secrets/.rotation_state.json",
                "migration-only",
                "never used as active fallback",
                "check_secret_rotation_state_path.py",
            ],
        )
    )
    failures.extend(
        require_markers(
            GITIGNORE_PATH,
            [
                "tools/secrets/.rotation_state.json",
                "$SECRETS_PATH",
            ],
        )
    )

    if failures:
        print("Secret rotation state path drift detected:")
        for failure in failures:
            print(f"- {failure}")
        return 2

    print(
        "Secret rotation state path OK: "
        f"{SCRIPT_PATH.as_posix()}, {README_PATH.as_posix()}, "
        f"{EVIDENCE_PATH.as_posix()}, {GITIGNORE_PATH.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
