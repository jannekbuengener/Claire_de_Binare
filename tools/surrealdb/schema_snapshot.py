"""Deterministic SurrealDB schema snapshot — repo-backed, no DB connection.

Parses a .surql file, extracts canonical DEFINE TABLE / FIELD / INDEX
statements, and produces a deterministic schema snapshot.

The snapshot hash is computed ONLY over canonical schema definitions
(sorted table/field/index lines).  The ``generated_at`` metadata field
is wall-clock only and does NOT affect ``schema_hash``.

Usage:
    python tools/surrealdb/schema_snapshot.py \\
        --surql-path infrastructure/surrealdb/context_intelligence_v0.surql

    python tools/surrealdb/schema_snapshot.py \\
        --surql-path infrastructure/surrealdb/context_intelligence_v0.surql \\
        --check-baseline \\
        --baseline-path infrastructure/surrealdb/schema_baseline.json

    python tools/surrealdb/schema_snapshot.py \\
        --surql-path infrastructure/surrealdb/context_intelligence_v0_deploy.surql \\
        --fixed-generated-at "2026-01-01T00:00:00Z"

Guardrails:
    - No DB connection (repo-backed, deterministic)
    - generated_at does NOT influence schema_hash
    - --check-baseline exits 1 on mismatch (fail-closed)
    - LR / Live / Echtgeld: NO-GO (this tool has no runtime effect)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RE_TABLE_SCHEMAFULL = re.compile(
    r"^\s*DEFINE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\S+)\s+SCHEMAFULL", re.IGNORECASE
)
RE_TABLE_RELATION = re.compile(
    r"^\s*DEFINE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\S+)\s+TYPE\s+RELATION",
    re.IGNORECASE,
)
RE_FIELD = re.compile(r"^\s*DEFINE\s+FIELD\s+(\S+)\s+ON\s+TABLE\s+(\S+)", re.IGNORECASE)
RE_INDEX = re.compile(
    r"^\s*DEFINE\s+INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?(\S+)\s+ON\s+TABLE\s+(\S+)",
    re.IGNORECASE,
)
RE_ANALYZER = re.compile(
    r"^\s*DEFINE\s+ANALYZER\s+(?:IF\s+NOT\s+EXISTS\s+)?(\S+)", re.IGNORECASE
)
RE_COMMENT_OR_BLANK = re.compile(r"^\s*(--|$)")


def parse_surql(path: Path) -> dict[str, Any]:
    """Parse a .surql file and return canonical schema definitions.

    Returns a dict with:
        tables: sorted list of table names
        fields: list of {"field": str, "table": str} sorted by (table, field)
        indexes: list of {"index": str, "table": str} sorted by (table, index)
        analyzers: sorted list of analyzer names
        raw_define_lines: sorted list of all DEFINE TABLE/FIELD/INDEX lines
    """
    tables: list[str] = []
    relation_tables: list[str] = []
    fields: list[dict[str, str]] = []
    indexes: list[dict[str, str]] = []
    analyzers: list[str] = []
    define_lines: list[str] = []

    text = path.read_text(encoding="utf-8")

    for line in text.splitlines():
        if RE_COMMENT_OR_BLANK.match(line):
            continue
        stripped = line.strip()

        m = RE_TABLE_RELATION.match(stripped)
        if m:
            tables.append(m.group(1))
            relation_tables.append(m.group(1))
            define_lines.append(stripped)
            continue

        m = RE_TABLE_SCHEMAFULL.match(stripped)
        if m:
            tables.append(m.group(1))
            define_lines.append(stripped)
            continue

        m = RE_FIELD.match(stripped)
        if m:
            fields.append({"field": m.group(1), "table": m.group(2)})
            define_lines.append(stripped)
            continue

        m = RE_INDEX.match(stripped)
        if m:
            indexes.append({"index": m.group(1), "table": m.group(2)})
            define_lines.append(stripped)
            continue

        m = RE_ANALYZER.match(stripped)
        if m:
            analyzers.append(m.group(1))
            continue

    relation_set = set(relation_tables)
    table_types: dict[str, str] = {}
    for t in tables:
        table_types[t] = "TYPE_RELATION" if t in relation_set else "SCHEMAFULL"

    return {
        "tables": sorted(tables),
        "relation_tables": sorted(relation_tables),
        "table_types": table_types,
        "fields": sorted(fields, key=lambda x: (x["table"], x["field"])),
        "indexes": sorted(indexes, key=lambda x: (x["table"], x["index"])),
        "analyzers": sorted(analyzers),
        "raw_define_lines": sorted(define_lines),
    }


def compute_schema_hash(canonical: dict[str, Any]) -> str:
    """Compute a deterministic SHA256 hash over canonical schema definitions.

    generated_at is NOT included in the hash input.
    """
    canonical_str = json.dumps(
        {
            "tables": canonical["tables"],
            "relation_tables": canonical["relation_tables"],
            "fields": canonical["fields"],
            "indexes": canonical["indexes"],
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


def build_snapshot(
    surql_path: Path,
    fixed_generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a full snapshot dict from a .surql file."""
    canonical = parse_surql(surql_path)
    schema_hash = compute_schema_hash(canonical)

    if fixed_generated_at is not None:
        generated_at = fixed_generated_at
    else:
        generated_at = datetime.now(timezone.utc).isoformat()

    return {
        "source_file": str(surql_path.resolve()),
        "generated_at": generated_at,
        "schema_hash": schema_hash,
        "table_count": len(canonical["tables"]),
        "relation_table_count": len(canonical["relation_tables"]),
        "field_count": len(canonical["fields"]),
        "index_count": len(canonical["indexes"]),
        "analyzer_count": len(canonical["analyzers"]),
        "tables": canonical["tables"],
        "relation_tables": canonical["relation_tables"],
        "fields": canonical["fields"],
        "indexes": canonical["indexes"],
        "analyzers": canonical["analyzers"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="CDB SurrealDB schema snapshot tool")
    parser.add_argument(
        "--surql-path",
        type=str,
        default="infrastructure/surrealdb/context_intelligence_v0.surql",
        help="Path to .surql file (default: context_intelligence_v0.surql)",
    )
    parser.add_argument(
        "--fixed-generated-at",
        type=str,
        default=None,
        help="Fixed ISO-8601 timestamp for deterministic testing",
    )
    parser.add_argument(
        "--check-baseline",
        action="store_true",
        default=False,
        help="Exit 1 if schema_hash differs from baseline",
    )
    parser.add_argument(
        "--baseline-path",
        type=str,
        default="infrastructure/surrealdb/schema_baseline.json",
        help="Path to baseline JSON file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Write snapshot JSON to file (default: stdout)",
    )

    args = parser.parse_args()
    surql_path = Path(args.surql_path)

    if not surql_path.exists():
        print(f"ERROR: File not found: {surql_path}", file=sys.stderr)
        sys.exit(1)

    snapshot = build_snapshot(
        surql_path=surql_path,
        fixed_generated_at=args.fixed_generated_at,
    )

    snapshot_json = json.dumps(snapshot, indent=2, ensure_ascii=False, default=str)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(snapshot_json, encoding="utf-8")
        print(f"Snapshot written to {out_path}")
    else:
        print(snapshot_json)

    if args.check_baseline:
        baseline_path = Path(args.baseline_path)
        if not baseline_path.exists():
            print(
                f"ERROR: Baseline file not found: {baseline_path}",
                file=sys.stderr,
            )
            print("  Run without --check-baseline to generate baseline first.")
            sys.exit(1)

        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        current_hash = snapshot["schema_hash"]
        baseline_hash = baseline["schema_hash"]

        if current_hash != baseline_hash:
            print(
                f"SCHEMA DRIFT DETECTED: hash={current_hash} "
                f"!= baseline={baseline_hash}",
                file=sys.stderr,
            )
            print(f"  Source: {surql_path}", file=sys.stderr)
            print(f"  Baseline: {baseline_path}", file=sys.stderr)
            sys.exit(1)

        print(f"Schema hash MATCHES baseline: {current_hash}")


if __name__ == "__main__":
    main()
