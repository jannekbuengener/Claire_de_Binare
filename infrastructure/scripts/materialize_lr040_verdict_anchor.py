#!/usr/bin/env python3
"""Materialize a committed LR-040 verdict anchor from raw 72h soak artifacts.

This script does not execute a soak run and does not authorize P5 start.
It only converts an already-evaluated raw LR-040 artifact directory under
``artifacts/soak_test_*`` into the committed anchor path under
``reports/p5_canary/<YYYY-MM-DD>/lr040/``.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_RELATIVE_PATH = "infrastructure/scripts/materialize_lr040_verdict_anchor.py"


class ContractError(ValueError):
    """Raised when the committed-anchor contract is violated."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise ContractError(
            f"path is outside the repository root: {path}"
        ) from exc


def _load_json_required(path: Path, description: str) -> dict:
    if not path.is_file():
        raise ContractError(f"required file missing: {description}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot load {description}: {exc}") from exc


def _file_record(path: Path, repo_root: Path) -> dict:
    if not path.is_file():
        raise ContractError(f"required source file missing: {path}")
    return {
        "path": _repo_relative(path, repo_root),
        "sha256": _sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _validate_source_layout(artifact_dir: Path, repo_root: Path) -> str:
    artifact_root = _repo_relative(artifact_dir, repo_root)
    if not artifact_root.startswith("artifacts/soak_test_"):
        raise ContractError(
            "source artifact directory must live under artifacts/soak_test_*"
        )
    return artifact_root


def _validate_report_root(report_root: Path, repo_root: Path) -> str:
    report_root_rel = _repo_relative(report_root, repo_root)
    if not report_root_rel.startswith("reports/p5_canary/"):
        raise ContractError(
            "committed report root must live under reports/p5_canary/<YYYY-MM-DD>/"
        )
    return report_root_rel


def _collect_snapshots(artifact_dir: Path) -> list[Path]:
    snapshots = sorted(artifact_dir.glob("resources_snapshot_*.txt"))
    if len(snapshots) < 2:
        raise ContractError("at least two resource snapshots are required")
    return snapshots


def _validate_raw_result(raw_result: dict, artifact_dir: Path, snapshots: list[Path]) -> None:
    if raw_result.get("control") != "LR-040":
        raise ContractError("raw evaluator output must declare control LR-040")

    verdict = raw_result.get("verdict")
    if verdict not in {"PASS", "FAIL"}:
        raise ContractError("raw evaluator output verdict must be PASS or FAIL")

    checks = raw_result.get("checks")
    metrics = raw_result.get("metrics")
    artifacts = raw_result.get("artifacts")
    failures = raw_result.get("failures")

    if not isinstance(checks, dict):
        raise ContractError("raw evaluator output missing checks object")
    if not isinstance(metrics, dict):
        raise ContractError("raw evaluator output missing metrics object")
    if not isinstance(artifacts, dict):
        raise ContractError("raw evaluator output missing artifacts object")
    if not isinstance(failures, list):
        raise ContractError("raw evaluator output missing failures list")

    hourly_log = artifact_dir / "hourly_checks.log"
    if artifacts.get("hourly_log") != hourly_log.name:
        raise ContractError("raw evaluator output hourly_log does not match source layout")

    expected_snapshots = [path.name for path in snapshots]
    if artifacts.get("resource_snapshots") != expected_snapshots:
        raise ContractError(
            "raw evaluator output resource_snapshots do not match source layout"
        )

    restart_alerts = artifact_dir / "restart_alerts.log"
    failed_marker = artifact_dir / "soak_test_FAILED.txt"

    raw_restart_alerts = artifacts.get("restart_alerts")
    if raw_restart_alerts is None and restart_alerts.is_file() and restart_alerts.stat().st_size > 0:
        raise ContractError("raw evaluator output omitted non-empty restart_alerts.log")
    if raw_restart_alerts is not None and raw_restart_alerts != restart_alerts.name:
        raise ContractError("raw evaluator output restart_alerts does not match source layout")

    raw_failed_marker = artifacts.get("failed_marker")
    if raw_failed_marker is None and failed_marker.is_file():
        raise ContractError("raw evaluator output omitted soak_test_FAILED.txt")
    if raw_failed_marker is not None and raw_failed_marker != failed_marker.name:
        raise ContractError("raw evaluator output failed_marker does not match source layout")


def materialize_lr040_verdict_anchor(
    artifact_dir: Path,
    report_root: Path,
    *,
    repo_root: Path | None = None,
    materialized_at_utc: str | None = None,
) -> tuple[Path, dict]:
    """Write the committed LR-040 verdict anchor and return ``(path, payload)``."""

    repo_root = (repo_root or DEFAULT_REPO_ROOT).resolve()
    artifact_dir = artifact_dir.resolve()
    report_root = report_root.resolve()

    artifact_root = _validate_source_layout(artifact_dir, repo_root)
    report_root_rel = _validate_report_root(report_root, repo_root)

    raw_eval_path = artifact_dir / "lr040_soak_gate_eval.json"
    raw_result = _load_json_required(raw_eval_path, "raw lr040_soak_gate_eval.json")

    hourly_log = artifact_dir / "hourly_checks.log"
    if not hourly_log.is_file():
        raise ContractError("required source file missing: hourly_checks.log")

    snapshots = _collect_snapshots(artifact_dir)
    _validate_raw_result(raw_result, artifact_dir, snapshots)

    target_dir = report_root / "lr040"
    target_path = target_dir / "lr040_soak_gate_eval.json"
    target_rel = _repo_relative(target_path, repo_root)

    restart_alerts = artifact_dir / "restart_alerts.log"
    failed_marker = artifact_dir / "soak_test_FAILED.txt"

    payload = {
        "schema_version": "1.0",
        "contract_role": "committed_verdict_anchor",
        "control": "LR-040",
        "verdict": raw_result["verdict"],
        "status": "EVIDENCE_COMMITTED",
        "reason": "materialized_from_raw_72h_soak_evidence",
        "committed_reference_path": target_rel,
        "source_raw_evidence": {
            "artifact_root": artifact_root,
            "verdict_source": _file_record(raw_eval_path, repo_root),
            "hourly_log": _file_record(hourly_log, repo_root),
            "resource_snapshots": [
                _file_record(snapshot, repo_root) for snapshot in snapshots
            ],
            "restart_alerts": (
                _file_record(restart_alerts, repo_root)
                if restart_alerts.is_file()
                else None
            ),
            "failed_marker": (
                _file_record(failed_marker, repo_root) if failed_marker.is_file() else None
            ),
        },
        "verdict_summary": {
            "checks": raw_result["checks"],
            "failures": raw_result["failures"],
            "metrics": raw_result["metrics"],
        },
        "materialization": {
            "report_root": report_root_rel,
            "materialized_at_utc": materialized_at_utc or _utc_now(),
            "script": SCRIPT_RELATIVE_PATH,
            "source_schema_version": raw_result.get("schema_version"),
        },
        "pass_required_before_start": True,
        "governance_effect": (
            "LR-040 PASS remains required; P5 stays NO-GO until all hard blockers "
            "are resolved"
        ),
        "notes": [
            "This file is a committed verdict anchor derived from raw 72h soak artifacts.",
            "It does not authorize a P5 canary start by itself.",
            "Shadow-prereq evidence packages are not valid LR-040 source artifacts.",
        ],
    }

    target_dir.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return target_path, payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize reports/p5_canary/<YYYY-MM-DD>/lr040/lr040_soak_gate_eval.json "
            "from raw artifacts/soak_test_*/lr040_soak_gate_eval.json"
        )
    )
    parser.add_argument("artifact_dir", help="Raw LR-040 artifact directory under artifacts/soak_test_*")
    parser.add_argument(
        "report_root",
        help="Committed report root under reports/p5_canary/<YYYY-MM-DD>/",
    )
    args = parser.parse_args()

    try:
        target_path, payload = materialize_lr040_verdict_anchor(
            Path(args.artifact_dir),
            Path(args.report_root),
        )
    except ContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Committed LR-040 verdict anchor written to {target_path}")
    print(f"Verdict: {payload['verdict']}")


if __name__ == "__main__":
    main()
