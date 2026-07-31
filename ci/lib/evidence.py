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
    reason_code: str | None = None


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
    if (manifest_sha or "").lower() != (head_sha or "").lower():
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
    merge_evidence: bool = True,
) -> dict[str, Any]:
    validate_run_id(run_id)
    validate_repo_name(repo_name)
    validate_stage_skip_rules(stages)
    overall = aggregate_overall_status(stages, dirty_worktree=dirty_worktree)
    # Slice / selective runs must never count as merge evidence (#4204).
    effective_merge_evidence = bool(merge_evidence) and profile not in ("slice",)
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
        "merge_evidence": effective_merge_evidence,
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


DEFAULT_REQUIRED_STAGES = ("lint", "unit", "docs", "governance")
DEFAULT_FRESHNESS_HOURS = 24


def _parse_utc(timestamp: str) -> datetime:
    raw = (timestamp or "").strip()
    if not raw:
        raise EvidenceError("Missing evidence timestamp")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise EvidenceError(f"Invalid evidence timestamp: {timestamp!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def verify_artifact_hashes(run_dir: Path, manifest: dict[str, Any]) -> None:
    """Recompute listed artifact hashes; fail closed on any mismatch or missing file."""
    listed = manifest.get("artifact_hashes")
    if not isinstance(listed, dict) or not listed:
        raise EvidenceError("manifest.artifact_hashes missing or empty")
    for rel, expected in listed.items():
        path = run_dir / str(rel)
        if not path.is_file():
            raise EvidenceError(f"Listed artifact missing: {rel}")
        actual = sha256_file(path)
        if actual != expected:
            raise EvidenceError(f"Artifact hash mismatch for {rel}")


def assert_evidence_fresh(
    manifest: dict[str, Any],
    *,
    max_age_hours: float = DEFAULT_FRESHNESS_HOURS,
    now: datetime | None = None,
) -> None:
    """Reject evidence older than the freshness window (based on ended_at_utc)."""
    if max_age_hours <= 0:
        raise EvidenceError("Freshness window must be positive")
    ended = _parse_utc(str(manifest.get("ended_at_utc", "")))
    current = now or datetime.now(timezone.utc)
    age_seconds = (current - ended).total_seconds()
    if age_seconds < 0:
        raise EvidenceError("Evidence ended_at_utc is in the future")
    max_age_seconds = max_age_hours * 3600.0
    if age_seconds > max_age_seconds:
        raise EvidenceError(
            f"Stale evidence rejected: age {age_seconds:.0f}s exceeds "
            f"{max_age_hours}h window"
        )


def optional_skipped_stages(manifest: dict[str, Any]) -> list[dict[str, str]]:
    """Return optional SKIPPED stages with their skip_reason (must be disclosed)."""
    disclosed: list[dict[str, str]] = []
    for stage in manifest.get("stages") or []:
        if not isinstance(stage, dict):
            continue
        if stage.get("status") != "SKIPPED":
            continue
        if stage.get("required", True):
            continue
        reason = stage.get("skip_reason") or ""
        disclosed.append(
            {
                "name": str(stage.get("name", "")),
                "skip_reason": str(reason),
            }
        )
    return disclosed


def assert_publishable(
    manifest: dict[str, Any],
    *,
    required_stages: Iterable[str] = DEFAULT_REQUIRED_STAGES,
) -> None:
    """Fail closed unless evidence is clean, PASS, and required stages passed.

    Does not itself verify hashes, freshness, or SHA binding — callers must
    compose those checks. Optional SKIPPED stages are allowed only with reason
    and are returned via :func:`optional_skipped_stages` for disclosure.
    """
    if manifest.get("dirty_worktree") is True:
        raise EvidenceError("Dirty worktree evidence cannot be published")
    # Explicit slice / selective Fast-CI must never publish as cdb-local-ci (#4204).
    if manifest.get("merge_evidence") is False:
        raise EvidenceError(
            "Evidence merge_evidence=false cannot be published as merge proof"
        )
    if str(manifest.get("profile") or "") == "slice":
        raise EvidenceError("Slice profile evidence cannot be published as merge proof")
    if manifest.get("overall_status") != "PASS":
        raise EvidenceError(
            f"Evidence overall_status is {manifest.get('overall_status')!r}, not PASS"
        )
    stages = manifest.get("stages") or []
    by_name: dict[str, dict[str, Any]] = {}
    for stage in stages:
        if not isinstance(stage, dict):
            raise EvidenceError("Invalid stage entry in manifest")
        name = str(stage.get("name", ""))
        by_name[name] = stage
        if stage.get("required", True) and stage.get("status") == "SKIPPED":
            raise EvidenceError(f"Required stage {name!r} is SKIPPED")
        if stage.get("required", True) and stage.get("status") != "PASS":
            raise EvidenceError(
                f"Required stage {name!r} status is {stage.get('status')!r}, not PASS"
            )
        if stage.get("status") == "SKIPPED" and not stage.get("skip_reason"):
            raise EvidenceError(f"Optional stage {name!r} SKIPPED without skip_reason")
    for required in required_stages:
        stage = by_name.get(required)
        if stage is None:
            raise EvidenceError(f"Required stage {required!r} missing from evidence")
        if stage.get("status") != "PASS":
            raise EvidenceError(
                f"Required stage {required!r} status is {stage.get('status')!r}, not PASS"
            )


def manifest_digest(run_dir: Path) -> str:
    """Return the digest recorded in manifest.sha256 (fail closed if missing)."""
    sha_path = run_dir / "manifest.sha256"
    if not sha_path.is_file():
        raise EvidenceError(f"Missing manifest.sha256 in {run_dir}")
    line = sha_path.read_text(encoding="utf-8").strip()
    if not line:
        raise EvidenceError("Empty manifest.sha256")
    return line.split()[0]
