#!/usr/bin/env python3
"""
Drift Guard: Validates correlation schema contracts (Phase 8C).

Checks that INSERT statements in code match canonical specs in:
- docs/contracts/correlation.schema.yaml
- docs/contracts/blocked_decisions.schema.yaml

Exit codes:
- 0: PASS (no drift)
- 1: FAIL (drift detected or missing INSERT - unless ALLOW_UNIMPLEMENTED=1)

Environment:
- ALLOW_UNIMPLEMENTED=1: Treat missing INSERT statements as INFO (exit 0)
"""

import os
import re
import sys
from pathlib import Path

import yaml

# Allow missing INSERT statements during development
ALLOW_UNIMPLEMENTED = os.getenv("ALLOW_UNIMPLEMENTED", "0") == "1"


def extract_insert_columns(code: str, table_name: str) -> list[str]:
    """Extract column names from INSERT INTO statement for given table.

    Handles:
    - Quoted table names ("table" or 'table')
    - Arbitrary whitespace/newlines between tokens
    - Case-insensitive matching
    """
    # Pattern: INSERT INTO [optional quotes]table_name[optional quotes] (col1, col2, ...)
    # Handles: INSERT INTO table_name, INSERT INTO "table_name", INSERT INTO 'table_name'
    pattern = (
        rf"INSERT\s+INTO\s+"  # INSERT INTO with flexible whitespace
        rf"[\"']?{re.escape(table_name)}[\"']?"  # table name with optional quotes
        rf"\s*\(\s*"  # opening paren with optional whitespace
        rf"([^)]+)"  # capture column list
        rf"\s*\)"  # closing paren
    )
    match = re.search(pattern, code, re.IGNORECASE | re.DOTALL)
    if not match:
        return []

    columns_str = match.group(1)
    # Normalize: collapse all whitespace (including newlines) to single space
    columns_str = re.sub(r"\s+", " ", columns_str)
    # Split by comma and clean up
    columns = [col.strip() for col in columns_str.split(",")]
    return [col for col in columns if col]


def load_schema_yaml(path: Path) -> dict:
    """Load schema YAML file."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def check_table_contract(
    code_file: Path,
    schema_file: Path,
    table_name: str,
) -> list[str]:
    """Check if code INSERT matches schema contract for a table."""
    violations = []

    # Load schema
    schema = load_schema_yaml(schema_file)
    if not schema:
        violations.append(f"MISSING: {schema_file} not found or empty")
        return violations

    expected_columns = schema.get("insert_columns", [])
    if not expected_columns:
        violations.append(f"MISSING: insert_columns not defined in {schema_file}")
        return violations

    # Load code
    if not code_file.exists():
        violations.append(f"MISSING: {code_file} not found")
        return violations

    code = code_file.read_text(encoding="utf-8")
    actual_columns = extract_insert_columns(code, table_name)

    if not actual_columns:
        # Table might not be implemented yet
        if ALLOW_UNIMPLEMENTED:
            violations.append(
                f"INFO: No INSERT INTO {table_name} found in {code_file.name} (ALLOW_UNIMPLEMENTED=1)"
            )
        else:
            violations.append(
                f"FAIL: No INSERT INTO {table_name} found in {code_file.name} (required)"
            )
        return violations

    # Compare
    if actual_columns != expected_columns:
        violations.append(
            f"DRIFT: {table_name} INSERT columns mismatch\n"
            f"  Expected: {expected_columns}\n"
            f"  Actual:   {actual_columns}"
        )

    return violations


def main() -> int:
    root_dir = Path(__file__).parent.parent.parent
    contracts_dir = root_dir / "docs" / "contracts"

    all_violations = []

    # Check correlation_ledger
    correlation_violations = check_table_contract(
        code_file=root_dir / "services" / "risk" / "service.py",
        schema_file=contracts_dir / "correlation.schema.yaml",
        table_name="correlation_ledger",
    )
    all_violations.extend(correlation_violations)

    # Also check signal service for SIGNAL events
    signal_violations = check_table_contract(
        code_file=root_dir / "services" / "signal" / "service.py",
        schema_file=contracts_dir / "correlation.schema.yaml",
        table_name="correlation_ledger",
    )
    all_violations.extend(signal_violations)

    # Also check execution service for ORDER/FILL events (INSERT is in database.py)
    exec_violations = check_table_contract(
        code_file=root_dir / "services" / "execution" / "database.py",
        schema_file=contracts_dir / "correlation.schema.yaml",
        table_name="correlation_ledger",
    )
    all_violations.extend(exec_violations)

    # Check blocked_decisions
    blocked_violations = check_table_contract(
        code_file=root_dir / "services" / "risk" / "service.py",
        schema_file=contracts_dir / "blocked_decisions.schema.yaml",
        table_name="blocked_decisions",
    )
    all_violations.extend(blocked_violations)

    # Filter: INFO is ignorable, everything else (FAIL/DRIFT/MISSING) is error
    errors = [v for v in all_violations if not v.startswith("INFO:")]
    infos = [v for v in all_violations if v.startswith("INFO:")]

    if infos:
        print("[INFO] Correlation Schema Contract Check:")
        for info in infos:
            print(f"  {info}")
        print()

    if not errors:
        print("[PASS] Correlation Schema Contract: PASS")
        print("  - correlation.schema.yaml: OK")
        print("  - blocked_decisions.schema.yaml: OK")
        return 0

    print("[FAIL] Correlation Schema Contract: FAIL")
    for violation in errors:
        print(f"  {violation}")
    print()
    print("Fix: Update schema YAML or code INSERT statements to align")
    return 1


if __name__ == "__main__":
    sys.exit(main())
