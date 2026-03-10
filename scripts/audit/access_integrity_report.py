"""
Access-domain DB integrity report for system_config and security_policy_refs.

The report validates row-level HMAC integrity for the access-domain mirror
tables and fails closed when the external integrity key is unavailable.
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
    ACCESS_INTEGRITY_KEY_ENV,
    REASON_VALIDATION_SKIPPED,
    STATUS_OK,
    resolve_integrity_key,
    validate_row_integrity,
)

TABLES = ("system_config", "security_policy_refs")
INPUT_FILE_CANDIDATES = {
    "system_config": ("system_config.json", "global_settings.json"),
    "security_policy_refs": ("security_policy_refs.json", "security_policies.json"),
}
DISPLAY_NAMES = {
    "system_config": "system_config",
    "security_policy_refs": "security_policies",
}
EXPECTED_COLUMNS = {
    "system_config": (
        "config_key",
        "config_scope",
        "value_ref",
        "value_hash",
        "source_path",
        "integrity_hash",
        "integrity_algo",
        "integrity_version",
        "observed_at",
    ),
    "security_policy_refs": (
        "policy_id",
        "version_hash",
        "docs_path",
        "integrity_hash",
        "integrity_algo",
        "integrity_version",
        "observed_at",
    ),
}

SCHEMA_STATUS_OK = "OK"
SCHEMA_STATUS_GAP = "GAP"
REASON_SCHEMA_GAP = "ACCESS_SCHEMA_GAP"
REASON_SCHEMA_NOT_PROVABLE = "ACCESS_SCHEMA_NOT_PROVABLE_FROM_FIXTURE"


def _display_table_name(table_name: str) -> str:
    return DISPLAY_NAMES.get(table_name, table_name)


def _load_json_array(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, list):
        raise ValueError(f"{path} must contain a JSON array of rows")
    return [dict(row) for row in loaded]


def load_rows_from_input_dir(input_dir: str) -> dict[str, list[dict[str, Any]]]:
    """Load access-domain table fixtures from JSON files in ``input_dir``."""
    rows_by_table: dict[str, list[dict[str, Any]]] = {}

    for table_name in TABLES:
        rows_by_table[table_name] = []
        for candidate in INPUT_FILE_CANDIDATES[table_name]:
            path = os.path.join(input_dir, candidate)
            if os.path.exists(path):
                rows_by_table[table_name] = _load_json_array(path)
                break

    return rows_by_table


def load_rows_from_postgres(
    schema_columns: dict[str, set[str]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Load access-domain rows from PostgreSQL using the shared client factory."""
    import psycopg2.extras

    from core.utils.postgres_client import create_postgres_connection

    queries = {
        "system_config": """
            SELECT
                config_key,
                config_scope,
                value_ref,
                value_hash,
                source_path,
                integrity_hash,
                integrity_algo,
                integrity_version,
                observed_at
            FROM system_config
            ORDER BY config_key ASC
        """,
        "security_policy_refs": """
            SELECT
                policy_id,
                version_hash,
                docs_path,
                integrity_hash,
                integrity_algo,
                integrity_version,
                observed_at
            FROM security_policy_refs
            ORDER BY policy_id ASC
        """,
    }

    rows_by_table: dict[str, list[dict[str, Any]]] = {table: [] for table in TABLES}
    conn = create_postgres_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for table_name, query in queries.items():
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                          AND table_name = %s
                    )
                    """,
                    (table_name,),
                )
                if not cur.fetchone()["exists"]:
                    continue

                present_columns = (
                    schema_columns.get(table_name) if schema_columns else None
                )
                if present_columns is not None and any(
                    column not in present_columns
                    for column in EXPECTED_COLUMNS[table_name]
                ):
                    continue

                cur.execute(query)
                rows_by_table[table_name] = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

    return rows_by_table


def load_schema_columns_from_postgres() -> dict[str, set[str]]:
    """Read actual column names for the access-domain tables from PostgreSQL."""
    import psycopg2.extras

    from core.utils.postgres_client import create_postgres_connection

    columns_by_table = {table_name: set() for table_name in TABLES}
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
                (list(TABLES),),
            )
            for row in cur.fetchall():
                columns_by_table[row["table_name"]].add(row["column_name"])
    finally:
        conn.close()

    return columns_by_table


def build_schema_checks(
    rows_by_table: dict[str, list[dict[str, Any]]],
    *,
    schema_columns: dict[str, set[str]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Describe whether required access-domain fields/columns are provably present."""
    checks: dict[str, dict[str, Any]] = {}

    for table_name in TABLES:
        expected = EXPECTED_COLUMNS[table_name]
        if schema_columns is not None:
            present = schema_columns.get(table_name, set())
            missing = [column for column in expected if column not in present]
            reason_code = None if not missing else REASON_SCHEMA_GAP
            reason = (
                "schema columns verified" if not missing else "schema columns missing"
            )
        else:
            rows = rows_by_table.get(table_name, [])
            if not rows:
                missing = list(expected)
                reason_code = REASON_SCHEMA_NOT_PROVABLE
                reason = "no fixture rows available to prove schema fields"
            else:
                missing = [
                    column
                    for column in expected
                    if any(column not in row for row in rows)
                ]
                reason_code = None if not missing else REASON_SCHEMA_GAP
                reason = (
                    "fixture fields verified"
                    if not missing
                    else "fixture rows are missing expected fields"
                )

        checks[table_name] = {
            "table": table_name,
            "display_name": _display_table_name(table_name),
            "status": SCHEMA_STATUS_OK if not missing else SCHEMA_STATUS_GAP,
            "reason_code": reason_code,
            "reason": reason,
            "missing_fields": missing,
        }

    return checks


def build_report(
    rows_by_table: dict[str, list[dict[str, Any]]],
    *,
    key: str | None = None,
    schema_columns: dict[str, set[str]] | None = None,
) -> dict[str, Any]:
    """Build a deterministic report for all access-domain rows and schema checks."""
    entries: list[dict[str, Any]] = []
    summary_by_table: dict[str, dict[str, int]] = {}
    resolved_key = resolve_integrity_key(key, env_var=ACCESS_INTEGRITY_KEY_ENV)
    schema_checks = build_schema_checks(rows_by_table, schema_columns=schema_columns)

    for table_name in TABLES:
        table_rows = rows_by_table.get(table_name, [])
        table_entries = [
            validate_row_integrity(table_name, row, key=resolved_key)
            for row in table_rows
        ]
        entries.extend(table_entries)
        summary_by_table[table_name] = {
            "total": len(table_entries),
            "ok": sum(1 for entry in table_entries if entry["status"] == STATUS_OK),
            "fail": sum(1 for entry in table_entries if entry["status"] != STATUS_OK),
        }

    failed_entries = [entry for entry in entries if entry["status"] != STATUS_OK]
    schema_gaps = [
        check for check in schema_checks.values() if check["status"] != SCHEMA_STATUS_OK
    ]
    key_missing = resolved_key is None
    overall_reason = None
    if key_missing:
        overall_reason = REASON_VALIDATION_SKIPPED
    elif schema_gaps:
        overall_reason = REASON_SCHEMA_GAP

    return {
        "schema": "governance.access_integrity_report.v1",
        "status": (
            "PASS"
            if not failed_entries and not key_missing and not schema_gaps
            else "FAIL"
        ),
        "reason_code": overall_reason,
        "integrity_key_env": ACCESS_INTEGRITY_KEY_ENV,
        "tables": summary_by_table,
        "schema_checks": schema_checks,
        "total_entries": len(entries),
        "failed_entries": len(failed_entries),
        "failed_schema_checks": len(schema_gaps),
        "entries": entries,
    }


def build_verification_md(report: dict[str, Any]) -> str:
    """Build a human-readable verification report with schema and row status."""
    lines = [
        "# Access Integrity Report",
        "",
        f"**Status:** {report['status']}",
        f"**Integrity key env:** `{report['integrity_key_env']}`",
        "**Naming note:** `security_policies` is stored as `security_policy_refs`; `global_settings` is treated as an input alias for `system_config`.",
    ]

    if report["reason_code"]:
        lines.append(f"**Reason code:** `{report['reason_code']}`")

    lines.extend(
        [
            "",
            "## Schema Checks",
            "",
            "| Table | Status | Reason | Missing Fields |",
            "|-------|--------|--------|----------------|",
        ]
    )

    for table_name in TABLES:
        schema_check = report["schema_checks"][table_name]
        missing_fields = ", ".join(
            f"`{field}`" for field in schema_check["missing_fields"]
        )
        lines.append(
            f"| `{schema_check['display_name']}` | {schema_check['status']} | "
            f"`{schema_check['reason_code'] or '-'}` | {missing_fields or '-'} |"
        )

    lines.extend(
        [
            "",
            "## Entry Status",
            "",
            "| Table | Record ID | Status | Reason | Stored Hash | Expected Hash |",
            "|-------|-----------|--------|--------|-------------|---------------|",
        ]
    )

    for entry in report["entries"]:
        record_id = entry["row_id"] if entry["row_id"] is not None else "<missing>"
        lines.append(
            f"| `{_display_table_name(entry['table'])}` | `{record_id}` | "
            f"{entry['status']} | `{entry['reason_code']}` | "
            f"`{entry['stored_hash_prefix']}` | "
            f"`{entry['expected_hash_prefix']}` |"
        )

    if not report["entries"]:
        lines.append("| `-` | `-` | - | `-` | `-` | `-` |")

    lines.extend(
        [
            "",
            "---",
            "*Generated by `access_integrity_report.py`*",
            "",
        ]
    )
    return "\n".join(lines)


def write_report_artifacts(report: dict[str, Any], out_dir: str) -> None:
    """Write report artifacts to disk."""
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(report, indent=2, sort_keys=True) + "\n")

    with open(
        os.path.join(out_dir, "verification.md"), "w", encoding="utf-8"
    ) as handle:
        handle.write(build_verification_md(report))


def generate_report(
    out_dir: str,
    input_dir: str | None = None,
    from_db: bool = False,
    key: str | None = None,
) -> dict[str, Any]:
    """Load rows, validate them, and write the evidence artifacts."""
    if from_db:
        schema_columns = load_schema_columns_from_postgres()
        rows_by_table = load_rows_from_postgres(schema_columns=schema_columns)
    elif input_dir:
        rows_by_table = load_rows_from_input_dir(input_dir)
        schema_columns = None
    else:
        raise ValueError("either input_dir or from_db must be provided")

    report = build_report(rows_by_table, key=key, schema_columns=schema_columns)
    write_report_artifacts(report, out_dir)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate access-domain mirror row integrity and emit an audit report. "
            f"Fails closed when {ACCESS_INTEGRITY_KEY_ENV} is missing."
        )
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--input-dir",
        help=(
            "Directory containing fixture files such as system_config.json, "
            "global_settings.json, security_policy_refs.json, or security_policies.json"
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
            f"PASS: validated {report['total_entries']} access-domain rows.",
            file=sys.stderr,
        )
        return 0

    print(
        "FAIL: access-domain integrity verification reported gaps or invalid rows.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
