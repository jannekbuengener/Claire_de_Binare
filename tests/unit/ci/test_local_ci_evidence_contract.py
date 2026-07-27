"""Contract tests for local Docker CI Phase 1 evidence rules.

Each test names the fail-closed rule it protects. Local evidence is intentionally
NOT a GitHub Required Check — Branch Protection remains unchanged in Phase 1.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ci.lib.evidence import (
    SCHEMA_VERSION,
    EvidenceError,
    StageResult,
    aggregate_overall_status,
    assert_run_id_available,
    assert_safe_cleanup_project,
    build_manifest,
    compose_project_name,
    load_and_validate_manifest,
    sha256_bytes,
    validate_repo_name,
    write_manifest,
)

pytestmark = pytest.mark.unit


def _stage(
    name: str,
    status: str,
    *,
    required: bool = True,
    skip_reason: str | None = None,
) -> StageResult:
    return StageResult(
        name=name,
        status=status,  # type: ignore[arg-type]
        exit_code=0 if status in ("PASS", "SKIPPED") else 1,
        started_at_utc="2026-07-27T00:00:00Z",
        ended_at_utc="2026-07-27T00:00:01Z",
        duration_seconds=1.0,
        command_summary=[f"cmd-{name}"],
        log_path=f"logs/{name}.log",
        artifacts=[],
        skip_reason=skip_reason,
        required=required,
    )


def test_pass_only_when_all_required_stages_pass():
    """Rule: PASS only when all required stages pass."""
    stages = [
        _stage("lint", "PASS"),
        _stage("unit", "PASS"),
        _stage("docs", "PASS"),
        _stage("governance", "PASS"),
        _stage("report", "PASS"),
        _stage("security", "SKIPPED", required=False, skip_reason="heavy only"),
    ]
    assert aggregate_overall_status(stages, dirty_worktree=False) == "PASS"


def test_fail_when_one_required_stage_fails():
    """Rule: Any FAIL means overall FAIL."""
    stages = [
        _stage("lint", "PASS"),
        _stage("unit", "FAIL"),
        _stage("report", "PASS"),
    ]
    assert aggregate_overall_status(stages, dirty_worktree=False) == "FAIL"


def test_fail_when_required_stage_skipped():
    """Rule: A skipped required stage means overall FAIL (no hidden skip PASS)."""
    stages = [
        _stage("lint", "SKIPPED", required=True, skip_reason="should not skip"),
        _stage("unit", "PASS"),
        _stage("report", "PASS"),
    ]
    assert aggregate_overall_status(stages, dirty_worktree=False) == "FAIL"


def test_blocked_when_dirty_worktree():
    """Rule: Dirty worktree evidence is overall BLOCKED and cannot count as merge evidence."""
    stages = [_stage("lint", "PASS"), _stage("report", "PASS")]
    assert aggregate_overall_status(stages, dirty_worktree=True) == "BLOCKED"


def test_reject_manifest_for_different_commit_sha(tmp_path: Path):
    """Rule: Reject evidence whose commit SHA differs from HEAD."""
    stages = [_stage("lint", "PASS"), _stage("report", "PASS")]
    manifest = build_manifest(
        run_id="run_abc12345",
        commit_sha="aaa",
        branch="feat/x",
        dirty_worktree=False,
        started_at_utc="2026-07-27T00:00:00Z",
        ended_at_utc="2026-07-27T00:01:00Z",
        host_platform="test",
        tool_versions={},
        docker_version="n/a",
        compose_version="n/a",
        profile="fast",
        stages=stages,
        skipped_checks=[],
        artifact_hashes={},
        repo_name="Claire_de_Binare",
    )
    run_dir = tmp_path / "run_abc12345"
    write_manifest(run_dir, manifest)
    with pytest.raises(EvidenceError, match="does not match HEAD"):
        load_and_validate_manifest(run_dir, expected_commit_sha="bbb")


def test_reject_duplicate_run_id(tmp_path: Path):
    """Rule: Reject reused run IDs."""
    run_id = "run_dup_0001"
    first = assert_run_id_available(tmp_path, run_id)
    first.mkdir()
    with pytest.raises(EvidenceError, match="Duplicate run_id"):
        assert_run_id_available(tmp_path, run_id)


def test_stable_report_schema(tmp_path: Path):
    """Rule: Stable report schema (schema_version + required fields)."""
    stages = [_stage("lint", "PASS"), _stage("report", "PASS")]
    manifest = build_manifest(
        run_id="run_schema01",
        commit_sha="deadbeef",
        branch="main",
        dirty_worktree=False,
        started_at_utc="2026-07-27T00:00:00Z",
        ended_at_utc="2026-07-27T00:01:00Z",
        host_platform="test",
        tool_versions={"python": "3.12"},
        docker_version="n/a",
        compose_version="n/a",
        profile="fast",
        stages=stages,
        skipped_checks=[{"check": "policy-gate", "skip_reason": "github-native"}],
        artifact_hashes={"logs/lint.log": "abc"},
        repo_name="Claire_de_Binare",
    )
    required = {
        "schema_version",
        "run_id",
        "commit_sha",
        "branch",
        "dirty_worktree",
        "started_at_utc",
        "ended_at_utc",
        "host_platform",
        "tool_versions",
        "docker_version",
        "compose_version",
        "profile",
        "stages",
        "skipped_checks",
        "artifact_hashes",
        "overall_status",
    }
    assert required.issubset(manifest.keys())
    assert manifest["schema_version"] == SCHEMA_VERSION
    write_manifest(tmp_path / "run_schema01", manifest)
    loaded = load_and_validate_manifest(
        tmp_path / "run_schema01", expected_commit_sha="deadbeef"
    )
    assert loaded["overall_status"] == "PASS"


def test_artifact_hashes_reproducible(tmp_path: Path):
    """Rule: Artifact hashes are reproducible for identical bytes."""
    payload = b'{"a":1}\n'
    assert sha256_bytes(payload) == sha256_bytes(payload)
    stages = [_stage("report", "PASS")]
    m1 = build_manifest(
        run_id="run_hash0001",
        commit_sha="cafebabe",
        branch="main",
        dirty_worktree=False,
        started_at_utc="2026-07-27T00:00:00Z",
        ended_at_utc="2026-07-27T00:01:00Z",
        host_platform="test",
        tool_versions={},
        docker_version="n/a",
        compose_version="n/a",
        profile="fast",
        stages=stages,
        skipped_checks=[],
        artifact_hashes={"x": sha256_bytes(payload)},
        repo_name="Claire_de_Binare",
    )
    m2 = build_manifest(
        run_id="run_hash0002",
        commit_sha="cafebabe",
        branch="main",
        dirty_worktree=False,
        started_at_utc="2026-07-27T00:00:00Z",
        ended_at_utc="2026-07-27T00:01:00Z",
        host_platform="test",
        tool_versions={},
        docker_version="n/a",
        compose_version="n/a",
        profile="fast",
        stages=stages,
        skipped_checks=[],
        artifact_hashes={"x": sha256_bytes(payload)},
        repo_name="Claire_de_Binare",
    )
    assert m1["artifact_hashes"] == m2["artifact_hashes"]


def test_cleanup_project_name_isolation():
    """Rule: Cleanup must only target cdb_ci_<run_id>, never unrelated projects."""
    assert compose_project_name("run_abc12345") == "cdb_ci_run_abc12345"
    assert_safe_cleanup_project("cdb_ci_run_abc12345")
    with pytest.raises(EvidenceError, match="Refusing cleanup"):
        assert_safe_cleanup_project("unrelated_compose_project")


def test_reject_foreign_repo_name():
    """Rule: Reject evidence generated for another repository."""
    with pytest.raises(EvidenceError, match="Foreign or unexpected"):
        validate_repo_name("other-repo")


def test_optional_skip_without_reason_fails_closed():
    """Rule: An optional skipped stage requires an explicit skip_reason."""
    stages = [
        _stage("lint", "PASS"),
        _stage("security", "SKIPPED", required=False, skip_reason=None),
        _stage("report", "PASS"),
    ]
    assert aggregate_overall_status(stages, dirty_worktree=False) == "FAIL"
