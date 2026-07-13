from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from core.utils.clock import utcnow as cdb_utcnow

from .contract import git_head_sha
from .data_capture_contract import (
    DATA_CAPTURE_GO_PHRASE,
    RUNTIME_RESOLVE,
    DataCaptureContractError,
    DataCaptureManifest,
    classify_running_services,
    load_data_capture_manifest,
    resolve_runtime_window,
    resolve_source_sha,
    validate_end_matches_start,
)

CAMPAIGN_STATE_FILENAME = "campaign_state.json"
CAMPAIGN_EVENTS_FILENAME = "campaign_events.jsonl"
HEARTBEAT_FILENAME = "heartbeat.json"
SERVICE_INVENTORY_FILENAME = "service_inventory.json"
COVERAGE_SNAPSHOTS_FILENAME = "coverage_snapshots.jsonl"

CAMPAIGN_PLANNED = "planned"
CAMPAIGN_RUNNING = "running"
CAMPAIGN_STOPPED = "stopped"
CAMPAIGN_COMPLETED = "completed"
CAMPAIGN_BLOCKED = "blocked"

DockerRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]
ContainerLister = Callable[[], list[str]]
CoverageProbe = Callable[[Path, str, int | None], dict[str, Any]]
GitStatusProbe = Callable[[Path], str]
DiskProbe = Callable[[Path], float]


class DataCaptureError(RuntimeError):
    pass


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _now_utc_iso() -> str:
    now = cdb_utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return now.astimezone(UTC).isoformat().replace("+00:00", "Z")


def default_disk_probe(path: Path) -> float:
    usage = shutil.disk_usage(path)
    return usage.free / (1024**3)


def default_docker_runner(args: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def default_container_lister() -> list[str]:
    result = default_docker_runner(
        ["docker", "ps", "--format", "{{.Names}}"],
        _repo_root(),
    )
    if result.returncode != 0:
        raise DataCaptureError(result.stderr.strip() or "docker ps failed")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def default_git_status_probe(repo_root: Path) -> str:
    result = default_docker_runner(["git", "status", "--porcelain"], repo_root)
    if result.returncode != 0:
        return "unknown"
    return "clean" if not result.stdout.strip() else "dirty"


def default_coverage_probe(
    repo_root: Path, symbol: str, start_ts_ms: int | None
) -> dict[str, Any]:
    dsn = os.environ.get("POSTGRES_READONLY_PASSWORD_DSN", "").strip()
    if not dsn:
        return {
            "available": False,
            "reason": "POSTGRES_READONLY_PASSWORD_DSN not set",
        }
    try:
        import psycopg2

        with psycopg2.connect(dsn) as conn:
            with conn.cursor() as cur:
                if start_ts_ms is not None:
                    cur.execute(
                        """
                        SELECT COUNT(*), MIN(ts_ms), MAX(ts_ms)
                        FROM public.candles_1m
                        WHERE symbol = %s AND ts_ms >= %s
                        """,
                        (symbol, start_ts_ms),
                    )
                else:
                    cur.execute(
                        """
                        SELECT COUNT(*), MIN(ts_ms), MAX(ts_ms)
                        FROM public.candles_1m
                        WHERE symbol = %s
                        """,
                        (symbol,),
                    )
                count, min_ts, max_ts = cur.fetchone()
        return {
            "available": True,
            "candle_count": int(count or 0),
            "min_ts_ms": int(min_ts) if min_ts is not None else None,
            "max_ts_ms": int(max_ts) if max_ts is not None else None,
        }
    except Exception as exc:  # noqa: BLE001 — probe must not crash status
        return {"available": False, "reason": str(exc)}


def _campaign_dir(manifest: DataCaptureManifest, repo_root: Path) -> Path:
    return manifest.campaign_artifact_dir(repo_root)


def _append_event(campaign_dir: Path, event_type: str, payload: Mapping[str, Any]) -> None:
    campaign_dir.mkdir(parents=True, exist_ok=True)
    record = {"ts_utc": _now_utc_iso(), "event_type": event_type, **dict(payload)}
    path = campaign_dir / CAMPAIGN_EVENTS_FILENAME
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_campaign_state(campaign_dir: Path) -> dict[str, Any] | None:
    path = campaign_dir / CAMPAIGN_STATE_FILENAME
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def verify_go_phrase(provided: str | None) -> None:
    expected = DATA_CAPTURE_GO_PHRASE
    actual = (provided or os.environ.get("CDB_DATA_CAPTURE_GO", "")).strip()
    if actual != expected:
        raise DataCaptureError(
            "Start blocked: exact DATA-CAPTURE-GO phrase required. "
            f"Expected: {expected!r}"
        )


def build_preflight_report(
    manifest: DataCaptureManifest,
    *,
    repo_root: Path | None = None,
    docker_runner: DockerRunner = default_docker_runner,
    container_lister: ContainerLister = default_container_lister,
    git_status_probe: GitStatusProbe = default_git_status_probe,
    disk_probe: DiskProbe = default_disk_probe,
    coverage_probe: CoverageProbe = default_coverage_probe,
    skip_docker: bool = False,
) -> dict[str, Any]:
    root = repo_root or _repo_root()
    manifest.validate_preflight()
    head = git_head_sha(root)
    resolved_sha = resolve_source_sha(manifest, root)
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "ok": ok, "detail": detail})

    pinned = (manifest.source_sha or "").strip().upper()
    if pinned in {RUNTIME_RESOLVE, "AUTO", ""}:
        add(
            "git_head_matches_manifest",
            True,
            f"HEAD={head} (RUNTIME_RESOLVE at GO)",
        )
    else:
        add(
            "git_head_matches_manifest",
            head == manifest.source_sha.strip(),
            f"HEAD={head} manifest.source_sha={manifest.source_sha}",
        )
    wt = git_status_probe(root)
    add("working_tree_clean", wt == "clean", f"working_tree={wt}")
    free_gb = disk_probe(root)
    add(
        "disk_space",
        free_gb >= manifest.min_free_disk_gb,
        f"free_gb={free_gb:.2f} required={manifest.min_free_disk_gb}",
    )
    add(
        "campaign_id_unique",
        not (manifest.campaign_artifact_dir(root).exists()
             and (manifest.campaign_artifact_dir(root) / CAMPAIGN_STATE_FILENAME).exists()),
        f"campaign_dir={manifest.campaign_artifact_dir(root)}",
    )
    add("allow_signal_false", not manifest.allow_signal, "ok")
    add("allow_execution_false", not manifest.allow_execution, "ok")
    add("allow_paper_false", not manifest.allow_paper, "ok")
    add("allow_live_trading_false", not manifest.allow_live_trading, "ok")

    if manifest.start_utc.upper() not in {"RUNTIME_RESOLVE", "AUTO", ""}:
        try:
            validate_end_matches_start(
                manifest.start_utc,
                manifest.planned_end_utc,
                manifest.max_duration_days,
            )
            add("planned_end_exact_14d", True, "start/end window validated")
        except DataCaptureContractError as exc:
            add("planned_end_exact_14d", False, str(exc))
    else:
        add("planned_end_exact_14d", True, "deferred until runtime GO")

    docker_ok = False
    docker_detail = "skipped"
    forbidden_running: list[str] = []
    if not skip_docker:
        ping = docker_runner(["docker", "info"], root)
        docker_ok = ping.returncode == 0
        docker_detail = "reachable" if docker_ok else (ping.stderr.strip() or "unreachable")
        if docker_ok:
            try:
                running = container_lister()
                classified = classify_running_services(
                    running,
                    allowed=manifest.allowed_services,
                    forbidden=manifest.forbidden_services,
                )
                forbidden_running = classified["running_forbidden"]
                add(
                    "no_forbidden_services_running",
                    not forbidden_running,
                    f"forbidden={forbidden_running}",
                )
            except DataCaptureError as exc:
                add("no_forbidden_services_running", False, str(exc))
    add("docker_reachable", docker_ok or skip_docker, docker_detail)

    coverage = coverage_probe(root, manifest.symbol, None)
    add(
        "coverage_probe_available",
        coverage.get("available", False) or skip_docker,
        coverage.get("reason", "ok"),
    )

    failed = [c for c in checks if not c["ok"]]
    return {
        "campaign_id": manifest.campaign_id,
        "source_sha": resolved_sha,
        "checks": checks,
        "passed": not failed,
        "failed_checks": [c["check"] for c in failed],
        "forbidden_services_running": forbidden_running,
        "coverage_probe": coverage,
        "verdict": "PREFLIGHT_PASS" if not failed else "PREFLIGHT_FAIL",
    }


def compose_up_allowed(
    manifest: DataCaptureManifest,
    repo_root: Path,
    *,
    docker_runner: DockerRunner = default_docker_runner,
) -> dict[str, Any]:
    blue = repo_root / manifest.compose_blue
    red = repo_root / manifest.compose_red
    blue_services = [s for s in manifest.allowed_services if s != "cdb_ws"]
    red_services = [s for s in manifest.allowed_services if s == "cdb_ws"]
    results: list[dict[str, Any]] = []
    if blue_services:
        cmd = [
            "docker",
            "compose",
            "-f",
            str(blue.relative_to(repo_root)).replace("\\", "/"),
            "up",
            "-d",
            *blue_services,
        ]
        proc = docker_runner(cmd, repo_root)
        results.append(
            {
                "compose": str(blue),
                "services": blue_services,
                "returncode": proc.returncode,
                "stderr": proc.stderr.strip(),
            }
        )
        if proc.returncode != 0:
            raise DataCaptureError(proc.stderr.strip() or "blue compose up failed")
    if red_services:
        cmd = [
            "docker",
            "compose",
            "-f",
            str(red.relative_to(repo_root)).replace("\\", "/"),
            "up",
            "-d",
            *red_services,
        ]
        proc = docker_runner(cmd, repo_root)
        results.append(
            {
                "compose": str(red),
                "services": red_services,
                "returncode": proc.returncode,
                "stderr": proc.stderr.strip(),
            }
        )
        if proc.returncode != 0:
            raise DataCaptureError(proc.stderr.strip() or "red compose up failed")
    return {"compose_results": results}


def compose_stop_allowed(
    manifest: DataCaptureManifest,
    repo_root: Path,
    *,
    docker_runner: DockerRunner = default_docker_runner,
) -> dict[str, Any]:
    blue = repo_root / manifest.compose_blue
    red = repo_root / manifest.compose_red
    results: list[dict[str, Any]] = []
    for compose_path, services in (
        (red, [s for s in manifest.allowed_services if s == "cdb_ws"]),
        (blue, [s for s in manifest.allowed_services if s != "cdb_ws"]),
    ):
        if not services:
            continue
        cmd = [
            "docker",
            "compose",
            "-f",
            str(compose_path.relative_to(repo_root)).replace("\\", "/"),
            "stop",
            *services,
        ]
        proc = docker_runner(cmd, repo_root)
        results.append(
            {
                "compose": str(compose_path),
                "services": services,
                "returncode": proc.returncode,
                "stderr": proc.stderr.strip(),
            }
        )
    return {"compose_results": results}


def build_status_report(
    manifest: DataCaptureManifest,
    *,
    repo_root: Path | None = None,
    container_lister: ContainerLister = default_container_lister,
    disk_probe: DiskProbe = default_disk_probe,
    coverage_probe: CoverageProbe = default_coverage_probe,
) -> dict[str, Any]:
    root = repo_root or _repo_root()
    campaign_dir = _campaign_dir(manifest, root)
    state = read_campaign_state(campaign_dir) or {}
    running = container_lister()
    classified = classify_running_services(
        running,
        allowed=manifest.allowed_services,
        forbidden=manifest.forbidden_services,
    )
    start_ts_ms = state.get("start_ts_ms")
    coverage = coverage_probe(root, manifest.symbol, start_ts_ms)
    now_ms = int(cdb_utcnow().timestamp() * 1000)
    stale = False
    last_ts = coverage.get("max_ts_ms")
    if last_ts is not None and state.get("status") == CAMPAIGN_RUNNING:
        stale = (now_ms - int(last_ts)) > manifest.stale_threshold_seconds * 1000

    verdict = state.get("status", CAMPAIGN_PLANNED)
    if classified["running_forbidden"]:
        verdict = CAMPAIGN_BLOCKED
    elif stale and state.get("status") == CAMPAIGN_RUNNING:
        verdict = "stale"

    return {
        "campaign_id": manifest.campaign_id,
        "start_utc": state.get("start_utc"),
        "planned_end_utc": state.get("planned_end_utc"),
        "status": state.get("status", CAMPAIGN_PLANNED),
        "running_allowed_services": classified["running_allowed"],
        "running_forbidden_services": classified["running_forbidden"],
        "running_unexpected_services": classified["running_unexpected"],
        "last_candle_ts_ms": last_ts,
        "new_candles_since_start": coverage.get("candle_count"),
        "gap_stale_status": "stale" if stale else "ok",
        "db_writer_running": "cdb_db_writer" in classified["running_allowed"],
        "free_disk_gb": round(disk_probe(root), 2),
        "restart_count": state.get("restart_count", 0),
        "campaign_verdict": verdict,
        "coverage_probe": coverage,
    }


def start_campaign(
    manifest: DataCaptureManifest,
    *,
    repo_root: Path | None = None,
    go_phrase: str | None = None,
    docker_runner: DockerRunner = default_docker_runner,
    container_lister: ContainerLister = default_container_lister,
    git_status_probe: GitStatusProbe = default_git_status_probe,
    disk_probe: DiskProbe = default_disk_probe,
    coverage_probe: CoverageProbe = default_coverage_probe,
    skip_docker: bool = False,
) -> dict[str, Any]:
    verify_go_phrase(go_phrase)
    root = repo_root or _repo_root()
    preflight = build_preflight_report(
        manifest,
        repo_root=root,
        docker_runner=docker_runner,
        container_lister=container_lister,
        git_status_probe=git_status_probe,
        disk_probe=disk_probe,
        coverage_probe=coverage_probe,
        skip_docker=skip_docker,
    )
    if not preflight["passed"]:
        raise DataCaptureError(
            f"preflight failed: {preflight['failed_checks']}"
        )

    start_utc, planned_end_utc = resolve_runtime_window(manifest)
    validate_end_matches_start(start_utc, planned_end_utc, manifest.max_duration_days)
    start_dt = datetime.fromisoformat(start_utc.replace("Z", "+00:00"))
    start_ts_ms = int(start_dt.timestamp() * 1000)

    campaign_dir = _campaign_dir(manifest, root)
    compose_result: dict[str, Any] = {}
    if not skip_docker:
        compose_result = compose_up_allowed(manifest, root, docker_runner=docker_runner)
        running = container_lister()
        classified = classify_running_services(
            running,
            allowed=manifest.allowed_services,
            forbidden=manifest.forbidden_services,
        )
        if classified["running_forbidden"]:
            raise DataCaptureError(
                f"forbidden services running after start: {classified['running_forbidden']}"
            )

    state = {
        "schema_version": "1.0",
        "campaign_id": manifest.campaign_id,
        "source_sha": resolve_source_sha(manifest, root),
        "status": CAMPAIGN_RUNNING,
        "start_utc": start_utc,
        "planned_end_utc": planned_end_utc,
        "start_ts_ms": start_ts_ms,
        "restart_count": 0,
        "allowed_services": list(manifest.allowed_services),
        "forbidden_services": list(manifest.forbidden_services),
    }
    _write_json(campaign_dir / CAMPAIGN_STATE_FILENAME, state)
    _write_json(
        campaign_dir / SERVICE_INVENTORY_FILENAME,
        classify_running_services(
            container_lister() if not skip_docker else [],
            allowed=manifest.allowed_services,
            forbidden=manifest.forbidden_services,
        ),
    )
    _append_event(campaign_dir, "campaign_start", {"state": state})
    if compose_result:
        _append_event(campaign_dir, "services_started", compose_result)

    coverage = coverage_probe(root, manifest.symbol, start_ts_ms)
    _write_json(
        campaign_dir / HEARTBEAT_FILENAME,
        {
            "ts_utc": _now_utc_iso(),
            "coverage": coverage,
            "free_disk_gb": round(disk_probe(root), 2),
        },
    )
    with (campaign_dir / COVERAGE_SNAPSHOTS_FILENAME).open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {"ts_utc": _now_utc_iso(), "coverage": coverage}, sort_keys=True
            )
            + "\n"
        )

    return {
        "status": CAMPAIGN_RUNNING,
        "campaign_dir": str(campaign_dir),
        "start_utc": start_utc,
        "planned_end_utc": planned_end_utc,
        "compose": compose_result,
    }


def stop_campaign(
    manifest: DataCaptureManifest,
    *,
    repo_root: Path | None = None,
    docker_runner: DockerRunner = default_docker_runner,
    skip_docker: bool = False,
) -> dict[str, Any]:
    root = repo_root or _repo_root()
    campaign_dir = _campaign_dir(manifest, root)
    state = read_campaign_state(campaign_dir) or {}
    compose_result: dict[str, Any] = {}
    if not skip_docker:
        compose_result = compose_stop_allowed(manifest, root, docker_runner=docker_runner)
    state["status"] = CAMPAIGN_STOPPED
    state["stopped_utc"] = _now_utc_iso()
    _write_json(campaign_dir / CAMPAIGN_STATE_FILENAME, state)
    _append_event(campaign_dir, "campaign_stop", {"compose": compose_result})
    return {"status": CAMPAIGN_STOPPED, "compose": compose_result}


def resume_campaign(
    manifest: DataCaptureManifest,
    *,
    repo_root: Path | None = None,
    go_phrase: str | None = None,
    docker_runner: DockerRunner = default_docker_runner,
    container_lister: ContainerLister = default_container_lister,
    skip_docker: bool = False,
) -> dict[str, Any]:
    verify_go_phrase(go_phrase)
    root = repo_root or _repo_root()
    campaign_dir = _campaign_dir(manifest, root)
    state = read_campaign_state(campaign_dir)
    if not state:
        raise DataCaptureError("no campaign state; use Start first")
    if state.get("status") == CAMPAIGN_COMPLETED:
        raise DataCaptureError("campaign already completed")
    restart_count = int(state.get("restart_count", 0)) + 1
    if restart_count > manifest.max_restart_budget:
        raise DataCaptureError(
            f"restart budget exhausted ({restart_count}>{manifest.max_restart_budget})"
        )
    planned_end = state.get("planned_end_utc", "")
    if planned_end:
        end_dt = datetime.fromisoformat(planned_end.replace("Z", "+00:00"))
        now = cdb_utcnow()
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        if now.astimezone(UTC) >= end_dt.astimezone(UTC):
            raise DataCaptureError("campaign planned_end_utc has passed")

    running = container_lister() if not skip_docker else []
    classified = classify_running_services(
        running,
        allowed=manifest.allowed_services,
        forbidden=manifest.forbidden_services,
    )
    if classified["running_forbidden"]:
        raise DataCaptureError(
            f"forbidden services running: {classified['running_forbidden']}"
        )

    compose_result: dict[str, Any] = {}
    if not skip_docker:
        compose_result = compose_up_allowed(manifest, root, docker_runner=docker_runner)

    state["status"] = CAMPAIGN_RUNNING
    state["restart_count"] = restart_count
    state["last_resume_utc"] = _now_utc_iso()
    _write_json(campaign_dir / CAMPAIGN_STATE_FILENAME, state)
    _append_event(
        campaign_dir,
        "campaign_resume",
        {"restart_count": restart_count, "compose": compose_result},
    )
    return {
        "status": CAMPAIGN_RUNNING,
        "restart_count": restart_count,
        "compose": compose_result,
    }


def preflight_manifest(manifest_path: Path, repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or _repo_root()
    manifest = load_data_capture_manifest(manifest_path)
    return build_preflight_report(manifest, repo_root=root)


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ARVP vacation data capture (#3990)")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--start", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--go-phrase", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--skip-docker", action="store_true")
    args = parser.parse_args(argv)

    root = _repo_root()
    manifest = load_data_capture_manifest(args.manifest)

    try:
        if args.preflight_only:
            report = build_preflight_report(
                manifest, repo_root=root, skip_docker=args.skip_docker
            )
        elif args.status:
            report = build_status_report(manifest, repo_root=root)
        elif args.start:
            report = start_campaign(
                manifest,
                repo_root=root,
                go_phrase=args.go_phrase or None,
                skip_docker=args.skip_docker,
            )
        elif args.stop:
            report = stop_campaign(
                manifest, repo_root=root, skip_docker=args.skip_docker
            )
        elif args.resume:
            report = resume_campaign(
                manifest,
                repo_root=root,
                go_phrase=args.go_phrase or None,
                skip_docker=args.skip_docker,
            )
        else:
            parser.error("Specify --preflight-only, --status, --start, --stop, or --resume")
            return 2
    except (DataCaptureContractError, DataCaptureError) as exc:
        print(str(exc), file=os.sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(json.dumps(report, indent=2))
    if report.get("verdict") == "PREFLIGHT_FAIL" or report.get("passed") is False:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
