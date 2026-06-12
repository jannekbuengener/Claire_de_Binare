#!/usr/bin/env python3
"""CLI gate for evidence_class metadata validation.

Scans JSON artifact files for valid evidence_class metadata.
Exit code 0 = all passed, 1 = failures found.

Usage:
    python tools/validate_evidence_class.py <path> [<path> ...]
    python tools/validate_evidence_class.py --dir <directory> [--recursive]

Forward-only: does not require historical artifacts to have evidence_class.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.utils.evidence_class import (
    EvidenceClassError,
    validate_evidence_class,
)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Validate evidence_class metadata on ARVP evidence artifacts."
    )
    p.add_argument("paths", nargs="*", type=Path, help="JSON artifact file paths.")
    p.add_argument(
        "--dir",
        type=Path,
        help="Scan a directory for JSON artifacts.",
    )
    p.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively scan --dir.",
    )
    p.add_argument(
        "--forward-only",
        action="store_true",
        default=True,
        help="Forward-only mode: missing evidence_class is a warning, not a failure (default).",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        default=False,
        help="Strict mode: missing evidence_class is a failure.",
    )
    return p.parse_args(argv)


def _scan_dir(directory: Path, recursive: bool) -> list[Path]:
    pattern = "**/*.json" if recursive else "*.json"
    return sorted(directory.glob(pattern))


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    files: list[Path] = list(args.paths)
    if args.dir:
        files.extend(_scan_dir(args.dir, args.recursive))

    if not files:
        print("No files to validate.", file=sys.stderr)
        return 0

    failures: list[str] = []
    warnings: list[str] = []
    passed = 0

    for path in files:
        if not path.is_file():
            failures.append(f"{path}: not a file")
            continue

        try:
            raw = path.read_text(encoding="utf-8")
            artifact = json.loads(raw)
        except (json.JSONDecodeError, OSError) as exc:
            failures.append(f"{path}: cannot read/parse: {exc}")
            continue

        if not isinstance(artifact, dict):
            failures.append(f"{path}: JSON root is not a dict")
            continue

        if "evidence_class" not in artifact:
            if args.strict:
                failures.append(f"{path}: missing evidence_class")
            else:
                warnings.append(f"{path}: missing evidence_class (forward-only, skipped)")
            continue

        try:
            validate_evidence_class(artifact)
            passed += 1
        except EvidenceClassError as exc:
            failures.append(f"{path}: {exc}")

    print(f"Validated: {passed} passed, {len(failures)} failed, {len(warnings)} warnings")

    for w in warnings:
        print(f"  WARNING: {w}")

    if failures:
        for f in failures:
            print(f"  FAIL: {f}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
