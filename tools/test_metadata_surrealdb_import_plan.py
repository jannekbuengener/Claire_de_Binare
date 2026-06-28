"""CDB Test-First Metadata SurrealDB Import Plan Builder (dry-run, read-only).

Translates an Import Bundle v1 into a deterministic dry-run SurrealDB
import plan. No SurrealDB connection, no SurrealQL, no write of any kind.

Usage:
    python -m tools.test_metadata_surrealdb_import_plan <bundle.json>
    python -m tools.test_metadata_surrealdb_import_plan --stdin < bundle.json
    python -m tools.test_metadata_surrealdb_import_plan --output <plan.json> <bundle.json>

Exit codes:
    0 - valid dry-run plan produced
    1 - no importable records / contract validation error
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

PLAN_SCHEMA_VERSION = "test-metadata-surrealdb-import-plan/v1"
BUNDLE_SCHEMA_VERSION = "test-metadata-import-bundle/v1"
PLAN_TYPE = "upsert_dry_run"
TARGET_TABLE = "test_case"

ABSOLUTE_PATH_RE = re.compile(r"^[a-zA-Z]:[/\\]|^/")


def _check_absolute_path(value: str) -> bool:
    cleaned = value.strip().replace("\\", "/")
    return bool(ABSOLUTE_PATH_RE.match(cleaned))


def _build_operation(record: dict[str, Any]) -> dict[str, Any]:
    target_id: str = record.get("record_id", "")
    content_hash: str = record.get("content_hash", "")

    record_payload: dict[str, Any] = {
        "source_file": record.get("source_file", ""),
        "pilot_id": record.get("pilot_id", ""),
        "test_id": record.get("test_id", ""),
        "test_type": record.get("test_type", ""),
        "ci_artifact": record.get("ci_artifact", ""),
        "surrealdb_export": record.get("surrealdb_export", False),
    }

    metadata = record.get("metadata")
    if isinstance(metadata, dict):
        record_payload.update(metadata)

    limitations: list[str] = list(record.get("limitations", []))

    return {
        "operation": PLAN_TYPE,
        "target_table": TARGET_TABLE,
        "target_id": target_id,
        "record": record_payload,
        "content_hash": content_hash,
        "source_bundle_record_id": target_id,
        "limitations": limitations,
    }


def load_bundle(input_data: str) -> dict[str, Any]:
    try:
        bundle = json.loads(input_data)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid bundle JSON: {exc}") from exc

    if not isinstance(bundle, dict):
        raise ValueError("Bundle must be a JSON object")

    records = bundle.get("records")
    if not isinstance(records, list):
        raise ValueError("Bundle missing 'records' list")

    return bundle


def validate_bundle_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for field in (
        "record_id",
        "content_hash",
        "test_id",
        "ci_artifact",
        "surrealdb_export",
    ):
        if field not in record:
            errors.append(f"Record missing required field: {field}")

    ci_artifact = record.get("ci_artifact")
    if ci_artifact is not None and not isinstance(ci_artifact, str):
        errors.append(f"ci_artifact must be a string, got {type(ci_artifact).__name__}")

    source_file = record.get("source_file", "")
    if _check_absolute_path(source_file):
        errors.append(f"Absolute path in source_file: {source_file}")

    return errors


def build_plan(
    bundle: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str], list[str], str]:
    records: list[dict[str, Any]] = bundle.get("records", [])
    operations: list[dict[str, Any]] = []
    warnings: list[str] = []
    global_limitations: list[str] = []

    sorted_records = sorted(
        records,
        key=lambda r: (
            r.get("source_file", ""),
            r.get("test_id", ""),
            r.get("record_id", ""),
        ),
    )

    for record in sorted_records:
        validation_errors = validate_bundle_record(record)
        if validation_errors:
            rid = record.get("record_id", "<unknown>")
            for err in validation_errors:
                warnings.append(f"[{rid}] {err}")
            continue

        pilot_id = record.get("pilot_id", "")
        if not pilot_id:
            rid = record.get("record_id", "")
            warnings.append(f"[{rid}] empty_pilot_id")
            limitation = "pilot_id: not derivable from test_id (expected cdb-test-pilot-NNN pattern)"
            record_limitations: list[str] = list(record.get("limitations", []))
            if limitation not in record_limitations:
                record_limitations.append(limitation)
            record["limitations"] = record_limitations

        operation = _build_operation(record)
        operations.append(operation)

    target_ids = sorted(op["target_id"] for op in operations)
    fingerprint_input = PLAN_SCHEMA_VERSION + "," + ",".join(target_ids)
    bundle_fingerprint = canonical_hash(fingerprint_input)

    return operations, warnings, global_limitations, bundle_fingerprint


def format_warning(w: str) -> str:
    if w.startswith("["):
        return w
    return f"[plan] {w}"


def write_plan(
    operations: list[dict[str, Any]],
    warnings: list[str],
    limitations: list[str],
    bundle_fingerprint: str,
) -> str:
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "source_bundle_schema": BUNDLE_SCHEMA_VERSION,
        "plan_type": PLAN_TYPE,
        "operation_count": len(operations),
        "dry_run": True,
        "surrealdb_write": False,
        "bundle_fingerprint": bundle_fingerprint,
        "warnings": [format_warning(w) for w in warnings],
        "limitations": limitations,
        "operations": operations,
    }
    return json.dumps(plan, indent=2, ensure_ascii=False, sort_keys=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CDB Test-First Metadata SurrealDB Import Plan Builder (dry-run, read-only)",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Bundle JSON file path, or '-' for stdin (default: '-')",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Write plan JSON to file (default: stdout)",
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
        bundle = load_bundle(input_data)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    result = build_plan(bundle)
    operations, warnings, limitations, bundle_fingerprint = result

    if not operations:
        for w in warnings:
            print(f"Warning: {w}", file=sys.stderr)
        print("No importable records found.", file=sys.stderr)
        return 1

    output = write_plan(operations, warnings, limitations, bundle_fingerprint)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
    else:
        print(output)

    if warnings:
        for w in warnings:
            print(f"Warning: {w}", file=sys.stderr)

    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
