"""CDB Test-First Metadata Scanner (read-only).

Scans Python test files for CDB test-first metadata blocks,
validates required fields, and outputs JSON.

Usage:
    python -m tools.test_metadata_scanner <path>...
    python -m tools.test_metadata_scanner --output <file> <path>...

Exit codes:
    0 - all blocks valid (or no blocks found)
    1 - validation errors found
    2 - usage / parse error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REQUIRED_FIELDS: list[str] = [
    "test_id",
    "test_title",
    "test_type",
    "cdb_area",
    "rule_ref",
    "decision_ref",
    "issue_ref",
    "pr_ref",
    "evidence_ref",
    "code_area",
    "security_relevant",
    "live_relevant",
    "profitability_relevant",
    "surrealdb_export",
    "ci_artifact",
]

REQUIRED_FIELD_SET: frozenset[str] = frozenset(REQUIRED_FIELDS)

BOOLEAN_FIELDS: frozenset[str] = frozenset(
    {
        "security_relevant",
        "live_relevant",
        "profitability_relevant",
        "surrealdb_export",
    }
)

FIELD_LINE_RE: re.Pattern = re.compile(r"^#\s{2,}(\w+):\s+(.+)$")


def _find_metadata_blocks(content: str) -> list[dict[str, str]]:
    """Find metadata field blocks in Python comment content.

    Looks for consecutive lines matching '#   field_name: value'
    where field_name is a known CDB metadata field.
    Groups consecutive field lines into blocks.
    """
    blocks: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in content.splitlines():
        m = FIELD_LINE_RE.match(line.strip())
        if m and m.group(1) in REQUIRED_FIELD_SET:
            current[m.group(1)] = m.group(2).strip()
        else:
            if current:
                blocks.append(current)
                current = {}
    if current:
        blocks.append(current)
    return blocks


def _coerce_bool(raw: str) -> bool:
    """Parse a string boolean value. Anything not 'true' is false."""
    return raw.strip().lower() == "true"


def _process_fields(
    raw: dict[str, str],
) -> dict[str, Any]:
    """Convert raw string fields to typed dict and validate."""
    processed: dict[str, Any] = {}
    missing: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in raw:
            missing.append(field)
            continue
        val: str = raw[field]
        if field in BOOLEAN_FIELDS:
            processed[field] = _coerce_bool(val)
        else:
            processed[field] = val
    return processed, missing


def _to_relpath(path: Path, anchor: Path | None = None) -> str:
    """Convert path to relative, or keep as simple name."""
    try:
        if anchor:
            return path.relative_to(anchor).as_posix()
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.name


def scan_file(
    path: Path,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Scan a single file for metadata blocks."""
    try:
        content: str = path.read_text(encoding="utf-8")
    except Exception as exc:
        return {
            "file": _to_relpath(path, repo_root),
            "error": f"Cannot read file: {exc}",
            "blocks": [],
        }

    raw_blocks: list[dict[str, str]] = _find_metadata_blocks(content)
    result_blocks: list[dict[str, Any]] = []
    validation_errors: list[dict[str, Any]] = []

    for raw in raw_blocks:
        processed, missing = _process_fields(raw)
        is_valid: bool = len(missing) == 0
        block: dict[str, Any] = {
            "fields": processed,
            "is_valid": is_valid,
            "surrealdb_export": processed.get("surrealdb_export", False),
        }
        if missing:
            block["missing_fields"] = missing
            validation_errors.append(
                {
                    "file": _to_relpath(path, repo_root),
                    "missing_fields": missing,
                }
            )
        result_blocks.append(block)

    return {
        "file": _to_relpath(path, repo_root),
        "blocks": result_blocks,
        "validation_errors": validation_errors,
    }


def build_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build final JSON report from scan results."""
    total_blocks: int = 0
    total_errors: int = 0
    surrealdb_ready: int = 0
    scanned_files: int = 0

    for res in results:
        if "error" not in res:
            scanned_files += 1
        total_blocks += len(res.get("blocks", []))
        total_errors += len(res.get("validation_errors", []))
        for b in res.get("blocks", []):
            if b.get("surrealdb_export"):
                surrealdb_ready += 1

    return {
        "scanner_version": "1.0.0",
        "scanned_files": scanned_files,
        "total_blocks": total_blocks,
        "total_errors": total_errors,
        "surrealdb_export_ready": surrealdb_ready,
        "results": results,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CDB Test-First Metadata Scanner (read-only)",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["tests/"],
        help="Files or directories to scan (default: tests/)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Write JSON report to file (default: stdout)",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root for relative paths in output",
    )
    return parser.parse_args(argv)


def collect_paths(patterns: list[str]) -> list[Path]:
    """Resolve file/directory patterns to Python file paths."""
    files: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        p = Path(pattern)
        if p.is_file() and p.suffix == ".py":
            resolved = p.resolve()
            if resolved not in seen:
                seen.add(resolved)
                files.append(resolved)
        elif p.is_dir():
            for child in sorted(p.rglob("*.py")):
                resolved = child.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    files.append(resolved)
        else:
            print(f"Warning: not a Python file or directory: {p}", file=sys.stderr)
    return files


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    paths: list[Path] = collect_paths(args.paths)
    if not paths:
        print("No Python files found to scan.", file=sys.stderr)
        return 2

    repo_root: Path | None = Path(args.repo_root).resolve() if args.repo_root else None

    results: list[dict[str, Any]] = []
    for path in sorted(paths):
        results.append(scan_file(path, repo_root=repo_root))

    report: dict[str, Any] = build_report(results)

    output: str = json.dumps(report, indent=2, ensure_ascii=False)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
    else:
        print(output)

    if report["total_errors"] > 0:
        return 1
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
