"""Write-free dry-plan CLI for hh_hl campaign preparation (#4374).

Never writes artifacts (except optional --write-draft-manifest which is an
explicit prep-time config materialization, not campaign evidence).
Never starts replays. Never posts Owner-GO.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, TextIO

from tools.arvp_vacation.campaign_executor_providers import resolve_campaign_executor
from tools.arvp_vacation.campaign_profile import (
    HH_HL_PREP_PROFILE_ID,
    CampaignProfileError,
    assert_execution_allowed,
    load_profile,
)
from tools.arvp_vacation.hh_hl_campaign_analyzer import build_hh_hl_analyzer_profile
from tools.arvp_vacation.hh_hl_campaign_dataset import build_dataset_binding_receipt
from tools.arvp_vacation.hh_hl_campaign_grid import grid_draft_report
from tools.arvp_vacation.hh_hl_campaign_manifest import (
    build_hh_hl_draft_manifest,
    write_hh_hl_draft_manifest,
)
from tools.arvp_vacation.hh_hl_campaign_reproduction import (
    build_hh_hl_reproduction_plan,
)
from tools.arvp_vacation.hh_hl_campaign_run_plan import build_hh_hl_run_plan

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _git_head_sha(repo_root: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo_root),
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def dry_plan(*, repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or PROJECT_ROOT
    profile = load_profile(HH_HL_PREP_PROFILE_ID)
    manifest = build_hh_hl_draft_manifest()
    receipt = build_dataset_binding_receipt()
    planning_sha = _git_head_sha(root)
    plan = build_hh_hl_run_plan(
        profile=profile,
        manifest=manifest,
        planning_sha=planning_sha,
        dataset_receipt=receipt,
    )
    reproduction = build_hh_hl_reproduction_plan(plan.run_keys)
    analyzer = build_hh_hl_analyzer_profile(expected_run_keys=plan.run_keys)
    grid = grid_draft_report()

    # Prove planning-only executor refuse path without executing replays.
    executor = resolve_campaign_executor(profile)
    execute_probe = "not_called"
    try:
        assert_execution_allowed(profile)
        execute_probe = "UNEXPECTED_ALLOWED"
    except CampaignProfileError as exc:
        execute_probe = str(exc)

    return {
        "command": "plan",
        "writes": False,
        "replays": False,
        "campaign_execution_authorized": False,
        "strategy_id": plan.strategy_id,
        "profile_id": profile.profile_id,
        "planning_sha": planning_sha,
        "execution_sha": None,
        "manifest_fingerprint": plan.manifest_fingerprint,
        "run_plan_fingerprint": plan.run_plan_fingerprint,
        "dataset_binding_status": receipt.quality_gate_status,
        "variant_count": plan.variant_count,
        "window_count": plan.window_count,
        "expected_run_count": plan.expected_run_count,
        "reproduction_plan_fingerprint": reproduction["reproduction_plan_fingerprint"],
        "analyzer_profile_id": analyzer["analyzer_profile_id"],
        "analyzer_profile_fingerprint": analyzer["analyzer_profile_fingerprint"],
        "evidence_namespace": plan.evidence_namespace,
        "grid_status": grid["status"],
        "missing_owner_gates": [
            "GO_HH_HL_CAMPAIGN_DESIGN",
            "GO_HH_HL_CAMPAIGN_EXECUTION",
        ],
        "executor_provider_id": profile.executor_provider_id,
        "executor_class": type(executor).__name__,
        "execute_probe": execute_probe,
        "lr_status": "NO-GO",
        "local_proof_required": receipt.local_proof_required,
        "local_proof_command": receipt.local_proof_command,
        "non_executable_reasons": list(manifest["non_executable_reasons"]),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.arvp_vacation.hh_hl_campaign_plan",
        description="hh_hl campaign preparation dry-plan (write-free, no replays)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan", help="Write-free dry plan")
    sub.add_parser("grid", help="Print baseline-only grid draft")
    sub.add_parser("prove-dataset", help="Print local dataset proof command / HOLD")
    write_p = sub.add_parser(
        "write-draft-manifest",
        help="Materialize non-executable draft manifest into config/arvp",
    )
    write_p.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Optional output path (default: profile manifest_path)",
    )
    return parser


def main(argv: list[str] | None = None, *, stream: TextIO | None = None) -> int:
    out = stream or sys.stdout
    args = build_parser().parse_args(argv)
    if args.command == "plan":
        payload = dry_plan()
        out.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return 0
    if args.command == "grid":
        out.write(json.dumps(grid_draft_report(), indent=2, sort_keys=True) + "\n")
        return 0
    if args.command == "prove-dataset":
        receipt = build_dataset_binding_receipt()
        out.write(json.dumps(receipt.as_dict(), indent=2, sort_keys=True) + "\n")
        return 2 if receipt.local_proof_required else 0
    if args.command == "write-draft-manifest":
        path = write_hh_hl_draft_manifest(args.path)
        out.write(json.dumps({"wrote": path.as_posix(), "writes": True}) + "\n")
        return 0
    raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
