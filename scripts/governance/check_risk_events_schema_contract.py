#!/usr/bin/env python3
"""
Drift Guard: Validates risk_events schema contract.

Ensures INSERT column list in services/risk/service.py matches
canonical spec in the local governance schema.

Exit Codes:
  0 - PASS (no drift detected)
  1 - FAIL (drift detected or spec missing)
"""

import sys
import re
from pathlib import Path


def main():
    violations = []
    root_dir = Path.cwd()

    # 1. Find code INSERT statement
    code_file = root_dir / "services" / "risk" / "service.py"
    if not code_file.exists():
        violations.append(f"MISSING: {code_file.relative_to(root_dir)}")
        print_violations(violations)
        sys.exit(1)

    code_text = code_file.read_text(encoding="utf-8")

    # Extract INSERT columns from code
    insert_pattern = r"INSERT INTO risk_events\s*\(\s*([^)]+)\s*\)"
    match = re.search(insert_pattern, code_text, re.IGNORECASE | re.DOTALL)

    if not match:
        violations.append("ERROR: Could not find INSERT INTO risk_events in code")
        print_violations(violations)
        sys.exit(1)

    code_columns_raw = match.group(1)
    code_columns = [col.strip() for col in code_columns_raw.split(",")]

    # 2. Find spec file (prefer local canon, allow local archive snapshot as fallback)
    docs_archive = root_dir / "docs" / "archive" / "docs_hub_snapshot"
    spec_paths = [
        root_dir / "docs" / "governance" / "risk_events.schema.yaml",
        docs_archive / "knowledge" / "governance" / "risk_events.schema.yaml",
    ]

    spec_file = None
    for path in spec_paths:
        if path.exists():
            spec_file = path
            break

    if not spec_file:
        violations.append(
            "MISSING: risk_events.schema.yaml not found in local canon or local archive snapshot"
        )
        print_violations(violations)
        sys.exit(1)

    # 3. Parse YAML spec (simple regex, no external deps)
    spec_text = spec_file.read_text(encoding="utf-8")

    # Extract insert_columns from spec
    insert_section_pattern = r"insert_columns:\s*\n((?:  (?:#.*|-.+)\n?)+)"
    spec_match = re.search(insert_section_pattern, spec_text)

    if not spec_match:
        violations.append("ERROR: Spec missing insert_columns section")
        print_violations(violations)
        sys.exit(1)

    spec_columns = [
        line.strip().lstrip("- ").strip()
        for line in spec_match.group(1).strip().split("\n")
        if line.strip() and not line.strip().startswith("#")
    ]

    # 4. Compare column sets (order-agnostic)
    code_set = set(code_columns)
    spec_set = set(spec_columns)

    missing_in_spec = code_set - spec_set
    missing_in_code = spec_set - code_set

    if missing_in_spec:
        violations.append(
            f"DRIFT: Code inserts columns NOT in spec: {sorted(missing_in_spec)}"
        )

    if missing_in_code:
        violations.append(
            f"DRIFT: Spec declares columns NOT in code: {sorted(missing_in_code)}"
        )

    # 5. Warn on order mismatch (not FAIL, just warn)
    if code_columns != spec_columns:
        print("WARNING: Column order differs (spec vs code)")
        print(f"  Spec order: {spec_columns}")
        print(f"  Code order: {code_columns}")
        print("  (Not a FAIL, but may indicate update needed)")
        print()

    # 6. Report results
    if violations:
        print_violations(violations)
        sys.exit(1)
    else:
        print("[PASS] risk_events Schema Contract: PASS")
        print(f"   Code columns: {code_columns}")
        print(f"   Spec columns: {spec_columns}")
        sys.exit(0)


def print_violations(violations):
    print("[FAIL] risk_events Schema Contract: FAIL")
    for v in violations:
        print(f"   {v}")
    print()
    print("Fix: Update risk_events.schema.yaml or services/risk/service.py to align")


if __name__ == "__main__":
    main()
