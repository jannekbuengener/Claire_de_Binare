"""Fail-closed evidence contract for local Docker CI Phase 1."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Literal

from ci import SCHEMA_VERSION

Status = Literal["PASS", "FAIL", "BLOCKED", "SKIPPED"]
OverallStatus = Literal["PASS", "FAIL", "BLOCKED"]

EXPECTED_REPO_NAMES = frozenset({"Claire_de_Binare", "claire_de_binare"})
RUN_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{7,127}$")


@dataclass
class StageResult:
    name: str
    status: Status
    exit_code: int
    started_at_utc: str
    ended_at_utc: str
    duration_seconds: float
    command_summary: list[str]
    log_path: str
    artifacts: list[str] = field(default_factory=list)
    skip_reason: str | None = None
    required: bool = True


class EvidenceError(ValueError):
    """Raised when evidence violates the fail-closed contract."""


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False).encode(
            "utf-8"
        )
        + b"\n"
    )


def aggregate_overall_status(
    stages: Iterable[StageResult],
    *,
    dirty_worktree: bool,
) -> OverallStatus:
    """Aggregate stage results fail-closed.

    Rules protected by tests:
    - dirty worktree => BLOCKED (cannot count as merge evidence)
    - any FAIL => FAIL
    - any BLOCKED => BLOCKED
    - required SKIPPED => FAIL
    - optional SKIPPED requires skip_reason (validated separately)
    """
    if dirty_worktree:
        return "BLOCKED"
    stage_list = list(stages)
    for stage in stage_list:
        if stage.required and stage.status == "SKIPPED":
            return "FAIL"
        if stage.status == "SKIPPED" and not stage.skip_reason:
            return "FAIL"
    if any(s.status == "FAIL" for s in stage_list):
        return "FAIL"
    if any(s.status == "BLOCKED" for s in stage_list):
        return "BLOCKED"
    if not stage_list:
        return "FAIL"
    if all(s.status in ("PASS", "SKIPPED") for s in stage_list):
        # optional skips already validated
        if any(s.required and s.status != "PASS" for s in stage_list):
            return "FAIL"
        return "PASS"
    return "FAIL"


def validate_stage_skip_rules(stages: Iterable[StageResult]) -> None:
    for stage in stages:
        if stage.status == "SKIPPED" and not stage.skip_reason:
            raise EvidenceError(
                f"Stage {stage.name!r} is SKIPPED without explicit skip_reason"
            )
        if stage.required and stage.status == "SKIPPED":
            # Allowed to record, but overall must FAIL — aggregation handles it.
            continue


def validate_run_id(run_id: str) -> None:
    if not RUN_ID_RE.match(run_id):
        raise EvidenceError(f"Invalid run_id: {run_id!r}")


def compose_project_name(run_id: str) -> str:
    """Build isolated Compose project name; never targets unrelated projects."""
    validate_run_id(run_id)
    return f"cdb_ci_{run_id}"


def assert_safe_cleanup_project(project: str) -> None:
    """Rule: cleanup must only target cdb_ci_* projects."""
    if not project.startswith("cdb_ci_"):
        raise EvidenceError(f"Refusing cleanup for non-cdb_ci project: {project!r}")


def validate_repo_name(repo_name: str) -> None:
    if repo_name not in EXPECTED_REPO_NAMES:
        raise EvidenceError(
            f"Foreign or unexpected repository name for local CI evidence: {repo_name!r}"
        )


def assert_commit_matches_head(manifest_sha: str, head_sha: str) -> None:
    if manifest_sha != head_sha:
        raise EvidenceError(
            f"Evidence commit_sha {manifest_sha} does not match HEAD {head_sha}"
        )


def assert_run_id_available(artifacts_root: Path, run_id: str) -> Path:
    validate_run_id(run_id)
    run_dir = artifacts_root / run_id
    if run_dir.exists():
        raise EvidenceError(f"Duplicate run_id rejected: {run_id}")
    return run_dir


def build_manifest(
    *,
    run_id: str,
    commit_sha: str,
    branch: str,
    dirty_worktree: bool,
    started_at_utc: str,
    ended_at_utc: str,
    host_platform: str,
    tool_versions: dict[str, str],
    docker_version: str,
    compose_version: str,
    profile: str,
    stages: list[StageResult],
    skipped_checks: list[dict[str, str]],
    artifact_hashes: dict[str, str],
    repo_name: str,
) -> dict[str, Any]:
    validate_run_id(run_id)
    validate_repo_name(repo_name)
    validate_stage_skip_rules(stages)
    overall = aggregate_overall_status(stages, dirty_worktree=dirty_worktree)
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "commit_sha": commit_sha,
        "branch": branch,
        "dirty_worktree": dirty_worktree,
        "repo_name": repo_name,
        "started_at_utc": started_at_utc,
        "ended_at_utc": ended_at_utc,
        "host_platform": host_platform,
        "tool_versions": tool_versions,
        "docker_version": docker_version,
        "compose_version": compose_version,
        "profile": profile,
        "stages": [asdict(s) for s in stages],
        "skipped_checks": skipped_checks,
        "artifact_hashes": artifact_hashes,
        "overall_status": overall,
    }


def write_manifest(run_dir: Path, manifest: dict[str, Any]) -> tuple[Path, Path]:
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / "manifest.json"
    payload = canonical_json_bytes(manifest)
    manifest_path.write_bytes(payload)
    digest = sha256_bytes(payload)
    sha_path = run_dir / "manifest.sha256"
    sha_path.write_text(f"{digest}  manifest.json\n", encoding="utf-8")
    return manifest_path, sha_path


def load_and_validate_manifest(
    run_dir: Path,
    *,
    expected_commit_sha: str | None = None,
    expected_repo_name: str | None = None,
) -> dict[str, Any]:
    manifest_path = run_dir / "manifest.json"
    sha_path = run_dir / "manifest.sha256"
    if not manifest_path.is_file():
        raise EvidenceError(f"Missing manifest.json in {run_dir}")
    if not sha_path.is_file():
        raise EvidenceError(f"Missing manifest.sha256 in {run_dir}")
    raw = manifest_path.read_bytes()
    expected_line = sha_path.read_text(encoding="utf-8").strip()
    expected_digest = expected_line.split()[0]
    actual_digest = sha256_bytes(raw)
    if actual_digest != expected_digest:
        raise EvidenceError("manifest.sha256 does not match manifest.json contents")
    manifest = json.loads(raw.decode("utf-8"))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise EvidenceError(
            f"Unsupported schema_version: {manifest.get('schema_version')!r}"
        )
    validate_repo_name(str(manifest.get("repo_name", "")))
    if expected_repo_name is not None:
        validate_repo_name(expected_repo_name)
        if manifest.get("repo_name") != expected_repo_name:
            raise EvidenceError("Foreign repository evidence rejected")
    if expected_commit_sha is not None:
        assert_commit_matches_head(str(manifest.get("commit_sha")), expected_commit_sha)
    if (
        manifest.get("dirty_worktree") is True
        and manifest.get("overall_status") != "BLOCKED"
    ):
        raise EvidenceError("Dirty worktree evidence must be overall BLOCKED")
    return manifest


def hash_artifacts(paths: list[Path], *, relative_to: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in paths:
        if not path.is_file():
            continue
        rel = path.relative_to(relative_to).as_posix()
        hashes[rel] = sha256_file(path)
    return hashes
