#!/usr/bin/env python3
"""
LR-005 Phase A: Live Readiness Completion Reporter (CLI, read-only, deterministic)

Purpose:
  Generate deterministic snapshots of LR task completion state from
  LR-TASKS.yaml and LR-*-STATE.yaml files.

Scope:
  - Read-only observer (no state mutations)
  - Deterministic outputs (same inputs -> same outputs)
  - Offline-capable (no network calls, no GitHub API)
  - Clock-independent (no datetime.now(), no age calculations)

Usage:
  python scripts/lr_reporter.py --json               # JSON to stdout
  python scripts/lr_reporter.py --markdown           # Markdown to stdout
  python scripts/lr_reporter.py --snapshot           # Write both files
  python scripts/lr_reporter.py --snapshot --output-dir <path>

Exit Codes:
  0 - Success
  1 - Validation/input error (STATE/TASKS missing or invalid)
  2 - Runtime/tool error
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


DEFAULT_DATA_DIR = Path("docs/live-readiness")
TASKS_FILE = "LR-TASKS.yaml"
STATE_FILE_PATTERN = "LR-*-STATE.yaml"


def get_git_metadata() -> Dict[str, str]:
    """
    Extract Git metadata (commit SHA, branch) for snapshot metadata.
    Returns placeholder values if Git is not available (test mode).
    """
    import subprocess

    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        commit = "unknown"

    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        branch = "unknown"

    return {"git_commit": commit, "git_branch": branch}


def load_tasks_manifest(data_dir: Path) -> Dict[str, Any]:
    """Load LR-TASKS.yaml manifest."""
    tasks_path = data_dir / TASKS_FILE
    if not tasks_path.exists():
        raise FileNotFoundError(f"Tasks manifest not found: {tasks_path}")

    with open(tasks_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_state_files(data_dir: Path, task_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Load all LR-*-STATE.yaml files for given task IDs."""
    states = {}

    for task_id in task_ids:
        state_path = data_dir / f"{task_id}-STATE.yaml"
        if not state_path.exists():
            raise FileNotFoundError(f"State file not found for {task_id}: {state_path}")

        with open(state_path, "r", encoding="utf-8") as f:
            states[task_id] = yaml.safe_load(f)

    return states


def parse_iso_timestamp(iso_str: Optional[str]) -> Optional[int]:
    """
    Convert ISO 8601 timestamp to Unix epoch (seconds).
    Returns None if input is None or invalid.
    Clock-independent: parses stored timestamp, does not use now().
    """
    if iso_str is None:
        return None

    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except (ValueError, AttributeError):
        return None


def generate_snapshot(data_dir: Path) -> Dict[str, Any]:
    """
    Generate deterministic completion snapshot from LR-TASKS + STATE files.

    Returns:
      Dict conforming to LR-005-SPEC §4.2 JSON schema
    """
    # Load inputs
    manifest = load_tasks_manifest(data_dir)
    task_ids = [task["task_id"] for task in manifest["tasks"]]
    states = load_state_files(data_dir, task_ids)
    git_meta = get_git_metadata()

    # Build task list with state details
    tasks = []
    blocked_details = []
    done_count = 0
    blocked_count = 0

    for task_def in manifest["tasks"]:
        task_id = task_def["task_id"]
        task_title = task_def["task_title"]
        state = states[task_id]

        status = state["status"]

        task_entry = {
            "task_id": task_id,
            "task_title": task_title,
            "status": status,
            "evidence_file": state.get("evidence_file"),
            "evidence_commit": state.get("evidence_commit"),
        }

        if status == "DONE":
            done_count += 1
            task_entry["completion_timestamp"] = state.get("completion_timestamp")
            task_entry["completion_author"] = state.get("completion_author")
            task_entry["blocked_reason_code"] = None
            task_entry["blocked_reason_text"] = None
            task_entry["blocked_since"] = None
            task_entry["blocked_since_epoch"] = None
        elif status == "BLOCKED":
            blocked_count += 1
            blocked_since = state.get("blocked_since")
            blocked_since_epoch = parse_iso_timestamp(blocked_since)

            task_entry["completion_timestamp"] = None
            task_entry["completion_author"] = None
            task_entry["blocked_reason_code"] = state.get("blocked_reason_code")
            task_entry["blocked_reason_text"] = state.get("blocked_reason_text")
            task_entry["blocked_since"] = blocked_since
            task_entry["blocked_since_epoch"] = blocked_since_epoch

            # Add to blocked_details
            blocked_details.append(
                {
                    "task_id": task_id,
                    "task_title": task_title,
                    "reason_code": state.get("blocked_reason_code"),
                    "reason_text": state.get("blocked_reason_text"),
                    "blocked_since": blocked_since,
                    "blocked_since_epoch": blocked_since_epoch,
                }
            )

        tasks.append(task_entry)

    total_tasks = len(task_ids)
    completion_percentage = (done_count / total_tasks * 100) if total_tasks > 0 else 0.0

    # Build snapshot (LR-005-SPEC §4.2)
    snapshot = {
        "spec_version": "1.0",
        "snapshot_metadata": {
            "data_source": str(data_dir),
            "git_commit": git_meta["git_commit"],
            "git_branch": git_meta["git_branch"],
        },
        "summary": {
            "total_tasks": total_tasks,
            "done_count": done_count,
            "blocked_count": blocked_count,
            "completion_percentage": round(completion_percentage, 1),
        },
        "tasks": tasks,
        "blocked_details": blocked_details,
    }

    return snapshot


def render_markdown(snapshot: Dict[str, Any]) -> str:
    """
    Render snapshot as Markdown (LR-005-SPEC §4.3 template).
    Clock-independent: no "Generated at" timestamps.
    """
    meta = snapshot["snapshot_metadata"]
    summary = snapshot["summary"]
    tasks = snapshot["tasks"]
    blocked = snapshot["blocked_details"]

    lines = [
        "# LR-Task Completion Snapshot",
        "",
        f"**Git Commit:** {meta['git_commit']}",
        f"**Branch:** {meta['git_branch']}",
        f"**Data Source:** {meta['data_source']}",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| **Total Tasks** | {summary['total_tasks']} |",
        f"| **Done** | {summary['done_count']} |",
        f"| **Blocked** | {summary['blocked_count']} |",
        f"| **Completion** | {summary['completion_percentage']}% |",
        "",
        "---",
        "",
        "## Task Status",
        "",
        "| Task ID | Title | Status | Details |",
        "|---------|-------|--------|---------|",
    ]

    for task in tasks:
        task_id = task["task_id"]
        title = task["task_title"]
        status = task["status"]

        if status == "DONE":
            icon = "✅"
            author = task.get("completion_author", "unknown")
            timestamp = task.get("completion_timestamp", "unknown")
            details = f"Completed {timestamp} by {author}"
        elif status == "BLOCKED":
            icon = "🔴"
            reason_code = task.get("blocked_reason_code", "unknown")
            blocked_since = task.get("blocked_since", "unknown")
            details = f"{reason_code} - since {blocked_since}"
        else:
            icon = "❓"
            details = "Unknown status"

        lines.append(f"| {task_id} | {title} | {icon} {status} | {details} |")

    lines.extend(
        [
            "",
            "---",
            "",
            f"## Blocked Tasks ({summary['blocked_count']})",
            "",
        ]
    )

    if blocked:
        lines.extend(
            [
                "| Task ID | Title | Reason Code | Blocked Since | Reason |",
                "|---------|-------|-------------|---------------|--------|",
            ]
        )
        for item in blocked:
            lines.append(
                f"| {item['task_id']} | {item['task_title']} | "
                f"{item['reason_code']} | {item['blocked_since']} | "
                f"{item['reason_text']} |"
            )
    else:
        lines.append("*No blocked tasks.*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="LR-005 Phase A: Live Readiness Completion Reporter"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output JSON snapshot to stdout"
    )
    parser.add_argument(
        "--markdown", action="store_true", help="Output Markdown snapshot to stdout"
    )
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Write JSON + Markdown snapshot files to output directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Output directory for --snapshot (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Input directory for STATE files (default: {DEFAULT_DATA_DIR})",
    )

    args = parser.parse_args()

    # Validate: at least one output mode
    if not (args.json or args.markdown or args.snapshot):
        parser.print_help()
        print(
            "\nERROR: Must specify at least one output mode (--json, --markdown, --snapshot)",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        # Generate snapshot
        snapshot = generate_snapshot(args.data_dir)

        # Output modes
        if args.json:
            print(json.dumps(snapshot, indent=2, ensure_ascii=False))

        if args.markdown:
            # Force UTF-8 encoding for stdout (Windows compatibility)
            import codecs

            if sys.stdout.encoding != "utf-8":
                sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
            print(render_markdown(snapshot))

        if args.snapshot:
            output_dir = args.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)

            json_path = output_dir / "completion_snapshot.json"
            md_path = output_dir / "completion_snapshot.md"

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(render_markdown(snapshot))

            print(f"Snapshots written:", file=sys.stderr)
            print(f"  JSON: {json_path}", file=sys.stderr)
            print(f"  Markdown: {md_path}", file=sys.stderr)

        sys.exit(0)

    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
