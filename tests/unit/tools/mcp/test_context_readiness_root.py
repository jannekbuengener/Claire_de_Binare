"""Unit tests for context.readiness host cwd vs repo root semantics (#2848)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.unit.tools.mcp.fixtures.context_fixtures import MINIMUM_REQUIRED_READS
from tools.mcp.context_bridge import (
    READINESS_MINIMUM_READS,
    context_readiness_handler,
)

pytestmark = pytest.mark.unit


def _base_kwargs(**overrides) -> dict:
    payload = {
        "task_scope": "normalize readiness root cwd semantics",
        "operation_mode": "read_only",
        "stop_conditions": ["S1: unit test scope"],
        "required_reads": [],
    }
    payload.update(overrides)
    return payload


def _readiness(result: dict) -> dict:
    assert result.get("tool") == "context.readiness"
    assert result.get("status") == "ok"
    readiness = result.get("readiness")
    assert isinstance(readiness, dict)
    return readiness


def _assert_root_fields(readiness: dict) -> None:
    for key in (
        "host_cwd",
        "resolved_repo_root",
        "effective_scan_root",
        "root_source",
        "cwd_matches_repo_root",
        "root_drift_detected",
        "drift_severity",
        "limitations",
        "evidence",
    ):
        assert key in readiness, f"missing root field: {key}"


@pytest.fixture
def mini_repo(tmp_path: Path) -> Path:
    for rel in READINESS_MINIMUM_READS:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"fixture for {rel}\n", encoding="utf-8")
    return tmp_path


def test_matching_cwd_and_repo_root_passes_without_required_reads_param(
    mini_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(mini_repo)
    readiness = _readiness(
        context_readiness_handler(**_base_kwargs(repo_root=str(mini_repo)))
    )
    _assert_root_fields(readiness)
    assert readiness["cwd_matches_repo_root"] is True
    assert readiness["root_drift_detected"] is False
    assert readiness["drift_severity"] == "none"
    assert readiness["status"] == "ready_for_read_only"
    assert readiness["effective_scan_root"] == str(mini_repo.resolve())


def test_host_cwd_drift_with_explicit_repo_root_scans_repo(
    mini_repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    other_cwd = tmp_path / "host_cwd"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)
    readiness = _readiness(
        context_readiness_handler(
            **_base_kwargs(repo_root=str(mini_repo)),
        )
    )
    _assert_root_fields(readiness)
    assert readiness["root_drift_detected"] is True
    assert readiness["drift_severity"] == "warning"
    assert readiness["cwd_matches_repo_root"] is False
    assert readiness["effective_scan_root"] == str(mini_repo.resolve())
    assert readiness["status"] == "ready_for_read_only"


def test_host_cwd_drift_without_repo_root_uses_bridge_module_root(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    other_cwd = tmp_path / "outside_repo"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)
    readiness = _readiness(context_readiness_handler(**_base_kwargs()))
    _assert_root_fields(readiness)
    assert readiness["resolved_repo_root"] == str(repo_root.resolve())
    assert readiness["effective_scan_root"] == str(repo_root.resolve())
    if readiness["root_drift_detected"]:
        assert readiness["drift_severity"] == "warning"
    assert readiness["status"] == "ready_for_read_only"


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def test_missing_canon_on_scan_root_blocks_fail_closed(
    mini_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = READINESS_MINIMUM_READS[0]
    (mini_repo / missing).unlink()
    monkeypatch.chdir(mini_repo)
    readiness = _readiness(
        context_readiness_handler(
            **_base_kwargs(
                repo_root=str(mini_repo),
                required_reads=list(MINIMUM_REQUIRED_READS),
            ),
        )
    )
    assert readiness["status"] == "blocked_missing_context"
    assert any("effective_scan_root" in item for item in readiness["missing_context"])


def test_invalid_repo_root_parameter_blocks() -> None:
    readiness = _readiness(
        context_readiness_handler(
            **_base_kwargs(repo_root="/nonexistent/cdb/repo/root")
        )
    )
    assert readiness["status"] == "blocked_missing_context"
    assert readiness["drift_severity"] == "blocked"
    assert readiness["effective_scan_root"] is None


def test_benchmark_repro_empty_reads_ok_when_canon_on_module_root(
    repo_root: Path,
) -> None:
    """MCP-style empty required_reads must not block when canon exists at repo root."""
    if not all((repo_root / rel).is_file() for rel in READINESS_MINIMUM_READS):
        pytest.skip("full working repo canon not present in this checkout")
    original = os.getcwd()
    try:
        os.chdir(repo_root)
        readiness = _readiness(context_readiness_handler(**_base_kwargs()))
    finally:
        os.chdir(original)
    assert readiness["status"] == "ready_for_read_only"
    assert readiness["root_drift_detected"] is False
