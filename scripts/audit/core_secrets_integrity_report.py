"""
Core-secrets DB integrity report for metadata-only secret mirror rows.

The report validates row-level HMAC integrity for the repo-visible core-secrets
storage and fails closed when the external integrity key is unavailable.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

if __name__ == "__main__":
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.utils.governance_integrity import (
    CORE_SECRETS_INTEGRITY_KEY_ENV,
    REASON_VALIDATION_SKIPPED,
    STATUS_OK,
    resolve_integrity_key,
    validate_row_integrity,
)

TABLE_NAME = "core_secrets_metadata"
DISPLAY_NAME = "core_secrets"
INPUT_FILE_CANDIDATES = (
    "core_secrets_metadata.json",
    "core_secrets.json",
    "service_secrets.json",
)
INPUT_FILE_TABLES = {
    "core_secrets_metadata.json": "core_secrets_metadata",
    "core_secrets.json": "core_secrets",
    "service_secrets.json": "service_secrets",
}
STORAGE_TABLE_CANDIDATES = (
    "core_secrets_metadata",
    "core_secrets",
    "service_secrets",
)
EXPECTED_COLUMNS = (
    "secret_name",
    "provider_ref",
    "fingerprint",
    "integrity_hash",
    "integrity_algo",
    "integrity_version",
    "created_at",
)

SCHEMA_STATUS_OK = "OK"
SCHEMA_STATUS_GAP = "GAP"
REASON_SCHEMA_GAP = "CORE_SECRETS_SCHEMA_GAP"
REASON_SCHEMA_NOT_PROVABLE = "CORE_SECRETS_SCHEMA_NOT_PROVABLE_FROM_FIXTURE"


def _load_json_array(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, list):
        raise ValueError(f"{path} must contain a JSON array of rows")
    return [dict(row) for row in loaded]


def load_rows_from_input_dir(input_dir: str) -> tuple[list[dict[str, Any]], str]:
    """Load core-secrets fixtures from JSON files in ``input_dir``."""
    for candidate in INPUT_FILE_CANDIDATES:
        path = os.path.join(input_dir, candidate)
        if os.path.exists(path):
            return _load_json_array(path), INPUT_FILE_TABLES[candidate]
    return [], TABLE_NAME


def _resolve_storage_table(
    schema_columns: dict[str, set[str]],
) -> tuple[str | None, set[str]]:
    for table_name in STORAGE_TABLE_CANDIDATES:
        if table_name in schema_columns:
            return table_name, schema_columns[table_name]
    return None, set()


def load_rows_from_postgres(
    schema_columns: dict[str, set[str]] | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    """Load core-secrets rows from PostgreSQL using the shared client factory."""
    import psycopg2.extras

    from core.utils.postgres_client import create_postgres_connection

    rows: list[dict[str, Any]] = []
    conn = create_postgres_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if schema_columns is None:
                schema_columns = load_schema_columns_from_postgres()
            storage_table, present_columns = _resolve_storage_table(schema_columns)
            if storage_table is None:
                return rows, None

            if any(column not in present_columns for column in EXPECTED_COLUMNS):
                return rows, storage_table

            query = (
                "SELECT "
                "secret_name, "
                "provider_ref, "
                "fingerprint, "
                "integrity_hash, "
                "integrity_algo, "
                "integrity_version, "
                "created_at "
                f"FROM {storage_table} "
                "ORDER BY secret_name ASC, created_at ASC"
            )
            cur.execute(query)
            rows = [dict(row) for row in cur.fetchall()]
            return rows, storage_table
    finally:
        conn.close()


def load_schema_columns_from_postgres() -> dict[str, set[str]]:
    """Read actual column names for core-secrets tables from PostgreSQL."""
    import psycopg2.extras

    from core.utils.postgres_client import create_postgres_connection

    columns_by_table: dict[str, set[str]] = {}
    conn = create_postgres_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = ANY(%s)
                ORDER BY table_name, ordinal_position
                """,
                (list(STORAGE_TABLE_CANDIDATES),),
            )
            for row in cur.fetchall():
                columns_by_table.setdefault(row["table_name"], set()).add(
                    row["column_name"]
                )
    finally:
        conn.close()

    return columns_by_table


def build_schema_check(
    rows: list[dict[str, Any]],
    *,
    schema_columns: dict[str, set[str]] | None = None,
    storage_table: str | None = None,
) -> dict[str, Any]:
    """Describe whether required core-secrets fields are provably present."""
    selected_table = storage_table or TABLE_NAME
    present: set[str] = set()
    if schema_columns is not None:
        resolved_table, resolved_columns = _resolve_storage_table(schema_columns)
        if resolved_table is not None:
            selected_table = resolved_table
            present = resolved_columns

    if schema_columns is not None:
        missing = [column for column in EXPECTED_COLUMNS if column not in present]
        reason_code = None if not missing else REASON_SCHEMA_GAP
        reason = "schema columns verified" if not missing else "schema columns missing"
    elif not rows:
        missing = list(EXPECTED_COLUMNS)
        reason_code = REASON_SCHEMA_NOT_PROVABLE
        reason = "no fixture rows available to prove schema fields"
    else:
        missing = [
            column
            for column in EXPECTED_COLUMNS
            if any(column not in row for row in rows)
        ]
        reason_code = None if not missing else REASON_SCHEMA_GAP
        reason = (
            "fixture fields verified"
            if not missing
            else "fixture rows are missing expected fields"
        )

    return {
        "table": TABLE_NAME,
        "display_name": DISPLAY_NAME,
        "storage_table": selected_table,
        "status": SCHEMA_STATUS_OK if not missing else SCHEMA_STATUS_GAP,
        "reason_code": reason_code,
        "reason": reason,
        "missing_fields": missing,
    }


def build_report(
    rows: list[dict[str, Any]],
    *,
    key: str | None = None,
    schema_columns: dict[str, set[str]] | None = None,
    storage_table: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic report for core-secrets integrity."""
    resolved_key = resolve_integrity_key(key, env_var=CORE_SECRETS_INTEGRITY_KEY_ENV)
    schema_check = build_schema_check(
        rows,
        schema_columns=schema_columns,
        storage_table=storage_table,
    )
    table_name = schema_check["storage_table"] or TABLE_NAME
    entries = [
        validate_row_integrity(table_name, row, key=resolved_key) for row in rows
    ]
    failed_entries = [entry for entry in entries if entry["status"] != STATUS_OK]
    schema_gap = schema_check["status"] != SCHEMA_STATUS_OK
    key_missing = resolved_key is None
    overall_reason = None
    if key_missing:
        overall_reason = REASON_VALIDATION_SKIPPED
    elif schema_gap:
        overall_reason = REASON_SCHEMA_GAP

    return {
        "schema": "governance.core_secrets_integrity_report.v1",
        "status": (
            "PASS"
            if not failed_entries and not key_missing and not schema_gap
            else "FAIL"
        ),
        "reason_code": overall_reason,
        "integrity_key_env": CORE_SECRETS_INTEGRITY_KEY_ENV,
        "table": {
            "logical_name": DISPLAY_NAME,
            "storage_table": schema_check["storage_table"],
            "total": len(entries),
            "ok": sum(1 for entry in entries if entry["status"] == STATUS_OK),
            "fail": sum(1 for entry in entries if entry["status"] != STATUS_OK),
        },
        "schema_check": schema_check,
        "total_entries": len(entries),
        "failed_entries": len(failed_entries),
        "failed_schema_checks": 0 if not schema_gap else 1,
        "entries": entries,
    }


def build_verification_md(report: dict[str, Any]) -> str:
    """Build a human-readable verification report with schema and row status."""
    lines = [
        "# Core Secrets Integrity Report",
        "",
        f"**Status:** {report['status']}",
        f"**Integrity key env:** `{report['integrity_key_env']}`",
        (
            "**Naming note:** `core_secrets` is the issue-domain name; the "
            "repo-visible Postgres storage is `core_secrets_metadata`. "
            "`service_secrets` is treated as a read-only drift alias if an "
            "environment still exposes that name. The report validates only "
            "metadata/fingerprints, never secret values."
        ),
    ]

    if report["reason_code"]:
        lines.append(f"**Reason code:** `{report['reason_code']}`")

    schema_check = report["schema_check"]
    missing_fields = ", ".join(f"`{field}`" for field in schema_check["missing_fields"])
    lines.extend(
        [
            "",
            "## Schema Check",
            "",
            "| Table | Storage | Status | Reason | Missing Fields |",
            "|-------|---------|--------|--------|----------------|",
            (
                f"| `{schema_check['display_name']}` | "
                f"`{schema_check['storage_table'] or '-'}` | "
                f"{schema_check['status']} | "
                f"`{schema_check['reason_code'] or '-'}` | "
                f"{missing_fields or '-'} |"
            ),
            "",
            "## Entry Status",
            "",
            "| Table | Record ID | Status | Reason | Stored Hash | Expected Hash |",
            "|-------|-----------|--------|--------|-------------|---------------|",
        ]
    )

    for entry in report["entries"]:
        record_id = entry.get("row_ref", "<redacted>")
        lines.append(
            f"| `{DISPLAY_NAME}` | `{record_id}` | {entry['status']} | "
            f"`{entry['reason_code']}` | `{entry['stored_hash_prefix']}` | "
            f"`{entry['expected_hash_prefix']}` |"
        )

    if not report["entries"]:
        lines.append("| `-` | `-` | - | `-` | `-` | `-` |")

    lines.extend(
        [
            "",
            "---",
            "*Generated by `core_secrets_integrity_report.py`*",
            "",
        ]
    )
    return "\n".join(lines)


def write_report_artifacts(_report: dict[str, Any], out_dir: str) -> None:
    """Write report artifacts to disk."""
    os.makedirs(out_dir, exist_ok=True)
    persisted_report = {
        "schema": "governance.core_secrets_integrity_artifact_redaction.v1",
        "artifact_mode": "fully_redacted",
        "note": "Row-level integrity data is intentionally not persisted in clear text.",
    }

    with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(persisted_report, indent=2, sort_keys=True) + "\n")

    with open(
        os.path.join(out_dir, "verification.md"), "w", encoding="utf-8"
    ) as handle:
        handle.write(
            "\n".join(
                [
                    "# Core Secrets Integrity Report",
                    "",
                    "**Artifact mode:** `fully_redacted`",
                    (
                        "**Note:** Row-level integrity data is intentionally not "
                        "persisted in clear text."
                    ),
                    "",
                    "---",
                    "*Generated by `core_secrets_integrity_report.py`*",
                    "",
                ]
            )
        )


def generate_report(
    out_dir: str,
    input_dir: str | None = None,
    from_db: bool = False,
    key: str | None = None,
) -> dict[str, Any]:
    """Load rows, validate them, and write the evidence artifacts."""
    if from_db:
        schema_columns = load_schema_columns_from_postgres()
        rows, storage_table = load_rows_from_postgres(schema_columns=schema_columns)
    elif input_dir:
        rows, storage_table = load_rows_from_input_dir(input_dir)
        schema_columns = None
    else:
        raise ValueError("either input_dir or from_db must be provided")

    report = build_report(
        rows,
        key=key,
        schema_columns=schema_columns,
        storage_table=storage_table,
    )
    write_report_artifacts(report, out_dir)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate core-secrets metadata integrity and emit an audit report. "
            f"Fails closed when {CORE_SECRETS_INTEGRITY_KEY_ENV} is missing."
        )
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--input-dir",
        help=(
            "Directory containing fixture files such as core_secrets_metadata.json, "
            "core_secrets.json, or service_secrets.json"
        ),
    )
    source_group.add_argument(
        "--from-db",
        action="store_true",
        help="Load rows directly from PostgreSQL using POSTGRES_* environment variables",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Directory for report artifacts",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on PASS and 1 on FAIL."""
    args = build_arg_parser().parse_args(argv)
    report = generate_report(
        out_dir=args.out_dir,
        input_dir=args.input_dir,
        from_db=args.from_db,
    )

    if report["status"] == "PASS":
        print(
            "PASS: core-secrets integrity verification completed.",
            file=sys.stderr,
        )
        return 0

    print(
        "FAIL: core-secrets integrity verification reported gaps or invalid rows.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
