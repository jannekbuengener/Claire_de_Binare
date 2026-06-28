"""CDB Test-First Metadata Import Bundle Builder (read-only).

Transforms scanner JSON output into a deterministic, SurrealDB-ready
import bundle. Only blocks with is_valid=true and surrealdb_export=true
are included.

This tool is read-only: it never connects to SurrealDB, never executes
SurrealQL, and never opens a database connection.

Usage:
    python -m tools.test_metadata_import_bundle <scanner-report.json>
    python -m tools.test_metadata_import_bundle --stdin < scanner-report.json
    python -m tools.test_metadata_import_bundle --output <bundle.json> <scanner-report.json>

Exit codes:
    0 - valid bundle produced
    1 - no exportable blocks or validation errors
    2 - parse / usage error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from core.replay.canonical_json import canonical_hash

SCHEMA_VERSION = "test-metadata-import-bundle/v1"
SOURCE_SCANNER = "test_metadata_scanner/v1.0.0"
RECORD_TYPE = "test_case"

PILOT_ID_RE = re.compile(r"cdb-test-pilot-(\d+)", re.IGNORECASE)
ABSOLUTE_PATH_RE = re.compile(r"^[a-zA-Z]:[/\\]|^/")


def _derive_pilot_id(test_id: str) -> str:
    m = PILOT_ID_RE.match(test_id)
    if m:
        return f"CDB-PILOT-{m.group(1)}"
    return ""


def _to_relpath_posix(file_value: str) -> str:
    cleaned = file_value.strip().replace("\\", "/")
    if ABSOLUTE_PATH_RE.match(cleaned):
        raise ValueError(f"Absolute path rejected: {file_value}")
    return cleaned


def _build_record_id(source_file: str, test_id: str) -> str:
    stable_input = f"{source_file}|{test_id}"
    h = canonical_hash(stable_input)
    return f"{RECORD_TYPE}:{h[:24]}"


def _build_content_hash(record: dict[str, Any]) -> str:
    hash_payload = {
        k: v for k, v in record.items()
        if k not in ("record_id", "content_hash")
    }
    return canonical_hash(hash_payload)


def _build_record(source_file: str, block: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = block.get("fields", {})
    test_id: str = fields.get("test_id", "")
    test_type: str = fields.get("test_type", "")
    ci_artifact: str = fields.get("ci_artifact", "")
    pilot_id: str = _derive_pilot_id(test_id)

    record = {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "source_file": source_file,
        "pilot_id": pilot_id,
        "test_id": test_id,
        "test_type": test_type,
        "ci_artifact": ci_artifact,
        "surrealdb_export": True,
        "metadata": dict(fields),
        "source_scanner": SOURCE_SCANNER,
        "limitations": [],
    }

    record["record_id"] = _build_record_id(source_file, test_id)
    record["content_hash"] = _build_content_hash(record)

    return record


def load_scanner_report(input_data: str) -> dict[str, Any]:
    try:
        report = json.loads(input_data)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid scanner JSON: {exc}") from exc

    if not isinstance(report, dict):
        raise ValueError("Scanner report must be a JSON object")

    results = report.get("results")
    if not isinstance(results, list):
        raise ValueError("Scanner report missing 'results' list")

    return report


def build_bundle(report: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = report.get("results", [])

    for result in results:
        source_file: str = result.get("file", "")
        try:
            source_file = _to_relpath_posix(source_file)
        except ValueError:
            continue

        blocks: list[dict[str, Any]] = result.get("blocks", [])
        for block in blocks:
            is_valid: bool = block.get("is_valid", False)
            surrealdb_export: bool = block.get("surrealdb_export", False)
            if is_valid and surrealdb_export:
                try:
                    record = _build_record(source_file, block)
                    records.append(record)
                except (ValueError, KeyError):
                    continue

    records.sort(key=lambda r: (r.get("source_file", ""), r.get("test_id", ""), r.get("record_id", "")))

    return records


def validate_records(records: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_record_ids: set[str] = set()

    for i, record in enumerate(records):
        rid = record.get("record_id", "")
        if rid in seen_record_ids:
            errors.append(f"records[{i}]: duplicate record_id: {rid}")
        seen_record_ids.add(rid)

        source_file = record.get("source_file", "")
        if ABSOLUTE_PATH_RE.match(source_file.replace("\\", "/")):
            errors.append(f"records[{i}]: absolute path in source_file: {source_file}")

    return errors


def write_bundle(records: list[dict[str, Any]]) -> str:
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "source_scanner": SOURCE_SCANNER,
        "record_count": len(records),
        "records": records,
    }
    return json.dumps(bundle, indent=2, ensure_ascii=False, sort_keys=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CDB Test-First Metadata Import Bundle Builder (read-only)",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Scanner JSON file path, or '-' for stdin (default: '-')",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Write bundle JSON to file (default: stdout)",
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.input == "-":
        input_data = sys.stdin.read()
    else:
        input_path = Path(args.input)
        if not input_path.is_file():
            print(f"Error: file not found: {args.input}", file=sys.stderr)
            return 2
        try:
            input_data = input_path.read_text(encoding="utf-8")
        except Exception as exc:
            print(f"Error: cannot read input: {exc}", file=sys.stderr)
            return 2

    try:
        report = load_scanner_report(input_data)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    records = build_bundle(report)

    if not records:
        print("No exportable blocks found.", file=sys.stderr)
        return 1

    errors = validate_records(records)
    if errors:
        for err in errors:
            print(f"Validation error: {err}", file=sys.stderr)
        return 1

    output = write_bundle(records)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
    else:
        print(output)

    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
