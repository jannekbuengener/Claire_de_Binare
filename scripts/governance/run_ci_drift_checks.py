#!/usr/bin/env python3
"""
Read-only CI drift wrapper for governance hygiene.

Runs both drift guards in one command and returns deterministic exit codes:
- 0: no drift
- 2: drift detected
- 1: execution error
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

DEFAULT_REPO = "jannekbuengener/Claire_de_Binare"
DEFAULT_BRANCH = "main"
DEFAULT_BP_SCRIPT = Path("scripts/governance/check_branch_protection_drift.py")
DEFAULT_BP_BASELINE = Path("reports/BRANCH_PROTECTION_BASELINE_main.json")
DEFAULT_BP_REPORT = Path("reports/BRANCH_PROTECTION_DRIFT_REPORT_main.md")
DEFAULT_BP_APPLY_PAYLOAD = Path("reports/BRANCH_PROTECTION_APPLY_PAYLOAD_main.json")
DEFAULT_RC_SCRIPT = Path("scripts/governance/check_required_check_contexts.py")
DEFAULT_RC_BASELINE = Path("reports/REQUIRED_CHECK_CONTEXTS_BASELINE_main.json")
DEFAULT_WORKFLOWS_DIR = Path(".github/workflows")
DEFAULT_RC_REPORT = Path("reports/REQUIRED_CHECK_CONTEXTS_DRIFT_REPORT_main.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run branch protection + required contexts drift checks (read-only)."
    )
    parser.add_argument(
        "--repo", default=DEFAULT_REPO, help="owner/repo for branch protection read"
    )
    parser.add_argument(
        "--branch", default=DEFAULT_BRANCH, help="branch for branch protection read"
    )

    parser.add_argument(
        "--branch-protection-script",
        default=str(DEFAULT_BP_SCRIPT),
        help="path to check_branch_protection_drift.py",
    )
    parser.add_argument(
        "--branch-protection-baseline",
        default=str(DEFAULT_BP_BASELINE),
        help="branch protection baseline JSON path",
    )
    parser.add_argument(
        "--branch-protection-report",
        default=str(DEFAULT_BP_REPORT),
        help="branch protection drift markdown output path",
    )
    parser.add_argument(
        "--branch-protection-apply-payload",
        default=str(DEFAULT_BP_APPLY_PAYLOAD),
        help="manual branch protection apply payload output path",
    )
    parser.add_argument(
        "--branch-protection-current-json",
        default=None,
        help="optional current branch protection JSON for offline/fallback mode",
    )

    parser.add_argument(
        "--required-contexts-script",
        default=str(DEFAULT_RC_SCRIPT),
        help="path to check_required_check_contexts.py",
    )
    parser.add_argument(
        "--required-contexts-baseline",
        default=str(DEFAULT_RC_BASELINE),
        help="required-check contexts baseline JSON path",
    )
    parser.add_argument(
        "--workflows-dir",
        default=str(DEFAULT_WORKFLOWS_DIR),
        help="workflow directory for context derivation",
    )
    parser.add_argument(
        "--required-contexts-report",
        default=str(DEFAULT_RC_REPORT),
        help="required-check contexts drift markdown output path",
    )
    return parser.parse_args()


def _run(label: str, command: list[str]) -> int:
    printable = " ".join(shlex.quote(part) for part in command)
    print(f"[ci-drift] {label}: {printable}", flush=True)
    proc = subprocess.run(command, check=False)
    print(f"[ci-drift] {label}: exit={proc.returncode}", flush=True)
    return proc.returncode


def _require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path.as_posix()}")


def main() -> int:
    args = parse_args()

    bp_script = Path(args.branch_protection_script)
    rc_script = Path(args.required_contexts_script)

    _require_file(bp_script, "branch protection checker")
    _require_file(rc_script, "required contexts checker")

    branch_cmd = [
        sys.executable,
        str(bp_script),
        "--repo",
        args.repo,
        "--branch",
        args.branch,
        "--baseline",
        args.branch_protection_baseline,
        "--report",
        args.branch_protection_report,
        "--apply-payload-out",
        args.branch_protection_apply_payload,
    ]
    if args.branch_protection_current_json:
        branch_cmd.extend(["--current-json", args.branch_protection_current_json])

    required_cmd = [
        sys.executable,
        str(rc_script),
        "--baseline",
        args.required_contexts_baseline,
        "--workflows-dir",
        args.workflows_dir,
        "--report",
        args.required_contexts_report,
    ]

    branch_code = _run("branch_protection_drift", branch_cmd)
    required_code = _run("required_check_contexts_drift", required_cmd)

    if branch_code not in {0, 2} or required_code not in {0, 2}:
        print(
            "[ci-drift] result=ERROR "
            f"(branch_protection={branch_code}, required_contexts={required_code})"
        )
        return 1

    if branch_code == 2 or required_code == 2:
        print(
            "[ci-drift] result=DRIFT "
            f"(branch_protection={branch_code}, required_contexts={required_code})"
        )
        return 2

    print(
        "[ci-drift] result=NO_DRIFT "
        f"(branch_protection={branch_code}, required_contexts={required_code})"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
