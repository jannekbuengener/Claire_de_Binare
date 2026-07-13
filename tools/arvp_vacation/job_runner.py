from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .contract import (
    STRATEGY_ADAPTERS,
    VacationContractError,
    VacationManifest,
    resolve_scenario_group_id,
)

EXPECTED_SCENARIO_ARTIFACTS = (
    "scenario_group_manifest.json",
    "scenario_comparison_summary.md",
)


@dataclass(frozen=True, slots=True)
class JobRunResult:
    exit_code: int
    command: list[str]
    stdout: str
    stderr: str
    artifact_dir: str
    artifacts_present: list[str]
    artifacts_missing: list[str]
    artifacts_complete: bool
    scenario_metrics: dict[str, Any]
    error_classification: str | None


SubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]


def build_replay_command(
    *,
    repo_root: Path,
    manifest: VacationManifest,
    job: Mapping[str, Any],
    replay_output_dir: Path,
) -> list[str]:
    strategy_id = str(job["strategy_id"])
    adapter_id = STRATEGY_ADAPTERS[strategy_id]
    scenarios = job.get("scenarios") or manifest.scenarios
    scenario_csv = ",".join(str(s) for s in scenarios)
    scenario_group_id = resolve_scenario_group_id(job)
    return [
        sys.executable,
        "-m",
        "services.validation.strategy_replay_runner",
        "--dataset-source",
        "file",
        "--input-candles",
        str(repo_root / str(job["input_candles"])),
        "--strategy-id",
        strategy_id,
        "--adapter-id",
        adapter_id,
        "--symbol",
        str(job.get("symbol") or manifest.symbol),
        "--speedup-profile",
        manifest.speedup_profile,
        "--output-dir",
        str(replay_output_dir),
        "--scenario-group",
        scenario_csv,
        "--scenario-group-id",
        scenario_group_id,
    ]


def _collect_artifact_status(group_dir: Path) -> tuple[list[str], list[str], bool]:
    present: list[str] = []
    missing: list[str] = []
    for name in EXPECTED_SCENARIO_ARTIFACTS:
        path = group_dir / name
        if path.exists():
            present.append(name)
        else:
            missing.append(name)
    metrics_files = sorted(group_dir.glob("*_metrics.json"))
    for path in metrics_files:
        present.append(path.name)
    complete = not missing and bool(metrics_files)
    return present, missing, complete


def _load_scenario_metrics(group_dir: Path) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for path in sorted(group_dir.glob("*_metrics.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        metrics[path.stem.replace("_metrics", "")] = payload
    manifest_path = group_dir / "scenario_group_manifest.json"
    if manifest_path.exists():
        try:
            metrics["_group_manifest"] = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            pass
    return metrics


def resolve_replay_group_dir(
    replay_output_dir: Path, scenario_group_id: str
) -> Path:
    """Resolve scenario artifacts under replay_output_dir / scenario_group_id."""
    primary = replay_output_dir / scenario_group_id
    if primary.is_dir():
        return primary
    if not replay_output_dir.is_dir():
        return primary
    alt_dirs = [p for p in replay_output_dir.iterdir() if p.is_dir()]
    if len(alt_dirs) == 1 and not primary.exists():
        return alt_dirs[0]
    return primary


def run_replay_job(
    *,
    repo_root: Path,
    manifest: VacationManifest,
    job: Mapping[str, Any],
    job_artifact_dir: Path,
    timeout_seconds: int,
    subprocess_runner: SubprocessRunner | None = None,
) -> JobRunResult:
    replay_output_dir = job_artifact_dir / "replay"
    replay_output_dir.mkdir(parents=True, exist_ok=True)
    command = build_replay_command(
        repo_root=repo_root,
        manifest=manifest,
        job=job,
        replay_output_dir=replay_output_dir,
    )
    runner = subprocess_runner or subprocess.run
    try:
        completed = runner(
            command,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        (job_artifact_dir / "stdout.log").write_text(exc.stdout or "", encoding="utf-8")
        (job_artifact_dir / "stderr.log").write_text(
            (exc.stderr or "") + "\nTIMEOUT",
            encoding="utf-8",
        )
        return JobRunResult(
            exit_code=124,
            command=command,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            artifact_dir=str(job_artifact_dir),
            artifacts_present=[],
            artifacts_missing=list(EXPECTED_SCENARIO_ARTIFACTS),
            artifacts_complete=False,
            scenario_metrics={},
            error_classification="RUNNER_TIMEOUT",
        )

    (job_artifact_dir / "stdout.log").write_text(completed.stdout or "", encoding="utf-8")
    (job_artifact_dir / "stderr.log").write_text(completed.stderr or "", encoding="utf-8")
    (job_artifact_dir / "command.json").write_text(
        json.dumps(
            {
                "command": command,
                "job_id": job.get("job_id"),
                "scenario_group_id": resolve_scenario_group_id(job),
                "fingerprint": job.get("fingerprint"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    scenario_group_id = resolve_scenario_group_id(job)
    group_dir = resolve_replay_group_dir(replay_output_dir, scenario_group_id)

    present, missing, complete = _collect_artifact_status(group_dir)
    metrics = _load_scenario_metrics(group_dir) if group_dir.exists() else {}

    error_classification: str | None = None
    if completed.returncode != 0:
        error_classification = "RUNNER_EXIT_NONZERO"
    elif not complete:
        error_classification = "ARTIFACT_INCOMPLETE"

    return JobRunResult(
        exit_code=int(completed.returncode),
        command=command,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        artifact_dir=str(job_artifact_dir),
        artifacts_present=present,
        artifacts_missing=missing,
        artifacts_complete=complete,
        scenario_metrics=metrics,
        error_classification=error_classification,
    )
