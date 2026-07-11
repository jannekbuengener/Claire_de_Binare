from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from core.utils.clock import utcnow as cdb_utcnow

from .contract import (
    EVIDENCE_CLASS_CONTROLLED,
    JOB_FAIL,
    JOB_FATAL_STOP,
    JOB_INSUFFICIENT_DATA,
    JOB_INTERRUPTED,
    JOB_PASS,
    JOB_PENDING,
    JOB_RUNNING,
    JOB_SKIPPED_DUPLICATE,
    STRATEGY_PARKED,
    TERMINAL_JOB_STATUSES,
    VacationContractError,
    VacationManifest,
    build_job_fingerprint,
    build_job_id,
    campaign_artifact_dir,
    discover_datasets,
    git_head_sha,
    load_manifest,
    resolve_source_sha,
)
from .job_runner import JobRunResult, run_replay_job
from .queue_store import (
    HEARTBEAT_FILENAME,
    QUEUE_EVENTS_FILENAME,
    QUEUE_STATE_FILENAME,
    completed_fingerprints,
    emit_event,
    job_dir,
    known_time_windows,
    read_queue_state,
    recover_orphan_running_jobs,
    write_heartbeat,
    write_queue_state,
)

CAMPAIGN_RUNNING = "running"
CAMPAIGN_COMPLETED = "completed"
CAMPAIGN_FATAL_STOP = "fatal_stop"


def _now_utc_iso() -> str:
    now = cdb_utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return now.astimezone(UTC).isoformat().replace("+00:00", "Z")


def default_disk_probe(path: Path) -> float:
    usage = shutil.disk_usage(path)
    return usage.free / (1024**3)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _new_job_record(
    manifest: VacationManifest,
    *,
    strategy_id: str,
    strategy_role: str,
    dataset: Mapping[str, Any],
) -> dict[str, Any]:
    fingerprint = build_job_fingerprint(
        source_sha=manifest.source_sha,
        strategy_id=strategy_id,
        dataset_fingerprint=str(dataset["dataset_fingerprint"]),
        scenarios=manifest.scenarios,
        speedup_profile=manifest.speedup_profile,
    )
    job_id = build_job_id(strategy_id, str(dataset["dataset_id"]))
    return {
        "job_id": job_id,
        "fingerprint": fingerprint,
        "strategy_id": strategy_id,
        "strategy_role": strategy_role,
        "dataset_id": dataset["dataset_id"],
        "dataset_dir": dataset["dataset_dir"],
        "spec_path": dataset["spec_path"],
        "input_candles": dataset["input_candles"],
        "dataset_fingerprint": dataset["dataset_fingerprint"],
        "start_ts_ms": dataset.get("start_ts_ms"),
        "end_ts_ms": dataset.get("end_ts_ms"),
        "symbol": dataset.get("symbol"),
        "scenarios": list(manifest.scenarios),
        "status": JOB_PENDING,
        "attempts": 0,
        "max_attempts": manifest.max_attempts_per_job,
        "started_at_utc": None,
        "finished_at_utc": None,
        "exit_code": None,
        "artifact_dir": None,
        "command": None,
        "error_classification": None,
        "artifacts_complete": False,
        "artifacts_present": [],
        "artifacts_missing": [],
        "evidence_class": EVIDENCE_CLASS_CONTROLLED,
        "ranking_ready": False,
    }


def _dataset_to_dict(record: Any) -> dict[str, Any]:
    return {
        "dataset_id": record.dataset_id,
        "dataset_dir": record.dataset_dir,
        "spec_path": record.spec_path,
        "input_candles": record.input_candles,
        "dataset_fingerprint": record.dataset_fingerprint,
        "start_ts_ms": record.start_ts_ms,
        "end_ts_ms": record.end_ts_ms,
        "symbol": record.symbol,
    }


def _dataset_record_id(record: Any) -> str:
    if isinstance(record, dict):
        return str(record.get("dataset_id", ""))
    return str(record.dataset_id)


def _parked_anchor_dataset_id(datasets: Sequence[Any]) -> str | None:
    if not datasets:
        return None
    for record in datasets:
        dataset_id = _dataset_record_id(record)
        if "strict" in dataset_id.lower() or "3091" in dataset_id:
            return dataset_id
    return _dataset_record_id(datasets[0])


def _should_schedule_job(strategy_role: str, dataset_id: str, datasets: Sequence[Any]) -> bool:
    if strategy_role != STRATEGY_PARKED:
        return True
    anchor = _parked_anchor_dataset_id(datasets)
    return anchor is not None and dataset_id == anchor


def initialize_queue_state(
    manifest: VacationManifest,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    root = repo_root or _repo_root()
    datasets = discover_datasets(
        manifest,
        root,
        exclude_time_windows=set(),
    )
    jobs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for dataset in datasets:
        ds_dict = _dataset_to_dict(dataset)
        for strategy in manifest.strategies:
            if not _should_schedule_job(strategy.role, ds_dict["dataset_id"], datasets):
                continue
            job = _new_job_record(
                manifest,
                strategy_id=strategy.strategy_id,
                strategy_role=strategy.role,
                dataset=ds_dict,
            )
            fp = job["fingerprint"]
            if fp in seen:
                job["status"] = JOB_SKIPPED_DUPLICATE
                job["error_classification"] = "DUPLICATE_FINGERPRINT"
                job["finished_at_utc"] = _now_utc_iso()
            else:
                seen.add(fp)
            jobs.append(job)
    return {
        "campaign_id": manifest.campaign_id,
        "source_sha": manifest.source_sha,
        "evidence_class": manifest.evidence_class,
        "campaign_status": CAMPAIGN_RUNNING,
        "completed_fingerprints": [],
        "jobs": jobs,
        "datasets_discovered": len(datasets),
    }


def sync_new_jobs(
    state: dict[str, Any],
    manifest: VacationManifest,
    repo_root: Path,
) -> dict[str, Any]:
    existing_fps = completed_fingerprints(state)
    for job in state.get("jobs") or []:
        if isinstance(job, dict) and isinstance(job.get("fingerprint"), str):
            existing_fps.add(job["fingerprint"].lower())
    datasets = discover_datasets(
        manifest,
        repo_root,
        exclude_fingerprints=existing_fps,
        exclude_time_windows=known_time_windows(state),
    )
    known_job_ids = {
        str(j.get("job_id"))
        for j in state.get("jobs") or []
        if isinstance(j, dict) and j.get("job_id")
    }
    for dataset in datasets:
        ds_dict = _dataset_to_dict(dataset)
        for strategy in manifest.strategies:
            if not _should_schedule_job(strategy.role, ds_dict["dataset_id"], datasets):
                continue
            job = _new_job_record(
                manifest,
                strategy_id=strategy.strategy_id,
                strategy_role=strategy.role,
                dataset=ds_dict,
            )
            if job["job_id"] in known_job_ids:
                continue
            fp = job["fingerprint"]
            if fp in existing_fps:
                job["status"] = JOB_SKIPPED_DUPLICATE
                job["error_classification"] = "DUPLICATE_FINGERPRINT"
                job["finished_at_utc"] = _now_utc_iso()
            state.setdefault("jobs", []).append(job)
            known_job_ids.add(job["job_id"])
    return state


def _find_job(state: dict[str, Any], job_id: str) -> dict[str, Any] | None:
    for job in state.get("jobs") or []:
        if isinstance(job, dict) and job.get("job_id") == job_id:
            return job
    return None


def _next_runnable_job(state: dict[str, Any]) -> dict[str, Any] | None:
    for job in state.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        status = job.get("status")
        if status == JOB_PENDING:
            return job
        if status == JOB_INTERRUPTED:
            attempts = int(job.get("attempts") or 0)
            max_attempts = int(job.get("max_attempts") or 1)
            if attempts < max_attempts:
                job["status"] = JOB_PENDING
                return job
    return None


def _apply_run_result(job: dict[str, Any], result: JobRunResult) -> None:
    job["exit_code"] = result.exit_code
    job["command"] = result.command
    job["artifact_dir"] = result.artifact_dir
    job["artifacts_present"] = result.artifacts_present
    job["artifacts_missing"] = result.artifacts_missing
    job["artifacts_complete"] = result.artifacts_complete
    job["scenario_metrics"] = result.scenario_metrics
    job["finished_at_utc"] = _now_utc_iso()
    job["error_classification"] = result.error_classification
    if result.exit_code == 0 and result.artifacts_complete:
        job["status"] = JOB_PASS
    else:
        job["status"] = JOB_FAIL


def _manifest_for_run(manifest: VacationManifest, repo_root: Path) -> VacationManifest:
    resolved_sha = resolve_source_sha(manifest, repo_root)
    if resolved_sha == manifest.source_sha:
        return manifest
    return VacationManifest(
        schema_version=manifest.schema_version,
        campaign_id=manifest.campaign_id,
        source_sha=resolved_sha,
        evidence_class=manifest.evidence_class,
        artifact_root=manifest.artifact_root,
        dataset_roots=manifest.dataset_roots,
        strategies=manifest.strategies,
        scenarios=manifest.scenarios,
        max_job_runtime_seconds=manifest.max_job_runtime_seconds,
        max_attempts_per_job=manifest.max_attempts_per_job,
        min_free_disk_gb=manifest.min_free_disk_gb,
        allow_paper_jobs=manifest.allow_paper_jobs,
        speedup_profile=manifest.speedup_profile,
        symbol=manifest.symbol,
    )


def run_coordinator_cycle(
    *,
    manifest_path: Path,
    repo_root: Path | None = None,
    resume: bool = False,
    disk_probe: Callable[[Path], float] | None = None,
    subprocess_runner: Callable[..., Any] | None = None,
    now_fn: Callable[[], str] | None = None,
) -> dict[str, Any]:
    root = repo_root or _repo_root()
    manifest = _manifest_for_run(load_manifest(manifest_path), root)
    manifest.validate_preflight()

    campaign_dir = campaign_artifact_dir(manifest, root)
    campaign_dir.mkdir(parents=True, exist_ok=True)
    state_path = campaign_dir / QUEUE_STATE_FILENAME
    events_path = campaign_dir / QUEUE_EVENTS_FILENAME
    heartbeat_path = campaign_dir / HEARTBEAT_FILENAME

    probe = disk_probe or default_disk_probe
    free_gb = probe(root)
    if free_gb < manifest.min_free_disk_gb:
        fatal_state = {
            "campaign_id": manifest.campaign_id,
            "source_sha": manifest.source_sha,
            "campaign_status": CAMPAIGN_FATAL_STOP,
            "fatal_reason": "DISK_BELOW_MINIMUM",
            "free_disk_gb": free_gb,
            "jobs": [],
        }
        write_queue_state(state_path, fatal_state, pretty=True)
        emit_event(
            events_path,
            campaign_id=manifest.campaign_id,
            event_type="fatal_stop",
            details={"reason": "DISK_BELOW_MINIMUM", "free_disk_gb": free_gb},
            now_fn=now_fn,
        )
        return fatal_state

    if state_path.exists() and resume:
        state = read_queue_state(state_path)
        state, interrupted = recover_orphan_running_jobs(state, now_fn=now_fn)
        for job_id in interrupted:
            emit_event(
                events_path,
                campaign_id=manifest.campaign_id,
                event_type="job_interrupted",
                job_id=job_id,
                now_fn=now_fn,
            )
    elif state_path.exists():
        state = read_queue_state(state_path)
    else:
        state = initialize_queue_state(manifest, root)
        emit_event(
            events_path,
            campaign_id=manifest.campaign_id,
            event_type="campaign_initialized",
            details={"job_count": len(state.get("jobs") or [])},
            now_fn=now_fn,
        )

    state = sync_new_jobs(state, manifest, root)

    if state.get("campaign_status") == CAMPAIGN_FATAL_STOP:
        write_queue_state(state_path, state, pretty=True)
        return state

    job = _next_runnable_job(state)
    if job is None:
        state["campaign_status"] = CAMPAIGN_COMPLETED
        write_queue_state(state_path, state, pretty=True)
        write_heartbeat(
            heartbeat_path,
            {
                "campaign_id": manifest.campaign_id,
                "campaign_status": CAMPAIGN_COMPLETED,
                "last_job_id": None,
            },
        )
        emit_event(
            events_path,
            campaign_id=manifest.campaign_id,
            event_type="campaign_completed",
            now_fn=now_fn,
        )
        return state

    fingerprint = str(job.get("fingerprint", "")).lower()
    if fingerprint in completed_fingerprints(state):
        job["status"] = JOB_SKIPPED_DUPLICATE
        job["error_classification"] = "DUPLICATE_FINGERPRINT"
        job["finished_at_utc"] = (now_fn or _now_utc_iso)()
        write_queue_state(state_path, state, pretty=True)
        emit_event(
            events_path,
            campaign_id=manifest.campaign_id,
            event_type="job_skipped_duplicate",
            job_id=str(job.get("job_id")),
            now_fn=now_fn,
        )
        return state

    job_id = str(job["job_id"])
    job["status"] = JOB_RUNNING
    job["attempts"] = int(job.get("attempts") or 0) + 1
    job["started_at_utc"] = (now_fn or _now_utc_iso)()
    job_artifact = job_dir(campaign_dir, job_id)
    job["artifact_dir"] = str(job_artifact.relative_to(root)).replace("\\", "/")
    write_queue_state(state_path, state, pretty=True)
    emit_event(
        events_path,
        campaign_id=manifest.campaign_id,
        event_type="job_started",
        job_id=job_id,
        details={"attempt": job["attempts"]},
        now_fn=now_fn,
    )

    try:
        result = run_replay_job(
            repo_root=root,
            manifest=manifest,
            job=job,
            job_artifact_dir=job_artifact,
            timeout_seconds=manifest.max_job_runtime_seconds,
            subprocess_runner=subprocess_runner,
        )
    except VacationContractError as exc:
        job["status"] = JOB_INSUFFICIENT_DATA
        job["error_classification"] = "DATASET_INVALID"
        job["finished_at_utc"] = (now_fn or _now_utc_iso)()
        job["exit_code"] = 2
        write_queue_state(state_path, state, pretty=True)
        emit_event(
            events_path,
            campaign_id=manifest.campaign_id,
            event_type="job_insufficient_data",
            job_id=job_id,
            details={"error": str(exc)},
            now_fn=now_fn,
        )
        write_heartbeat(
            heartbeat_path,
            {
                "campaign_id": manifest.campaign_id,
                "campaign_status": CAMPAIGN_RUNNING,
                "last_job_id": job_id,
            },
        )
        return state

    _apply_run_result(job, result)
    if job["status"] == JOB_PASS:
        fps = list(state.get("completed_fingerprints") or [])
        fps.append(fingerprint)
        state["completed_fingerprints"] = sorted(set(fps))

    pending = _next_runnable_job(state)
    state["campaign_status"] = CAMPAIGN_COMPLETED if pending is None else CAMPAIGN_RUNNING
    write_queue_state(state_path, state, pretty=True)
    write_heartbeat(
        heartbeat_path,
        {
            "campaign_id": manifest.campaign_id,
            "campaign_status": state["campaign_status"],
            "last_job_id": job_id,
            "last_job_status": job["status"],
        },
    )
    emit_event(
        events_path,
        campaign_id=manifest.campaign_id,
        event_type="job_finished",
        job_id=job_id,
        details={
            "status": job["status"],
            "exit_code": job.get("exit_code"),
            "error_classification": job.get("error_classification"),
        },
        now_fn=now_fn,
    )
    return state


def run_until_complete(
    *,
    manifest_path: Path,
    repo_root: Path | None = None,
    resume: bool = False,
    max_cycles: int | None = None,
    disk_probe: Callable[[Path], float] | None = None,
    subprocess_runner: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    root = repo_root or _repo_root()
    cycles = 0
    state: dict[str, Any] = {}
    while True:
        state = run_coordinator_cycle(
            manifest_path=manifest_path,
            repo_root=root,
            resume=resume or cycles > 0,
            disk_probe=disk_probe,
            subprocess_runner=subprocess_runner,
        )
        cycles += 1
        if max_cycles is not None and cycles >= max_cycles:
            break
        if state.get("campaign_status") in {CAMPAIGN_COMPLETED, CAMPAIGN_FATAL_STOP}:
            break
        if _next_runnable_job(state) is None:
            break
    return state


def preflight_manifest(manifest_path: Path, repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or _repo_root()
    manifest = _manifest_for_run(load_manifest(manifest_path), root)
    manifest.validate_preflight()
    datasets = discover_datasets(manifest, root)
    active_strategies = sum(1 for s in manifest.strategies if s.role != STRATEGY_PARKED)
    parked_strategies = sum(1 for s in manifest.strategies if s.role == STRATEGY_PARKED)
    job_estimate = len(datasets) * active_strategies + (1 if parked_strategies else 0)
    return {
        "campaign_id": manifest.campaign_id,
        "source_sha": manifest.source_sha,
        "dataset_count": len(datasets),
        "datasets": [d.dataset_id for d in datasets],
        "job_count_estimate": job_estimate,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="ARVP Vacation Autopilot MVP coordinator")
    parser.add_argument("--manifest", required=True, help="Path to vacation manifest YAML")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--once", action="store_true", help="Run a single coordinator cycle")
    parser.add_argument("--run-until-complete", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--write-summary", action="store_true")
    parser.add_argument("--max-cycles", type=int, default=None)
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    root = _repo_root()
    manifest = _manifest_for_run(load_manifest(manifest_path), root)

    if args.preflight_only:
        info = preflight_manifest(manifest_path, root)
        print(json.dumps(info, indent=2))
        return 0

    if args.run_until_complete:
        state = run_until_complete(
            manifest_path=manifest_path,
            repo_root=root,
            resume=args.resume,
            max_cycles=args.max_cycles,
        )
    elif args.once:
        state = run_coordinator_cycle(
            manifest_path=manifest_path,
            repo_root=root,
            resume=args.resume,
        )
    else:
        parser.error("Specify --once, --run-until-complete, or --preflight-only")

    if args.write_summary or args.run_until_complete:
        from .summary import write_summary

        write_summary(manifest, state, root)
    print(json.dumps({"campaign_status": state.get("campaign_status")}, indent=2))
    if state.get("campaign_status") == CAMPAIGN_FATAL_STOP:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
