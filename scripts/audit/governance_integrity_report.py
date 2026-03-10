"""
Governance DB integrity report for audit_trail and governance_events.

The report validates row-level HMAC integrity for the governance mirror tables
and fails closed when the external integrity key is unavailable.
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
    INTEGRITY_KEY_ENV,
    REASON_KEY_MISSING,
    REASON_VALIDATION_SKIPPED,
    STATUS_OK,
    resolve_integrity_key,
    validate_row_integrity,
)

TABLES = ("audit_trail", "governance_events")


def load_rows_from_input_dir(input_dir: str) -> dict[str, list[dict[str, Any]]]:
    """Load governance table fixtures from ``<input_dir>/<table>.json`` files."""
    rows_by_table: dict[str, list[dict[str, Any]]] = {}

    for table_name in TABLES:
        path = os.path.join(input_dir, f"{table_name}.json")
        if not os.path.exists(path):
            rows_by_table[table_name] = []
            continue

        with open(path, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)

        if not isinstance(loaded, list):
            raise ValueError(f"{path} must contain a JSON array of rows")
        rows_by_table[table_name] = loaded

    return rows_by_table


def load_rows_from_postgres() -> dict[str, list[dict[str, Any]]]:
    """Load governance rows from PostgreSQL using the shared client factory."""
    import psycopg2.extras

    from core.utils.postgres_client import create_postgres_connection

    queries = {
        "audit_trail": """
            SELECT
                id,
                service_name,
                action_type,
                actor_id,
                payload,
                integrity_hash,
                integrity_algo,
                integrity_version,
                created_at
            FROM audit_trail
            ORDER BY id ASC
        """,
        "governance_events": """
            SELECT
                id,
                event_type,
                evidence_ref,
                integrity_hash,
                integrity_algo,
                integrity_version,
                created_at
            FROM governance_events
            ORDER BY id ASC
        """,
    }

    rows_by_table: dict[str, list[dict[str, Any]]] = {}
    conn = create_postgres_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for table_name, query in queries.items():
                cur.execute(query)
                rows_by_table[table_name] = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

    return rows_by_table


def build_report(
    rows_by_table: dict[str, list[dict[str, Any]]], key: str | None = None
) -> dict[str, Any]:
    """Build a deterministic report for all governance rows."""
    entries: list[dict[str, Any]] = []
    summary_by_table: dict[str, dict[str, int]] = {}
    resolved_key = resolve_integrity_key(key)

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
    key_missing = resolved_key is None or any(
        entry["reason_code"] == REASON_KEY_MISSING for entry in failed_entries
    )
    overall_reason = REASON_VALIDATION_SKIPPED if key_missing else None

    return {
        "schema": "governance.integrity_report.v1",
        "status": "PASS" if not failed_entries and not key_missing else "FAIL",
        "reason_code": overall_reason,
        "integrity_key_env": INTEGRITY_KEY_ENV,
        "tables": summary_by_table,
        "total_entries": len(entries),
        "failed_entries": len(failed_entries),
        "entries": entries,
    }


def build_verification_md(report: dict[str, Any]) -> str:
    """Build a human-readable verification report with per-entry status rows."""
    lines = [
        "# Governance Integrity Report",
        "",
        f"**Status:** {report['status']}",
        f"**Integrity key env:** `{report['integrity_key_env']}`",
    ]

    if report["reason_code"]:
        lines.append(f"**Reason code:** `{report['reason_code']}`")

    lines.extend(
        [
            "",
            "## Summary",
            "",
            "| Table | Total | OK | FAIL |",
            "|-------|-------|----|------|",
        ]
    )

    for table_name in TABLES:
        table_summary = report["tables"][table_name]
        lines.append(
            f"| `{table_name}` | {table_summary['total']} | "
            f"{table_summary['ok']} | {table_summary['fail']} |"
        )

    lines.extend(
        [
            "",
            "## Entry Status",
            "",
            "| Table | Row ID | Status | Reason | Stored Hash | Expected Hash |",
            "|-------|--------|--------|--------|-------------|---------------|",
        ]
    )

    for entry in report["entries"]:
        lines.append(
            f"| `{entry['table']}` | `{entry['row_id']}` | {entry['status']} | "
            f"`{entry['reason_code']}` | `{entry['stored_hash_prefix']}` | "
            f"`{entry['expected_hash_prefix']}` |"
        )

    lines.extend(
        [
            "",
            "---",
            "*Generated by `governance_integrity_report.py`*",
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
        rows_by_table = load_rows_from_postgres()
    elif input_dir:
        rows_by_table = load_rows_from_input_dir(input_dir)
    else:
        raise ValueError("either input_dir or from_db must be provided")

    report = build_report(rows_by_table, key=key)
    write_report_artifacts(report, out_dir)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate governance mirror row integrity and emit an audit report. "
            "Fails closed when CDB_AUDIT_INTEGRITY_KEY is missing."
        )
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--input-dir",
        help="Directory containing audit_trail.json and governance_events.json fixtures",
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
            f"PASS: validated {report['total_entries']} governance rows.",
            file=sys.stderr,
        )
        return 0

    print(
        f"FAIL: {report['failed_entries']} governance row(s) failed integrity validation.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
