#!/usr/bin/env python3
"""
Coverage Guard: Validates correlation event type implementation (Phase 8D).

Checks that all required event types have literal persist calls in code.
This is NOT schema validation (see check_correlation_schema_contract.py).
This guard ensures event types are actually implemented, not just defined.

Detection method:
- Searches for persist_correlation_event( or _persist_correlation_event(
- Only counts string literals: event_type="ORDER"
- Variables or dynamic values are NOT counted

Exit codes:
- 0: PASS (all required events implemented, or ALLOW_EVIDENCE_DEBT=1)
- 1: FAIL (missing event implementations)

Environment:
- ALLOW_EVIDENCE_DEBT=1: Treat missing events as PASS with INFO (exit 0)
"""

import os
import re
import sys
from pathlib import Path

# Environment gate
ALLOW_EVIDENCE_DEBT = os.getenv("ALLOW_EVIDENCE_DEBT", "0") == "1"

# Required event types for full correlation chain
REQUIRED_EVENT_TYPES = {"SIGNAL", "DECISION", "ORDER", "FILL"}

# Target files to scan (hardcoded, deterministic)
TARGET_FILES = [
    "services/signal/service.py",
    "services/risk/service.py",
    "services/execution/service.py",
    "services/execution/database.py",
]

# Search window: how many characters after persist call to look for event_type
SEARCH_WINDOW = 500


def extract_event_types(code: str) -> set[str]:
    """Extract event_type string literals from persist_correlation_event calls.

    Strategy:
    1. Find all persist_correlation_event( or _persist_correlation_event( calls
    2. For each call, search within a bounded window for event_type="LITERAL"
    3. Only string literals count (no variables)

    Returns set of found event type literals.
    """
    found = set()

    # Find all persist call positions
    persist_pattern = r"_?persist_correlation_event\s*\("
    for match in re.finditer(persist_pattern, code):
        start_pos = match.end()
        # Search within bounded window for event_type literal
        window = code[start_pos : start_pos + SEARCH_WINDOW]

        # Look for event_type="LITERAL" or event_type='LITERAL'
        event_match = re.search(r'event_type\s*=\s*["\']([A-Z_]+)["\']', window)
        if event_match:
            found.add(event_match.group(1))

    return found


def scan_file(file_path: Path) -> set[str]:
    """Scan a single file for event type implementations."""
    if not file_path.exists():
        return set()

    code = file_path.read_text(encoding="utf-8")
    return extract_event_types(code)


def main() -> int:
    root_dir = Path(__file__).parent.parent.parent

    # Collect all implemented event types across target files
    implemented = set()

    for rel_path in TARGET_FILES:
        file_path = root_dir / rel_path
        found = scan_file(file_path)
        implemented.update(found)

    # Determine missing
    missing = REQUIRED_EVENT_TYPES - implemented

    # Output - strict contract: only PASS or FAIL as status
    if not missing:
        print("[PASS] Correlation Event Coverage: PASS")
        return 0

    if ALLOW_EVIDENCE_DEBT:
        print("[PASS] Correlation Event Coverage: PASS")
        print()
        print("[INFO] Evidence debt allowed (ALLOW_EVIDENCE_DEBT=1)")
        print(f"  Missing: {', '.join(sorted(missing))}")
        return 0

    # Fail-closed
    print("[FAIL] Correlation Event Coverage: FAIL")
    print(f"Missing: {', '.join(sorted(missing))}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
