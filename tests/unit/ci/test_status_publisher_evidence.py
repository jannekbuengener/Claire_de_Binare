"""Unit tests for status publisher evidence validation (Issue #4164)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ci.lib.evidence import (
    StageResult,
    build_manifest,
    write_manifest,
)
from ci.publisher.evidence import validate_evidence_for_publish
from ci.publisher.exceptions import LedgerError
from ci.publisher.ledger import (
    LedgerEntry,
    append_entry,
    assert_run_id_not_reused,
    load_ledger,
)

pytestmark = pytest.mark.unit

SHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
OTHER_SHA = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


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
        started_at_utc="2026-07-27T12:00:00Z",
        ended_at_utc="2026-07-27T12:00:01Z",
        duration_seconds=1.0,
        command_summary=[f"cmd-{name}"],
        log_path=f"logs/{name}.log",
        skip_reason=skip_reason,
        required=required,
    )


def _write_pass_evidence(
    tmp_path: Path,
    *,
    sha: str = SHA,
    dirty: bool = False,
    overall_override: str | None = None,
    ended_at: str | None = None,
    stages: list[StageResult] | None = None,
    repo_name: str = "Claire_de_Binare",
    run_id: str = "testrun01",
    mutate_artifact: bool = False,
) -> Path:
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    log = run_dir / "logs"
    log.mkdir()
    (log / "lint.log").write_text("ok\n", encoding="utf-8")
    report = run_dir / "reports"
    report.mkdir()
    (report / "check-matrix.json").write_text("{}\n", encoding="utf-8")
    artifact_paths = [log / "lint.log", report / "check-matrix.json"]
    from ci.lib.evidence import hash_artifacts

    hashes = hash_artifacts(artifact_paths, relative_to=run_dir)
    if stages is None:
        stages = [
            _stage("lint", "PASS"),
            _stage("unit", "PASS"),
            _stage("docs", "PASS"),
            _stage("governance", "PASS"),
            _stage("report", "PASS"),
            _stage("security", "SKIPPED", required=False, skip_reason="fast profile"),
        ]
    ended = ended_at or datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")
    manifest = build_manifest(
        run_id=run_id,
        commit_sha=sha,
        branch="feat/test",
        dirty_worktree=dirty,
        started_at_utc="2026-07-27T12:00:00Z",
        ended_at_utc=ended,
        host_platform="test",
        tool_versions={"python": "3.12"},
        docker_version="n/a",
        compose_version="n/a",
        profile="fast",
        stages=stages,
        skipped_checks=[],
        artifact_hashes=hashes,
        repo_name=repo_name,
    )
    if overall_override is not None:
        manifest["overall_status"] = overall_override
    write_manifest(run_dir, manifest)
    if mutate_artifact:
        (log / "lint.log").write_text("tampered\n", encoding="utf-8")
    return run_dir


def test_valid_clean_evidence_for_exact_sha_passes(tmp_path: Path):
    run_dir = _write_pass_evidence(tmp_path)
    result = validate_evidence_for_publish(
        run_dir, commit_sha=SHA, repository="jannekbuengener/Claire_de_Binare"
    )
    assert result.ok is True
    assert result.intended_payload is not None
    assert result.intended_payload.state == "success"
    assert result.intended_payload.sha == SHA
    assert any(s["name"] == "security" for s in result.optional_skipped)


def test_wrong_sha_is_rejected(tmp_path: Path):
    run_dir = _write_pass_evidence(tmp_path, sha=SHA)
    result = validate_evidence_for_publish(run_dir, commit_sha=OTHER_SHA)
    assert result.ok is False
    assert "does not match" in (result.reason or "")
    assert result.intended_payload is None


def test_foreign_repository_is_rejected(tmp_path: Path):
    run_dir = _write_pass_evidence(tmp_path)
    # Tamper after write: foreign repo_name must fail closed on load/publish.
    manifest_path = run_dir / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["repo_name"] = "Other_Repo"
    from ci.lib.evidence import write_manifest

    write_manifest(run_dir, data)
    result = validate_evidence_for_publish(
        run_dir,
        commit_sha=SHA,
        repository="evil/other",
    )
    assert result.ok is False


def test_dirty_worktree_is_rejected(tmp_path: Path):
    stages = [
        _stage("lint", "PASS"),
        _stage("unit", "PASS"),
        _stage("docs", "PASS"),
        _stage("governance", "PASS"),
        _stage("report", "PASS"),
    ]
    run_dir = _write_pass_evidence(tmp_path, dirty=True, stages=stages)
    result = validate_evidence_for_publish(run_dir, commit_sha=SHA)
    assert result.ok is False
    assert "Dirty" in (result.reason or "") or "dirty" in (result.reason or "").lower()


def test_manifest_hash_mismatch_is_rejected(tmp_path: Path):
    run_dir = _write_pass_evidence(tmp_path)
    sha_path = run_dir / "manifest.sha256"
    sha_path.write_text("0" * 64 + "  manifest.json\n", encoding="utf-8")
    result = validate_evidence_for_publish(run_dir, commit_sha=SHA)
    assert result.ok is False
    assert "manifest.sha256" in (result.reason or "")


def test_artifact_hash_mismatch_is_rejected(tmp_path: Path):
    run_dir = _write_pass_evidence(tmp_path, mutate_artifact=True)
    result = validate_evidence_for_publish(run_dir, commit_sha=SHA)
    assert result.ok is False
    assert "hash mismatch" in (result.reason or "").lower()


def test_required_stage_fail_is_rejected(tmp_path: Path):
    stages = [
        _stage("lint", "PASS"),
        _stage("unit", "FAIL"),
        _stage("docs", "PASS"),
        _stage("governance", "PASS"),
        _stage("report", "PASS"),
    ]
    run_dir = _write_pass_evidence(tmp_path, stages=stages)
    result = validate_evidence_for_publish(run_dir, commit_sha=SHA)
    assert result.ok is False


def test_required_stage_skipped_is_rejected(tmp_path: Path):
    stages = [
        _stage("lint", "SKIPPED", required=True, skip_reason="nope"),
        _stage("unit", "PASS"),
        _stage("docs", "PASS"),
        _stage("governance", "PASS"),
        _stage("report", "PASS"),
    ]
    run_dir = _write_pass_evidence(tmp_path, stages=stages)
    result = validate_evidence_for_publish(run_dir, commit_sha=SHA)
    assert result.ok is False


def test_optional_skipped_stage_is_disclosed(tmp_path: Path):
    run_dir = _write_pass_evidence(tmp_path)
    result = validate_evidence_for_publish(run_dir, commit_sha=SHA)
    assert result.ok is True
    assert result.optional_skipped
    assert "Optional skipped" in (
        result.intended_payload.description if result.intended_payload else ""
    )


def test_stale_evidence_is_rejected(tmp_path: Path):
    old = (
        (datetime.now(timezone.utc) - timedelta(hours=48))
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    run_dir = _write_pass_evidence(tmp_path, ended_at=old)
    result = validate_evidence_for_publish(run_dir, commit_sha=SHA, freshness_hours=24)
    assert result.ok is False
    assert "Stale" in (result.reason or "")


def test_duplicate_run_id_for_another_sha_is_rejected(tmp_path: Path):
    ledger_path = tmp_path / "published-runs.json"
    append_entry(
        ledger_path,
        LedgerEntry(
            run_id="testrun01",
            commit_sha=OTHER_SHA,
            repository="jannekbuengener/Claire_de_Binare",
            status_context="cdb-local-ci",
            manifest_sha256="a" * 64,
            published_at_utc="2026-07-27T00:00:00Z",
        ),
    )
    ledger = load_ledger(ledger_path)
    with pytest.raises(LedgerError):
        assert_run_id_not_reused(ledger, run_id="testrun01", commit_sha=SHA)


def test_ledger_corruption_blocks(tmp_path: Path):
    ledger_path = tmp_path / "published-runs.json"
    ledger_path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(LedgerError):
        load_ledger(ledger_path)


def test_failure_never_produces_success_payload(tmp_path: Path):
    run_dir = _write_pass_evidence(tmp_path, sha=SHA)
    result = validate_evidence_for_publish(run_dir, commit_sha=OTHER_SHA)
    assert result.ok is False
    assert result.intended_payload is None or result.intended_payload.state != "success"
