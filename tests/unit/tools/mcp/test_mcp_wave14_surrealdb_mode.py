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
