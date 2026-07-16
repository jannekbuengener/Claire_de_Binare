"""Contract tests for SurrealDB read-only query integration harness (#3776).

Fixture/adapter backed — no live SurrealDB in standard CI.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.mcp.memory_write_intent_tools import MUTATION_ALLOWED
from tools.surrealdb import context_readonly_query_harness as harness
from tools.surrealdb.context_query import WriteDeniedError, classify_statement

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_CONFIG = REPO_ROOT / "infrastructure/config/surrealdb/context_query.local.example.yaml"
LOCAL_TEST_FILE = REPO_ROOT / "tests/local/surrealdb/test_context_readonly_query_harness.py"
CI_YAML = REPO_ROOT / ".github/workflows/ci.yml"
PYTEST_INI = REPO_ROOT / "pytest.ini"


# ---------------------------------------------------------------------------
# Safety / CI contract
# ---------------------------------------------------------------------------


def test_mutation_allowed_false_default() -> None:
    assert MUTATION_ALLOWED is False
    flags = harness.harness_safety_flags()
    assert flags["MUTATION_ALLOWED"] is False
    assert flags["read_only_default"] is True
    assert flags["productive_write_path"] is False


def test_standard_ci_excludes_local_only() -> None:
    evidence = harness.standard_ci_excludes_local_only()
    assert evidence["pytest_marker_registered"] is True
    assert evidence["ci_excludes_local_only"] is True
    assert evidence["ok"] is True
    assert "pytest -q" in CI_YAML.read_text(encoding="utf-8")
    assert "norecursedirs = local" in PYTEST_INI.read_text(encoding="utf-8")
    assert "local_only:" in PYTEST_INI.read_text(encoding="utf-8")


def test_local_only_marker_present_on_local_integration_file() -> None:
    source = LOCAL_TEST_FILE.read_text(encoding="utf-8")
    assert "pytest.mark.local_only" in source
    assert harness.ENV_REAL_SURREALDB_READONLY_QUERY in source


def test_harness_has_no_productive_write_path() -> None:
    violations = harness.assert_harness_has_no_productive_write_path()
    assert violations == []


# ---------------------------------------------------------------------------
# Fail-closed / repo-fallback posture
# ---------------------------------------------------------------------------


def test_unreachable_db_fail_closed_repo_fallback() -> None:
    posture = harness.classify_db_evidence_posture(
        db_reachable=False,
        record_source="surrealdb-local",
        record_ids=["evidence_ref:abc"],
    )
    assert posture["db_claims_allowed"] is False
    assert posture["brain_source"] == "repo-only"
    assert posture["brain_status"] == "not-used"
    assert posture["repo_fallback_used"] is True
    assert posture["repo_fallback_reason"] == "unavailable"


def test_unreachable_db_blocks_false_db_backed_claim() -> None:
    blocked = harness.assert_repo_only_db_claim_blocked(
        db_reachable=False,
        record_source=None,
        claimed_brain_source="surrealdb-local",
    )
    assert blocked is True


def test_db_backed_posture_requires_records_and_source() -> None:
    posture = harness.classify_db_evidence_posture(
        db_reachable=True,
        record_source="surrealdb-local",
        record_ids=["evidence_ref:deadbeef"],
    )
    assert posture["db_claims_allowed"] is True
    assert posture["brain_source"] == "surrealdb-local"


def test_preflight_fail_closed_without_env_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(harness.ENV_REAL_SURREALDB_READONLY_QUERY, raising=False)
    result = harness.check_readonly_query_preconditions(confirm=False)
    assert result["ok"] is False
    assert any(harness.ENV_REAL_SURREALDB_READONLY_QUERY in err for err in result["errors"])


def test_preflight_ok_with_confirm_when_health_and_config_ok(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(harness.ENV_REAL_SURREALDB_READONLY_QUERY, raising=False)
    fake_root = tmp_path / "repo"
    config_dir = fake_root / harness.QUERY_CONFIG_REL.parent
    config_dir.mkdir(parents=True)
    (config_dir / harness.QUERY_CONFIG_REL.name).write_text(
        "schema_version: context-query-local/v0\n", encoding="utf-8"
    )
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "SURREALDB_ENV").write_text(
        "SURREAL_USER=x\nSURREAL_PASS=y\n", encoding="utf-8"
    )
    with (
        patch.object(harness, "repo_root", return_value=fake_root),
        patch.object(harness, "http_status", return_value=200),
        patch.object(harness, "resolve_secrets_path", return_value=secrets),
    ):
        result = harness.check_readonly_query_preconditions(confirm=True)
    assert result["ok"] is True
    assert result["db_reachable"] is True


# ---------------------------------------------------------------------------
# Namespace isolation
# ---------------------------------------------------------------------------


def test_namespace_isolation_contract() -> None:
    isolation = harness.build_isolation(run_tag="run3776")
    assert isolation.namespace == harness.HARNESS_NAMESPACE
    assert isolation.database == harness.HARNESS_DATABASE
    headers = isolation.as_headers()
    assert headers["surreal-ns"] == harness.HARNESS_NAMESPACE
    assert headers["surreal-db"] == harness.HARNESS_DATABASE
    assert headers["surreal-url"] == harness.LOCAL_SURR_URL


def test_write_probe_denied_by_classifier() -> None:
    with pytest.raises(WriteDeniedError):
        classify_statement(harness.HARNESS_WRITE_PROBE)


# ---------------------------------------------------------------------------
# Adapter modes: embedded / file / mem (no live DB)
# ---------------------------------------------------------------------------


def test_embedded_mode_returns_empty_results() -> None:
    adapter = harness.build_adapter_for_mode("embedded")
    result = harness.run_readonly_probe(adapter)
    assert result["row_count"] == 0
    assert result["read_only"] is True


def test_mem_mode_returns_fixture_rows() -> None:
    adapter = harness.build_adapter_for_mode(
        "mem",
        mem_rows=[{"artifact_id": "repo_artifact:abc", "source_path": "core/x.py"}],
    )
    result = harness.run_readonly_probe(adapter, query="SELECT * FROM repo_artifact LIMIT 1")
    assert result["row_count"] == 1


def test_mem_mode_denies_write_probe() -> None:
    adapter = harness.build_adapter_for_mode("mem")
    with pytest.raises(WriteDeniedError):
        harness.run_readonly_probe(adapter, query=harness.HARNESS_WRITE_PROBE)


def test_file_mode_loads_example_config_namespace() -> None:
    adapter = harness.build_adapter_for_mode("file", config_path=EXAMPLE_CONFIG)
    assert adapter.namespace == "cdb_context_local"
    assert adapter.database == "cdb_context_intel"
    result = harness.run_readonly_probe(adapter)
    assert result["classification"]["allowed"] is True


def test_live_mode_unreachable_soft_returns_empty_with_repo_fallback_posture(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "SURREALDB_ENV").write_text(
        "SURREAL_USER=x\nSURREAL_PASS=y\n", encoding="utf-8"
    )
    adapter = harness.build_live_adapter(
        config_path=EXAMPLE_CONFIG,
        secrets_path=secrets,
        hard_mode=False,
    )
    import urllib.error

    mock_opener = MagicMock()
    mock_opener.open.side_effect = urllib.error.URLError("connection refused")
    with patch("tools.surrealdb.context_query.urllib.request.build_opener", return_value=mock_opener):
        rows = adapter.execute(harness.HARNESS_PROBE_QUERY)
    assert rows == []
    posture = harness.classify_db_evidence_posture(
        db_reachable=False,
        record_source="surrealdb-local",
        record_ids=None,
    )
    assert posture["db_claims_allowed"] is False
    assert harness.assert_repo_only_db_claim_blocked(
        db_reachable=False,
        record_source=None,
        claimed_brain_source="surrealdb-local",
    )
