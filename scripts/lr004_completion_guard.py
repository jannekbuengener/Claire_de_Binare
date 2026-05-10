#!/usr/bin/env python3
"""
LR-004 Completion Guard: Deterministic LR-Task State Validator

Enforces fail-closed completion tracking for Live Readiness tasks.
Validates state files against LR-TASKS.yaml manifest.

Exit Codes:
  0 - All LR-Task states valid
  1 - Validation failure (invalid/missing state, schema violation)
  2 - Configuration error (missing manifest, invalid args)
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

try:
    import yaml
except ImportError:
    print("[LR-004] ERROR: pyyaml not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

# Constants
SPEC_VERSION = "1.0"
LR_DOCS_DIR = Path("docs/live-readiness")
MANIFEST_FILE = LR_DOCS_DIR / "LR-TASKS.yaml"
STATE_FILE_PATTERN = "LR-*-STATE.yaml"
VALID_STATES = {"DONE", "BLOCKED"}

# Reason Code Taxonomy (from LR-004-SPEC.md §5.2)
BLOCKED_REASON_CODES = {
    "RC_B001": "Upstream LR-Task not completed (hard dependency)",
    "RC_B002": "External system dependency unavailable",
    "RC_B003": "Third-party API/service unavailable or quota exceeded",
    "RC_B100": "Budget/funding approval required",
    "RC_B101": "Infrastructure resource unavailable",
    "RC_B102": "Personnel resource unavailable",
    "RC_B200": "Critical bug blocking implementation",
    "RC_B201": "Technology limitation (not fixable in scope)",
    "RC_B202": "Security/compliance blocker",
    "RC_B300": "Awaiting stakeholder decision/approval",
    "RC_B301": "Organizational policy change required",
    "RC_B302": "Cross-team coordination blocker",
    "RC_B400": "Requirements clarification needed",
    "RC_B401": "Scope change invalidated approach",
    "RC_B402": "Acceptance criteria unachievable",
}


class ValidationError:
    """Represents a single validation error"""
    def __init__(self, task_id: str, rule: str, message: str):
        self.task_id = task_id
        self.rule = rule
        self.message = message

    def __str__(self):
        return f"[FAIL] {self.task_id}: Rule {self.rule} violation - {self.message}"


class CompletionGuard:
    def __init__(self):
        self.errors: List[ValidationError] = []
        self.tasks_registry: Dict[str, str] = {}  # task_id -> task_title (from manifest)
        self.state_files: Dict[str, Path] = {}  # task_id -> filepath
        self.blocked_tasks: List[Dict] = []

    def add_error(self, task_id: str, rule: str, message: str):
        """Add validation error"""
        self.errors.append(ValidationError(task_id, rule, message))

    def validate_manifest(self) -> bool:
        """Validate manifest (Rules V000-V002)"""
        # Rule V000: Manifest Existence
        if not MANIFEST_FILE.exists():
            self.add_error("MANIFEST", "V000", f"Task manifest not found: {MANIFEST_FILE}")
            return False

        # Parse manifest
        try:
            with open(MANIFEST_FILE, 'r', encoding='utf-8') as f:
                manifest = yaml.safe_load(f)
        except Exception as e:
            self.add_error("MANIFEST", "V001", f"Failed to parse manifest: {e}")
            return False

        # Rule V001: Manifest Schema Valid
        if not isinstance(manifest, dict):
            self.add_error("MANIFEST", "V001", "Manifest schema invalid (not a dict)")
            return False

        if manifest.get("spec_version") != SPEC_VERSION:
            self.add_error("MANIFEST", "V001", f"Manifest schema invalid (spec_version must be '{SPEC_VERSION}')")
            return False

        if "tasks" not in manifest or not isinstance(manifest["tasks"], list):
            self.add_error("MANIFEST", "V001", "Manifest schema invalid (missing tasks array)")
            return False

        # Rule V002: No Duplicate Task IDs + Format Validation
        seen_ids: Set[str] = set()
        prev_task_id: Optional[str] = None
        task_id_pattern = re.compile(r"^LR-\d{3}$")

        for idx, task in enumerate(manifest["tasks"]):
            if not isinstance(task, dict):
                self.add_error("MANIFEST", "V002", f"Invalid task entry (not a dict): {task}")
                continue

            # Check for unexpected keys (only task_id and task_title allowed)
            expected_keys = {"task_id", "task_title"}
            actual_keys = set(task.keys())
            unexpected = actual_keys - expected_keys
            if unexpected:
                self.add_error("MANIFEST", "V002", f"Task entry has unexpected keys: {unexpected} (only task_id, task_title allowed)")

            task_id = task.get("task_id")
            task_title = task.get("task_title")

            if not task_id or not task_title:
                self.add_error("MANIFEST", "V002", f"Task entry missing task_id or task_title: {task}")
                continue

            # Validate task_id format (LR-NNN)
            if not task_id_pattern.match(task_id):
                self.add_error("MANIFEST", "V002", f"Invalid task_id format: {task_id} (expected LR-NNN)")

            # Validate task_title constraints
            if not isinstance(task_title, str) or len(task_title) == 0:
                self.add_error("MANIFEST", "V002", f"Task title must be non-empty string: {task_id}")
            elif len(task_title) > 200:
                self.add_error("MANIFEST", "V002", f"Task title exceeds 200 chars: {task_id} ({len(task_title)} chars)")

            # Check for duplicate task_id
            if task_id in seen_ids:
                self.add_error("MANIFEST", "V002", f"Duplicate task_id in manifest: {task_id}")
            else:
                seen_ids.add(task_id)
                self.tasks_registry[task_id] = task_title

            # Check ascending order
            if prev_task_id and task_id <= prev_task_id:
                self.add_error("MANIFEST", "V002", f"Tasks not in ascending order: {prev_task_id} >= {task_id}")
            prev_task_id = task_id

        return len(self.tasks_registry) > 0

    def scan_state_files(self):
        """Scan for STATE files and build registry"""
        if not LR_DOCS_DIR.exists():
            self.add_error("SCAN", "V003", f"Live readiness directory not found: {LR_DOCS_DIR}")
            return

        # Glob for STATE files
        state_files_found = list(LR_DOCS_DIR.glob(STATE_FILE_PATTERN))

        for filepath in state_files_found:
            # Extract task_id from filename (e.g., LR-001-STATE.yaml -> LR-001)
            match = re.match(r"(LR-\d{3})-STATE\.yaml", filepath.name)
            if not match:
                self.add_error("UNKNOWN", "V004", f"Invalid STATE filename format: {filepath.name}")
                continue

            task_id = match.group(1)

            # Rule V005: No Duplicate STATE Files for Same Task
            if task_id in self.state_files:
                existing = self.state_files[task_id]
                self.add_error(task_id, "V005", f"Duplicate STATE files for task: {existing.name}, {filepath.name}")
            else:
                self.state_files[task_id] = filepath

    def cross_validate_manifest_states(self):
        """Cross-validate manifest ↔ STATE files (Rules V003-V004)"""
        # Rule V003: STATE File Exists for Each Manifest Entry
        for task_id in self.tasks_registry.keys():
            if task_id not in self.state_files:
                expected_path = LR_DOCS_DIR / f"{task_id}-STATE.yaml"
                self.add_error(task_id, "V003", f"Missing STATE file (expected: {expected_path})")

        # Rule V004: No Orphan STATE Files
        for task_id in self.state_files.keys():
            if task_id not in self.tasks_registry:
                self.add_error(task_id, "V004", f"Orphan STATE file ({self.state_files[task_id].name} not in manifest)")

    def validate_state_file(self, task_id: str, filepath: Path) -> Optional[Dict]:
        """Validate single STATE file (Rules V006-V015)"""
        # Parse YAML
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state = yaml.safe_load(f)
        except Exception as e:
            self.add_error(task_id, "V006", f"Failed to parse STATE file: {e}")
            return None

        if not isinstance(state, dict):
            self.add_error(task_id, "V006", "STATE file is not a valid YAML dict")
            return None

        # Rule V006: Schema Version Match
        if state.get("spec_version") != SPEC_VERSION:
            self.add_error(task_id, "V006", f"Schema version must be '{SPEC_VERSION}' (found: {state.get('spec_version')})")

        # Rule V007: Task ID Consistency
        state_task_id = state.get("task_id")
        if state_task_id != task_id:
            self.add_error(task_id, "V007", f"Task ID mismatch (filename: {task_id}, content: {state_task_id})")

        # Rule V008: Task Title Consistency
        state_title = state.get("task_title")
        manifest_title = self.tasks_registry.get(task_id)
        if manifest_title and state_title != manifest_title:
            self.add_error(task_id, "V008", f"Task title mismatch (STATE: '{state_title}', manifest: '{manifest_title}')")

        # Rule V009: Status Enum Validity
        status = state.get("status")
        if status not in VALID_STATES:
            self.add_error(task_id, "V009", f"Status must be 'DONE' or 'BLOCKED' (found: {status})")
            return state  # Continue validation

        # Rule V010: DONE State Completeness
        if status == "DONE":
            required_fields = ["completion_timestamp", "completion_author"]
            forbidden_fields = ["blocked_reason_code", "blocked_reason_text", "blocked_since"]

            for field in required_fields:
                if not state.get(field):
                    self.add_error(task_id, "V010", f"DONE state missing required field: {field}")

            for field in forbidden_fields:
                if state.get(field) is not None:
                    self.add_error(task_id, "V010", f"DONE state has unexpected {field} (must be null)")

            # Validate timestamp format
            ts = state.get("completion_timestamp")
            if ts and not self.is_valid_iso8601_utc(ts):
                self.add_error(task_id, "V012", f"Invalid timestamp format for completion_timestamp: {ts}")

        # Rule V011: BLOCKED State Completeness
        if status == "BLOCKED":
            required_fields = ["blocked_reason_code", "blocked_reason_text", "blocked_since"]
            forbidden_fields = ["completion_timestamp", "completion_author"]

            for field in required_fields:
                if not state.get(field):
                    self.add_error(task_id, "V011", f"BLOCKED state missing required field: {field}")

            for field in forbidden_fields:
                if state.get(field) is not None:
                    self.add_error(task_id, "V011", f"BLOCKED state has unexpected {field} (must be null)")

            # Rule V013: Reason Code Taxonomy Validity
            reason_code = state.get("blocked_reason_code")
            if reason_code and reason_code not in BLOCKED_REASON_CODES:
                self.add_error(task_id, "V013", f"Invalid blocked_reason_code: {reason_code} (not in taxonomy)")

            # Validate timestamp format
            ts = state.get("blocked_since")
            if ts and not self.is_valid_iso8601_utc(ts):
                self.add_error(task_id, "V012", f"Invalid timestamp format for blocked_since: {ts}")

            # Track blocked tasks for reporting (always track, even if task has validation errors)
            if status == "BLOCKED":
                has_errors = any(e.task_id == task_id for e in self.errors)
                self.blocked_tasks.append({
                    "task_id": task_id,
                    "reason_code": reason_code,
                    "reason_text": state.get("blocked_reason_text", ""),
                    "since": state.get("blocked_since", ""),
                    "has_validation_errors": has_errors
                })

        # Rule V014: Evidence File Existence + Path Safety
        evidence_file = state.get("evidence_file")
        if evidence_file:
            # Check for absolute paths or directory traversal
            if Path(evidence_file).is_absolute():
                self.add_error(task_id, "V014", f"Evidence file must be relative path (found absolute): {evidence_file}")
            elif ".." in evidence_file:
                self.add_error(task_id, "V014", f"Evidence file contains directory traversal (..): {evidence_file}")
            else:
                evidence_path = Path(evidence_file)
                if not evidence_path.exists():
                    self.add_error(task_id, "V014", f"Evidence file not found: {evidence_file}")
        else:
            self.add_error(task_id, "V014", "Missing evidence_file field")

        # Rule V015: Evidence Commit Format
        evidence_commit = state.get("evidence_commit")
        if evidence_commit:
            if not self.is_valid_hex(evidence_commit, min_len=7, max_len=40):
                self.add_error(task_id, "V015", f"Invalid evidence_commit format: {evidence_commit} (expected 7-40 hex chars)")
        else:
            self.add_error(task_id, "V015", "Missing evidence_commit field")

        return state

    def is_valid_iso8601_utc(self, timestamp: str) -> bool:
        """Validate ISO 8601 UTC timestamp format (YYYY-MM-DDTHH:MM:SSZ)"""
        if not isinstance(timestamp, str):
            return False
        # Simple regex for ISO 8601 UTC (ending in Z)
        pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
        return bool(re.match(pattern, timestamp))

    def is_valid_hex(self, value: str, min_len: int, max_len: int) -> bool:
        """Validate hexadecimal string with length constraints"""
        if not isinstance(value, str):
            return False
        if not (min_len <= len(value) <= max_len):
            return False
        return bool(re.match(r"^[0-9a-fA-F]+$", value))

    def validate_all(self, task_id_filter: Optional[str] = None) -> int:
        """Validate all tasks or specific task"""
        print("[LR-004] Completion Guard: Validating LR-Task States...")
        print(f"[LR-004] Loading manifest: {MANIFEST_FILE}")

        # Step 1: Validate manifest
        if not self.validate_manifest():
            self.report_errors()
            return 1

        print(f"[LR-004] Found {len(self.tasks_registry)} tasks in manifest")

        # Step 2: Scan for STATE files
        self.scan_state_files()

        # Step 3: Cross-validate manifest ↔ STATE files
        self.cross_validate_manifest_states()

        # Step 4: Validate each STATE file
        tasks_to_validate = [task_id_filter] if task_id_filter else self.tasks_registry.keys()

        # Track actual status counts from STATE files
        done_count = 0
        blocked_count = 0

        for task_id in tasks_to_validate:
            if task_id not in self.tasks_registry:
                print(f"[LR-004] ERROR: Task {task_id} not in manifest")
                return 2

            if task_id in self.state_files:
                filepath = self.state_files[task_id]
                state = self.validate_state_file(task_id, filepath)

                # Report individual task status
                if state:
                    status = state.get("status")
                    if status == "DONE":
                        done_count += 1
                        completed = state.get("completion_timestamp", "unknown")
                        print(f"[OK] {task_id}: DONE (completed {completed[:10]})")
                    elif status == "BLOCKED":
                        blocked_count += 1
                        reason_code = state.get("blocked_reason_code", "unknown")
                        reason_text = state.get("blocked_reason_text", "")[:50]
                        print(f"[BLOCKED] {task_id}: {reason_code} - {reason_text}")

        # Step 5: Report results
        print()
        print("[LR-004] Summary:")
        print(f"  Total Tasks: {len(self.tasks_registry)}")
        print(f"  DONE: {done_count}")
        print(f"  BLOCKED: {blocked_count}")
        missing_count = sum(1 for e in self.errors if e.rule == "V003")
        orphan_count = sum(1 for e in self.errors if e.rule == "V004")
        print(f"  Missing: {missing_count}")
        print(f"  Orphaned: {orphan_count}")

        if self.blocked_tasks:
            print()
            print("[LR-004] BLOCKED Tasks:")
            for task in self.blocked_tasks:
                error_marker = " (has validation errors)" if task.get('has_validation_errors') else ""
                print(f"  - {task['task_id']}: {task['reason_code']} - {task['reason_text'][:80]}{error_marker}")

        if self.errors:
            print()
            self.report_errors()
            return 1

        print()
        print("[LR-004] PASS: All LR-Task states valid")
        return 0

    def report_errors(self):
        """Report all validation errors"""
        if not self.errors:
            return

        print()
        print(f"[LR-004] VALIDATION FAILURES ({len(self.errors)}):")
        for error in self.errors:
            print(f"  {error}")
        print()
        print("[LR-004] FAIL: Validation failed (fail-closed)")

    def generate_report(self) -> int:
        """Generate human-readable markdown report"""
        print("[LR-004] Completion Guard: Generating Report...")
        print()

        # Load manifest
        if not self.validate_manifest():
            self.report_errors()
            return 1

        # Scan STATE files
        self.scan_state_files()

        # Generate markdown table
        print("# LR-Task Completion Status")
        print()
        print("| Task ID | Title | Status | Details |")
        print("|---------|-------|--------|---------|")

        for task_id, task_title in sorted(self.tasks_registry.items()):
            if task_id in self.state_files:
                filepath = self.state_files[task_id]
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        state = yaml.safe_load(f)

                    status = state.get("status", "UNKNOWN")
                    if status == "DONE":
                        completed = state.get("completion_timestamp", "unknown")[:10]
                        details = f"Completed {completed}"
                    elif status == "BLOCKED":
                        reason_code = state.get("blocked_reason_code", "unknown")
                        reason_text = state.get("blocked_reason_text", "")[:50]
                        details = f"{reason_code}: {reason_text}"
                    else:
                        details = "Invalid status"

                    print(f"| {task_id} | {task_title} | {status} | {details} |")
                except Exception as e:
                    print(f"| {task_id} | {task_title} | ERROR | Failed to parse: {e} |")
            else:
                print(f"| {task_id} | {task_title} | MISSING | STATE file not found |")

        print()
        print(f"**Generated:** {MANIFEST_FILE}")
        print(f"**Total Tasks:** {len(self.tasks_registry)}")

        return 0


def main():
    parser = argparse.ArgumentParser(
        description="LR-004 Completion Guard: Validate LR-Task completion states",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate all tasks (CI mode)
  python scripts/lr004_completion_guard.py --check

  # Validate specific task
  python scripts/lr004_completion_guard.py --check --task-id LR-001

  # Generate markdown report
  python scripts/lr004_completion_guard.py --report
"""
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate mode (CI): Check all LR-*-STATE.yaml files (exit 1 on failure)"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Report mode: Generate human-readable markdown summary"
    )
    parser.add_argument(
        "--task-id",
        metavar="LR-NNN",
        help="Validate specific task only (e.g., LR-001)"
    )

    args = parser.parse_args()

    # Validate arguments
    if not (args.check or args.report):
        parser.print_help()
        return 2

    if args.task_id and not args.check:
        print("[LR-004] ERROR: --task-id requires --check", file=sys.stderr)
        return 2

    # Execute mode
    guard = CompletionGuard()

    try:
        if args.check:
            return guard.validate_all(task_id_filter=args.task_id)
        if args.report:
            return guard.generate_report()
    except Exception as e:
        print(f"[LR-004] FATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
