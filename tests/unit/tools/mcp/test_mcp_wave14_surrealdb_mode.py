"""Unit tests for Wave-14 MCP tools in DB-backed (surrealdb-local) mode.

Issue #2461 — Wire core context MCP tools to local SurrealDB read-only adapters.
Parent: #1976

Tests the explicit opt-in adapter path (adapter_config_path param).
All HTTP / adapter calls are mocked — no real DB or network required.

Markers: @pytest.mark.unit
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from tools.mcp.context_evidence_memory_tools import (
    TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
    TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
    TOOL_CDB_CONTEXT_MEMORY_GET,
    TOOL_CDB_CONTEXT_TRUST_SUMMARY,
    handle_cdb_context_evidence_resolve,
    handle_cdb_context_claim_resolve,
    handle_cdb_context_memory_get,
    handle_cdb_context_trust_summary,
)
from tools.mcp.context_decision_tools import (
    TOOL_CDB_CONTEXT_DECISION_HISTORY,
    TOOL_CDB_CONTEXT_DECISION_REPLAY,
    handle_cdb_context_decision_history,
    handle_cdb_context_decision_replay,
)
from tools.surrealdb.context_query import (
    QueryAdapter,
    WriteDeniedError,
)

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

_FAKE_CONFIG_PATH = "infrastructure/config/surrealdb/context_query.local.example.yaml"

_EVIDENCE_RECORD: dict[str, Any] = {
    "evidence_id": "ev-db-001",
    "title": "DB evidence record",
    "evidence_type": "test_run",
    "confidence": 0.85,
    "stale": False,
    "blocking_missing": False,
    "scope": "wave14",
    "artifact_refs": ["tools/surrealdb/evidence_lookup.py"],
    "claim_refs": [],
    "decision_refs": [],
}

_CLAIM_RECORD: dict[str, Any] = {
    "claim_id": "claim-db-001",
    "title": "DB claim record",
    "statement": "evidence_lookup is read-only",
    "status": "supported",
    "scope": "wave14",
    "topic": "context_tools",
    "evidence_refs": ["ev-db-001"],
}

_MEMORY_RECORD: dict[str, Any] = {
    "memory_id": "mem-db-001",
    "title": "DB memory record",
    "content": "All MCP tools are read-only",
    "memory_type": "constraint",
    "scope": "wave14",
    "agent": "copilot",
    "topic": "context_tools",
}

_DECISION_RECORD: dict[str, Any] = {
    "decision_id": "dec-db-001",
    "title": "DB decision record",
    "topic": "context_tools",
    "scope": "wave14",
    "status": "approved",
    "decision_type": "architectural",
}

# Record using SurrealDB schema field names (validates, related_artifacts, etc.)
# instead of the lookup-contract names (claim_refs, artifact_refs, etc.).
_EVIDENCE_SCHEMA_RECORD: dict[str, Any] = {
    "evidence_id": "ev-schema-001",
    "evidence_type": "test_run",
    "confidence": 0.9,
    "validates": ["claim-db-001"],
    "invalidates": [],
    "related_artifacts": ["tools/surrealdb/evidence_lookup.py"],
    "related_decisions": ["dec-db-001"],
    "source_path": "tests/unit/test_foo.py",
    "comment": "Schema-format evidence record for normalization tests",
    "freshness": "fresh",
}

# Record matching SurrealDB claim schema: no topic/topics/artifact_refs/decision_refs.
_CLAIM_SCHEMA_RECORD: dict[str, Any] = {
    "claim_id": "claim-schema-001",
    "title": "Schema-format claim",
    "statement": "evidence_lookup is read-only",
    "scope": "wave14",
    "status": "supported",
    "evidence_refs": ["ev-db-001"],
    "confidence": 0.9,
}

# Record matching SurrealDB agent_memory schema: uses created_by (not agent),
# ttl (not ttl_days), and omits topic/topics/artifact_refs/decision_refs.
_MEMORY_SCHEMA_RECORD: dict[str, Any] = {
    "memory_id": "mem-schema-001",
    "scope": "wave14",
    "namespace": "session",
    "memory_type": "constraint",
    "content": "All MCP tools are read-only",
    "created_by": "agent-test-001",
    "ttl": 7,
    "source_refs": ["docs/AGENTS.md"],
}


def _make_mock_adapter(
    records: list[dict[str, Any]], status: str = "surrealdb-local"
) -> MagicMock:
    """Return a mock QueryAdapter that returns *records* from execute()."""
    adapter = MagicMock(spec=QueryAdapter)
    adapter.status = status
    adapter.execute.return_value = records
    return adapter


def _patch_adapter_factory(
    monkeypatch, module_path: str, adapter: MagicMock, config: Any = None
) -> None:
    """Patch build_adapter_from_params in *module_path* to return (adapter, config)."""
    monkeypatch.setattr(
        module_path,
        lambda params, tool_name: (adapter, config),
    )


_FORGED_DB_CLAIM_FIELDS: dict[str, Any] = {
    "source": "surrealdb-local",
    "brain_source": "surrealdb-local",
    "brain_status": "used",
    "metadata": {"source": "surrealdb-local"},
    "secrets_path": "sentinel://fake-secrets-path",
    "dummy_secret": "secret-sentinel-2636",
}

_SECRET_SENTINELS = ("sentinel://fake-secrets-path", "secret-sentinel-2636")
_FORGED_ADAPTER_STATUS = "surrealdb-local-forged"


def _wave14_in_memory_parameters(tool_name: str) -> dict[str, Any]:
    if tool_name == TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE:
        return {
            "mode": "by_artifact",
            "artifact": "tools/surrealdb/evidence_lookup.py",
            "evidence_records": [_EVIDENCE_RECORD],
        }
    if tool_name == TOOL_CDB_CONTEXT_CLAIM_RESOLVE:
        return {
            "mode": "by_topic",
            "topic": "context_tools",
            "claim_records": [_CLAIM_RECORD],
        }
    if tool_name == TOOL_CDB_CONTEXT_MEMORY_GET:
        return {
            "mode": "by_scope",
            "scope": "wave14",
            "memory_records": [_MEMORY_RECORD],
        }
    if tool_name == TOOL_CDB_CONTEXT_TRUST_SUMMARY:
        return {"scope": "wave14"}
    if tool_name == TOOL_CDB_CONTEXT_DECISION_HISTORY:
        return {
            "mode": "by_topic",
            "topic": "context_tools",
            "decision_events": [_DECISION_RECORD],
        }
    if tool_name == TOOL_CDB_CONTEXT_DECISION_REPLAY:
        return {
            "mode": "replay_by_scope",
            "scope": "wave14",
            "decision_events": [_DECISION_RECORD],
        }
    raise AssertionError(f"Unhandled Wave-14 tool: {tool_name}")


def _make_wave14_db_adapter(tool_name: str, *, status: str) -> MagicMock:
    if tool_name == TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE:
        return _make_mock_adapter([_EVIDENCE_RECORD], status=status)
    if tool_name == TOOL_CDB_CONTEXT_CLAIM_RESOLVE:
        return _make_mock_adapter([_CLAIM_RECORD], status=status)
    if tool_name == TOOL_CDB_CONTEXT_MEMORY_GET:
        return _make_mock_adapter([_MEMORY_RECORD], status=status)
    if tool_name == TOOL_CDB_CONTEXT_TRUST_SUMMARY:
        adapter = MagicMock(spec=QueryAdapter)
        adapter.status = status
        adapter.execute.side_effect = [
            [_EVIDENCE_RECORD],
            [_CLAIM_RECORD],
            [_MEMORY_RECORD],
            [_DECISION_RECORD],
        ]
        return adapter
    if tool_name == TOOL_CDB_CONTEXT_DECISION_HISTORY:
        return _make_mock_adapter([_DECISION_RECORD], status=status)
    if tool_name == TOOL_CDB_CONTEXT_DECISION_REPLAY:
        return _make_mock_adapter([_DECISION_RECORD], status=status)
    raise AssertionError(f"Unhandled Wave-14 tool: {tool_name}")


def _assert_no_secret_leak(payload: dict[str, Any]) -> None:
    rendered = repr(payload)
    for sentinel in _SECRET_SENTINELS:
        assert sentinel not in rendered, (
            "Wave-14 tool leaked a caller-supplied secret sentinel: "
            f"{sentinel!r} in {rendered}"
        )


_WAVE14_HANDLER_CASES = [
    pytest.param(
        TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
        handle_cdb_context_evidence_resolve,
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        id="cdb_context_evidence_resolve",
    ),
    pytest.param(
        TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
        handle_cdb_context_claim_resolve,
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        id="cdb_context_claim_resolve",
    ),
    pytest.param(
        TOOL_CDB_CONTEXT_MEMORY_GET,
        handle_cdb_context_memory_get,
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        id="cdb_context_memory_get",
    ),
    pytest.param(
        TOOL_CDB_CONTEXT_TRUST_SUMMARY,
        handle_cdb_context_trust_summary,
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        id="cdb_context_trust_summary",
    ),
    pytest.param(
        TOOL_CDB_CONTEXT_DECISION_HISTORY,
        handle_cdb_context_decision_history,
        "tools.mcp.context_decision_tools.build_adapter_from_params",
        id="cdb_context_decision_history",
    ),
    pytest.param(
        TOOL_CDB_CONTEXT_DECISION_REPLAY,
        handle_cdb_context_decision_replay,
        "tools.mcp.context_decision_tools.build_adapter_from_params",
        id="cdb_context_decision_replay",
    ),
]


# ---------------------------------------------------------------------------
# Evidence Resolve — DB mode
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_evidence_resolve_db_mode_ok(monkeypatch) -> None:
    """DB mode: adapter returns 1 evidence record → status=ok, source=surrealdb-local."""
    mock_adapter = _make_mock_adapter([_EVIDENCE_RECORD])
    _patch_adapter_factory(
        monkeypatch,
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        mock_adapter,
    )

    result = handle_cdb_context_evidence_resolve(
        {
            "tool": TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "mode": "by_artifact",
                "artifact": "tools/surrealdb/evidence_lookup.py",
            },
        }
    )

    assert result["status"] == "ok", result
    assert result["tool"] == TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE
    assert result["metadata"]["source"] == "surrealdb-local"
    assert result["metadata"]["read_only"] is True
    assert result["result"]["approval_semantics"]["no_echtgeld_go"] is True
    mock_adapter.execute.assert_called_once()
    call_arg = mock_adapter.execute.call_args[0][0]
    assert "evidence_ref" in call_arg.lower()
    assert "SELECT" in call_arg.upper()


@pytest.mark.unit
def test_evidence_resolve_db_unavailable(monkeypatch) -> None:
    """DB unavailable: adapter.status transitions to surrealdb-local-unavailable, returns empty result."""
    mock_adapter = _make_mock_adapter([], status="surrealdb-local-unavailable")
    _patch_adapter_factory(
        monkeypatch,
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        mock_adapter,
    )

    result = handle_cdb_context_evidence_resolve(
        {
            "tool": TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "mode": "by_artifact",
                "artifact": "tools/surrealdb/evidence_lookup.py",
            },
        }
    )

    assert result["status"] == "ok"
    assert result["metadata"]["source"] == "surrealdb-local-unavailable"


@pytest.mark.unit
def test_evidence_resolve_adapter_config_error(monkeypatch) -> None:
    """Invalid adapter_config_path → status=error, code=adapter_config_error."""
    monkeypatch.setattr(
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        lambda params, tool_name: {
            "tool": tool_name,
            "status": "error",
            "error": {"code": "adapter_config_error", "message": "config not found"},
            "metadata": {"query_time_ms": 0, "source": "in_memory", "read_only": True},
        },
    )

    result = handle_cdb_context_evidence_resolve(
        {
            "tool": TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
            "parameters": {
                "adapter_config_path": "/nonexistent/path/config.yaml",
                "mode": "by_artifact",
                "artifact": "some/path",
            },
        }
    )

    assert result["status"] == "error"
    assert result["error"]["code"] == "adapter_config_error"


@pytest.mark.unit
def test_evidence_resolve_in_memory_regression() -> None:
    """No adapter_config_path → in-memory path unmodified, source=in_memory."""
    result = handle_cdb_context_evidence_resolve(
        {
            "tool": TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
            "parameters": {
                "mode": "by_artifact",
                "artifact": "tools/surrealdb/evidence_lookup.py",
                "evidence_records": [_EVIDENCE_RECORD],
            },
        }
    )

    assert result["status"] == "ok"
    assert result["metadata"]["source"] == "in_memory"


# ---------------------------------------------------------------------------
# Claim Resolve — DB mode
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_claim_resolve_db_mode_ok(monkeypatch) -> None:
    """DB mode: adapter returns 1 claim record → status=ok, source=surrealdb-local."""
    mock_adapter = _make_mock_adapter([_CLAIM_RECORD])
    _patch_adapter_factory(
        monkeypatch,
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        mock_adapter,
    )

    result = handle_cdb_context_claim_resolve(
        {
            "tool": TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "mode": "by_topic",
                "topic": "context_tools",
            },
        }
    )

    assert result["status"] == "ok", result
    assert result["metadata"]["source"] == "surrealdb-local"
    assert result["metadata"]["read_only"] is True
    assert result["result"]["approval_semantics"]["no_echtgeld_go"] is True
    call_arg = mock_adapter.execute.call_args[0][0]
    assert "claim" in call_arg.lower()


# ---------------------------------------------------------------------------
# Memory Get — DB mode
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_memory_get_db_mode_ok(monkeypatch) -> None:
    """DB mode: adapter returns 1 memory record → status=ok, source=surrealdb-local."""
    mock_adapter = _make_mock_adapter([_MEMORY_RECORD])
    _patch_adapter_factory(
        monkeypatch,
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        mock_adapter,
    )

    result = handle_cdb_context_memory_get(
        {
            "tool": TOOL_CDB_CONTEXT_MEMORY_GET,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "mode": "by_scope",
                "scope": "wave14",
            },
        }
    )

    assert result["status"] == "ok", result
    assert result["metadata"]["source"] == "surrealdb-local"
    call_arg = mock_adapter.execute.call_args[0][0]
    assert "agent_memory" in call_arg.lower()


# ---------------------------------------------------------------------------
# Trust Summary — DB mode
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_trust_summary_db_mode_ok(monkeypatch) -> None:
    """DB mode: adapter returns records for all 4 tables → status=ok, source=surrealdb-local."""
    mock_adapter = MagicMock(spec=QueryAdapter)
    mock_adapter.status = "surrealdb-local"
    # Returns different records based on the query (evidence, claim, agent_memory, decision_event)
    mock_adapter.execute.side_effect = [
        [_EVIDENCE_RECORD],  # evidence
        [_CLAIM_RECORD],  # claim
        [_MEMORY_RECORD],  # agent_memory
        [_DECISION_RECORD],  # decision_event
    ]
    _patch_adapter_factory(
        monkeypatch,
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        mock_adapter,
    )

    result = handle_cdb_context_trust_summary(
        {
            "tool": TOOL_CDB_CONTEXT_TRUST_SUMMARY,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "scope": "wave14",
            },
        }
    )

    assert result["status"] == "ok", result
    assert result["metadata"]["source"] == "surrealdb-local"
    assert result["result"]["approval_semantics"]["no_echtgeld_go"] is True
    assert mock_adapter.execute.call_count == 4


# ---------------------------------------------------------------------------
# Decision History — DB mode
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_decision_history_db_mode_ok(monkeypatch) -> None:
    """DB mode: adapter returns 1 decision_event → status=ok, source=surrealdb-local."""
    mock_adapter = _make_mock_adapter([_DECISION_RECORD])
    _patch_adapter_factory(
        monkeypatch,
        "tools.mcp.context_decision_tools.build_adapter_from_params",
        mock_adapter,
    )

    result = handle_cdb_context_decision_history(
        {
            "tool": TOOL_CDB_CONTEXT_DECISION_HISTORY,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "mode": "by_topic",
                "topic": "context_tools",
            },
        }
    )

    assert result["status"] == "ok", result
    assert result["metadata"]["source"] == "surrealdb-local"
    assert result["result"]["approval_semantics"]["no_echtgeld_go"] is True
    call_arg = mock_adapter.execute.call_args[0][0]
    assert "decision_event" in call_arg.lower()


@pytest.mark.unit
def test_decision_history_in_memory_regression() -> None:
    """No adapter_config_path → in-memory path unmodified, source=in_memory."""
    result = handle_cdb_context_decision_history(
        {
            "tool": TOOL_CDB_CONTEXT_DECISION_HISTORY,
            "parameters": {
                "mode": "by_topic",
                "topic": "context_tools",
                "decision_events": [_DECISION_RECORD],
            },
        }
    )

    assert result["status"] == "ok"
    assert result["metadata"]["source"] == "in_memory"


# ---------------------------------------------------------------------------
# Decision Replay — DB mode
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_decision_replay_db_mode_ok(monkeypatch) -> None:
    """DB mode: adapter returns 1 decision_event → status=ok, source=surrealdb-local."""
    mock_adapter = _make_mock_adapter([_DECISION_RECORD])
    _patch_adapter_factory(
        monkeypatch,
        "tools.mcp.context_decision_tools.build_adapter_from_params",
        mock_adapter,
    )

    result = handle_cdb_context_decision_replay(
        {
            "tool": TOOL_CDB_CONTEXT_DECISION_REPLAY,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "mode": "replay_by_scope",
                "scope": "wave14",
            },
        }
    )

    assert result["status"] == "ok", result
    assert result["metadata"]["source"] == "surrealdb-local"
    call_arg = mock_adapter.execute.call_args[0][0]
    assert "decision_event" in call_arg.lower()


# ---------------------------------------------------------------------------
# Write-mode enforcement (via adapter query error)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_evidence_resolve_adapter_query_error_propagates(monkeypatch) -> None:
    """When adapter.execute raises ContextQueryError → status=error, code=adapter_query_error."""
    mock_adapter = MagicMock(spec=QueryAdapter)
    mock_adapter.status = "surrealdb-local"
    mock_adapter.execute.side_effect = WriteDeniedError("INSERT statements are denied")
    _patch_adapter_factory(
        monkeypatch,
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        mock_adapter,
    )

    result = handle_cdb_context_evidence_resolve(
        {
            "tool": TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "mode": "by_artifact",
                "artifact": "some/path",
            },
        }
    )

    assert result["status"] == "error"
    assert result["error"]["code"] == "adapter_query_error"
    assert "denied" in result["error"]["message"].lower()


# ---------------------------------------------------------------------------
# Config alignment: allowed_tables covers all Wave-14 handler tables
# ---------------------------------------------------------------------------

_WAVE14_HANDLER_TABLES = {
    "evidence_ref",
    "claim",
    "agent_memory",
    "decision_event",
}

_EXAMPLE_CONFIG_PATH = (
    "infrastructure/config/surrealdb/context_query.local.example.yaml"
)


@pytest.mark.unit
def test_example_config_allows_all_wave14_tables() -> None:
    """All tables queried by the DB-backed Wave-14 handlers must be in
    the documented example config's allowed_tables list (Issue #2461).
    """
    import yaml  # stdlib-bundled via PyYAML; already a project dependency

    with open(_EXAMPLE_CONFIG_PATH) as fh:
        cfg = yaml.safe_load(fh)

    allowed: set[str] = set(cfg.get("allowed_tables", []))
    missing = _WAVE14_HANDLER_TABLES - allowed
    assert missing == set(), (
        f"Wave-14 tables missing from allowed_tables in {_EXAMPLE_CONFIG_PATH}: "
        f"{sorted(missing)}"
    )


@pytest.mark.unit
def test_evidence_handler_queries_evidence_ref_not_evidence(monkeypatch) -> None:
    """evidence_resolve DB mode must query 'evidence_ref' (schema table name),
    not 'evidence' (incorrect alias rejected by statement classifier).
    """
    mock_adapter = _make_mock_adapter([_EVIDENCE_RECORD])
    _patch_adapter_factory(
        monkeypatch,
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        mock_adapter,
    )

    handle_cdb_context_evidence_resolve(
        {
            "tool": TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "mode": "all",
            },
        }
    )

    call_arg = mock_adapter.execute.call_args[0][0]
    assert (
        "evidence_ref" in call_arg
    ), f"Handler must query 'evidence_ref', got: {call_arg!r}"
    assert "FROM evidence " not in call_arg and not call_arg.endswith(
        "FROM evidence"
    ), f"Handler must not query bare 'evidence' table, got: {call_arg!r}"


# ---------------------------------------------------------------------------
# P1: Field normalization — schema rows must match lookup contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_evidence_resolve_normalizes_schema_fields(monkeypatch) -> None:
    """P1: adapter returns a row with schema field names (validates, related_artifacts,
    related_decisions, source_path) instead of the contract names; the handler must
    normalise them so lookup_evidence_v1 can match.
    """
    mock_adapter = _make_mock_adapter([_EVIDENCE_SCHEMA_RECORD])
    _patch_adapter_factory(
        monkeypatch,
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        mock_adapter,
    )

    result = handle_cdb_context_evidence_resolve(
        {
            "tool": TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "mode": "by_artifact",
                "artifact": "tools/surrealdb/evidence_lookup.py",
            },
        }
    )

    assert result["status"] == "ok", result
    matched = result["result"]["matched_evidence"]
    assert (
        len(matched) == 1
    ), f"Expected 1 match after schema-field normalisation, got {len(matched)}: {matched}"
    ev = matched[0]
    assert ev["evidence_id"] == "ev-schema-001"
    # Verify normalization produced the contract field names
    assert "artifact_refs" in ev
    assert "tools/surrealdb/evidence_lookup.py" in ev["artifact_refs"]
    assert "claim_refs" in ev
    assert "claim-db-001" in ev["claim_refs"]
    assert "decision_refs" in ev
    assert "dec-db-001" in ev["decision_refs"]


# ---------------------------------------------------------------------------
# P2: Filter pushdown — WHERE clause must be present in the SurrealQL query
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_evidence_resolve_filter_pushdown_by_artifact(monkeypatch) -> None:
    """P2: by_artifact mode must push a WHERE clause into the SurrealQL query
    so that records are filtered at DB level, not only in RAM.
    """
    mock_adapter = _make_mock_adapter([_EVIDENCE_SCHEMA_RECORD])
    _patch_adapter_factory(
        monkeypatch,
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        mock_adapter,
    )

    handle_cdb_context_evidence_resolve(
        {
            "tool": TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "mode": "by_artifact",
                "artifact": "tools/surrealdb/evidence_lookup.py",
            },
        }
    )

    call_arg = mock_adapter.execute.call_args[0][0]
    assert "WHERE" in call_arg.upper(), f"Expected WHERE clause, got: {call_arg!r}"
    assert (
        "related_artifacts" in call_arg
    ), f"Expected 'related_artifacts' in WHERE clause, got: {call_arg!r}"
    assert (
        "CONTAINS" in call_arg.upper()
    ), f"Expected CONTAINS in WHERE clause, got: {call_arg!r}"


@pytest.mark.unit
def test_memory_get_filter_pushdown_by_scope(monkeypatch) -> None:
    """P2: by_scope mode on agent_memory must push a WHERE scope = '...' clause."""
    mock_adapter = _make_mock_adapter([_MEMORY_RECORD])
    _patch_adapter_factory(
        monkeypatch,
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        mock_adapter,
    )

    handle_cdb_context_memory_get(
        {
            "tool": TOOL_CDB_CONTEXT_MEMORY_GET,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "mode": "by_scope",
                "scope": "wave14",
            },
        }
    )

    call_arg = mock_adapter.execute.call_args[0][0]
    assert "WHERE" in call_arg.upper(), f"Expected WHERE clause, got: {call_arg!r}"
    assert "scope" in call_arg, f"Expected 'scope' in WHERE clause, got: {call_arg!r}"
    assert (
        "wave14" in call_arg
    ), f"Expected scope value in WHERE clause, got: {call_arg!r}"


@pytest.mark.unit
def test_decision_history_filter_pushdown_by_scope(monkeypatch) -> None:
    """P2: by_scope mode on decision_event must push a WHERE scope = '...' clause."""
    mock_adapter = _make_mock_adapter([_DECISION_RECORD])
    _patch_adapter_factory(
        monkeypatch,
        "tools.mcp.context_decision_tools.build_adapter_from_params",
        mock_adapter,
    )

    handle_cdb_context_decision_history(
        {
            "tool": TOOL_CDB_CONTEXT_DECISION_HISTORY,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "mode": "by_scope",
                "scope": "wave14",
            },
        }
    )

    call_arg = mock_adapter.execute.call_args[0][0]
    assert "WHERE" in call_arg.upper(), f"Expected WHERE clause, got: {call_arg!r}"
    assert "scope" in call_arg, f"Expected 'scope' in WHERE clause, got: {call_arg!r}"
    assert (
        "wave14" in call_arg
    ), f"Expected scope value in WHERE clause, got: {call_arg!r}"


# ---------------------------------------------------------------------------
# P2 (BuwCW): Claim schema projection
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_claim_resolve_normalizes_schema_row(monkeypatch) -> None:
    """DB rows without topic/artifact_refs/decision_refs must not crash the resolver.

    The SurrealDB claim schema does not define those fields; _normalize_claim_row
    must add empty defaults so resolve_claims_v1 can operate on them.
    """
    mock_adapter = _make_mock_adapter([_CLAIM_SCHEMA_RECORD])
    _patch_adapter_factory(
        monkeypatch,
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        mock_adapter,
    )

    result = handle_cdb_context_claim_resolve(
        {
            "tool": TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "mode": "by_scope",
                "scope": "wave14",
            },
        }
    )

    assert result["status"] == "ok", result
    matched = result["result"]["matched_claims"]
    assert (
        len(matched) == 1
    ), f"Expected 1 match after schema normalisation, got {matched}"
    assert matched[0]["claim_id"] == "claim-schema-001"


@pytest.mark.unit
def test_claim_resolve_filter_pushdown_by_scope(monkeypatch) -> None:
    """P2: by_scope mode on claim must push a WHERE scope = '...' clause."""
    mock_adapter = _make_mock_adapter([_CLAIM_SCHEMA_RECORD])
    _patch_adapter_factory(
        monkeypatch,
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        mock_adapter,
    )

    handle_cdb_context_claim_resolve(
        {
            "tool": TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "mode": "by_scope",
                "scope": "wave14",
            },
        }
    )

    call_arg = mock_adapter.execute.call_args[0][0]
    assert "WHERE" in call_arg.upper(), f"Expected WHERE clause, got: {call_arg!r}"
    assert "scope" in call_arg, f"Expected 'scope' in WHERE clause, got: {call_arg!r}"
    assert (
        "wave14" in call_arg
    ), f"Expected scope value in WHERE clause, got: {call_arg!r}"


# ---------------------------------------------------------------------------
# P2 (BuwCZ): Replay filter pushdown using replay_* mode names
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_decision_replay_filter_pushdown_by_scope(monkeypatch) -> None:
    """P2: replay_by_scope mode must push a WHERE scope = '...' clause."""
    mock_adapter = _make_mock_adapter([_DECISION_RECORD])
    _patch_adapter_factory(
        monkeypatch,
        "tools.mcp.context_decision_tools.build_adapter_from_params",
        mock_adapter,
    )

    handle_cdb_context_decision_replay(
        {
            "tool": TOOL_CDB_CONTEXT_DECISION_REPLAY,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "mode": "replay_by_scope",
                "scope": "wave14",
            },
        }
    )

    call_arg = mock_adapter.execute.call_args[0][0]
    assert "WHERE" in call_arg.upper(), f"Expected WHERE clause, got: {call_arg!r}"
    assert "scope" in call_arg, f"Expected 'scope' in WHERE clause, got: {call_arg!r}"
    assert (
        "wave14" in call_arg
    ), f"Expected scope value in WHERE clause, got: {call_arg!r}"


# ---------------------------------------------------------------------------
# Bu_hB: invalid limit returns structured MCP error (not bare ValueError)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_evidence_resolve_db_limit_invalid_returns_error(monkeypatch) -> None:
    """Bu_hB: limit='bad' must return invalid_parameters error, not raise ValueError."""
    mock_adapter = _make_mock_adapter([_EVIDENCE_RECORD])
    _patch_adapter_factory(
        monkeypatch,
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        mock_adapter,
    )

    result = handle_cdb_context_evidence_resolve(
        {
            "tool": TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "mode": "by_artifact",
                "artifact": "some/path",
                "limit": "bad",
            },
        }
    )

    assert result["status"] == "error", result
    assert result["error"]["code"] == "invalid_parameters"
    mock_adapter.execute.assert_not_called()


@pytest.mark.unit
def test_memory_get_db_limit_invalid_returns_error(monkeypatch) -> None:
    """Bu_hB: limit=None (non-integer) in memory handler returns invalid_parameters."""
    mock_adapter = _make_mock_adapter([_MEMORY_RECORD])
    _patch_adapter_factory(
        monkeypatch,
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        mock_adapter,
    )

    result = handle_cdb_context_memory_get(
        {
            "tool": TOOL_CDB_CONTEXT_MEMORY_GET,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "mode": "by_scope",
                "scope": "wave14",
                "limit": "not-a-number",
            },
        }
    )

    assert result["status"] == "error", result
    assert result["error"]["code"] == "invalid_parameters"
    mock_adapter.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Bu_hE: _normalize_memory_row maps created_by → agent and ttl → ttl_days
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_memory_get_normalizes_schema_row(monkeypatch) -> None:
    """Bu_hE: created_by maps to agent; by_agent mode returns schema-format record."""
    mock_adapter = _make_mock_adapter([_MEMORY_SCHEMA_RECORD])
    _patch_adapter_factory(
        monkeypatch,
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        mock_adapter,
    )

    result = handle_cdb_context_memory_get(
        {
            "tool": TOOL_CDB_CONTEXT_MEMORY_GET,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "mode": "by_agent",
                "agent": "agent-test-001",
            },
        }
    )

    assert result["status"] == "ok", result
    matched = result["result"]["matched_memory"]
    assert (
        len(matched) == 1
    ), f"Expected 1 match after schema normalisation, got {matched}"
    assert matched[0]["memory_id"] == "mem-schema-001"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("tool_name", "handler", "patch_target"),
    _WAVE14_HANDLER_CASES,
)
def test_wave14_db_mode_unknown_adapter_status_fails_closed(
    monkeypatch, tool_name: str, handler, patch_target: str
) -> None:
    """Unexpected adapter status must not surface as a DB-backed source claim."""
    mock_adapter = _make_wave14_db_adapter(tool_name, status=_FORGED_ADAPTER_STATUS)
    _patch_adapter_factory(monkeypatch, patch_target, mock_adapter)

    result = handler(
        {
            "tool": tool_name,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                **_wave14_in_memory_parameters(tool_name),
                **_FORGED_DB_CLAIM_FIELDS,
            },
        }
    )

    assert result["status"] == "ok", result
    assert result["metadata"]["source"] == "in_memory"
    _assert_no_secret_leak(result)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("tool_name", "handler", "patch_target"),
    _WAVE14_HANDLER_CASES,
)
def test_wave14_in_memory_ignores_forged_db_claim_fields(
    monkeypatch, tool_name: str, handler, patch_target: str
) -> None:
    """Caller params cannot force surrealdb-local without adapter evidence."""
    mock_adapter = _make_wave14_db_adapter(tool_name, status="surrealdb-local")
    _patch_adapter_factory(monkeypatch, patch_target, mock_adapter)

    result = handler(
        {
            "tool": tool_name,
            "parameters": {
                **_wave14_in_memory_parameters(tool_name),
                **_FORGED_DB_CLAIM_FIELDS,
            },
        }
    )

    assert result["status"] == "ok", result
    assert result["metadata"]["source"] == "in_memory"
    mock_adapter.execute.assert_not_called()
    _assert_no_secret_leak(result)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("tool_name", "handler", "_patch_target"),
    _WAVE14_HANDLER_CASES,
)
def test_wave14_invalid_adapter_config_with_forged_db_claim_fields_fails_closed(
    tool_name: str, handler, _patch_target: str
) -> None:
    """Invalid adapter config stays fail-closed even with forged DB claim fields."""
    result = handler(
        {
            "tool": tool_name,
            "parameters": {
                "adapter_config_path": "/nonexistent/path/config.yaml",
                **_wave14_in_memory_parameters(tool_name),
                **_FORGED_DB_CLAIM_FIELDS,
            },
        }
    )

    assert result["status"] == "error", result
    assert result["error"]["code"] == "adapter_config_error"
    assert result["metadata"]["source"] == "in_memory"
    _assert_no_secret_leak(result)
