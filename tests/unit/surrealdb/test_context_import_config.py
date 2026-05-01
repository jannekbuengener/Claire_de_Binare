"""Unit tests for the Context Importer local config loader (#2069)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.surrealdb.context_importer import (
    CONFIG_SCHEMA_VERSION,
    EXIT_INPUT_NOT_FOUND,
    EXIT_OK,
    EXIT_VALIDATION_ERROR,
    EXIT_WRITE_DENIED,
    FORBIDDEN_CONTEXT_IMPORT_TABLES,
    load_config,
    main,
)


EXAMPLE_CONFIG = Path("infrastructure/config/surrealdb/context_import.local.example.yaml")


def _read_json(capsys) -> dict:
    out = capsys.readouterr().out.strip()
    return json.loads(out)


def _write_config(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "context_import.local.yaml"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.unit
def test_example_config_loads_with_fail_closed_defaults() -> None:
    config = load_config(EXAMPLE_CONFIG)

    assert config.schema_version == CONFIG_SCHEMA_VERSION
    assert config.allow_apply_default is False
    assert config.auth_mode == "none"
    assert config.surreal_url == "ws://127.0.0.1:8000/rpc"
    assert config.namespace == "cdb_context_local"
    assert config.database == "cdb_context_intel"
    assert set(FORBIDDEN_CONTEXT_IMPORT_TABLES).issubset(config.forbidden_tables)
    assert not set(config.allowed_tables).intersection(FORBIDDEN_CONTEXT_IMPORT_TABLES)


@pytest.mark.unit
def test_cli_loads_config_only_when_explicitly_supplied(capsys) -> None:
    exit_code = main(["plan"])
    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    assert payload["config_loaded"] is False
    assert "config" not in payload

    exit_code = main(["plan", "--config", str(EXAMPLE_CONFIG)])
    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    assert payload["config_loaded"] is True
    assert payload["config"]["schema_version"] == CONFIG_SCHEMA_VERSION
    assert payload["config"]["allow_apply_default"] is False


@pytest.mark.unit
def test_missing_explicit_config_returns_input_not_found(capsys) -> None:
    exit_code = main(["plan", "--config", "does-not-exist.yaml"])

    assert exit_code == EXIT_INPUT_NOT_FOUND
    payload = _read_json(capsys)
    assert payload["status"] == "error"
    assert payload["error"] == "INPUT_NOT_FOUND"


@pytest.mark.unit
def test_apply_paths_short_circuit_before_config_is_read(capsys) -> None:
    exit_code = main(["apply", "--config", "missing.yaml"])
    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"

    exit_code = main(["plan", "--apply", "--config", "missing.yaml"])
    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"


@pytest.mark.unit
def test_config_stat_permission_error_is_user_input_error(
    monkeypatch, capsys
) -> None:
    def _raise_permission_error(self) -> bool:
        raise PermissionError("stat denied")

    monkeypatch.setattr(Path, "exists", _raise_permission_error)

    exit_code = main(["plan", "--config", "blocked.yaml"])

    assert exit_code == EXIT_INPUT_NOT_FOUND
    payload = _read_json(capsys)
    assert payload["status"] == "error"
    assert payload["error"] == "INPUT_NOT_FOUND"
    assert payload["error"] != "INTERNAL"

    exit_code = main(["plan", "--apply", "--config", "blocked.yaml"])
    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"


@pytest.mark.unit
def test_config_rejects_apply_default_true(tmp_path: Path, capsys) -> None:
    path = _write_config(
        tmp_path,
        """
schema_version: context-import-local/v0
surreal_url: ws://127.0.0.1:8000/rpc
namespace: cdb_context_local
database: cdb_context_intel
auth_mode: none
timeout: 10
allow_apply_default: true
allowed_tables:
  - context_document
forbidden_tables:
  - orders
  - fills
  - positions
  - balances
  - pnl
  - risk_state
  - execution_state
  - governance_event
  - governance_decision
  - governance_state
""",
    )

    exit_code = main(["plan", "--config", str(path)])

    assert exit_code == EXIT_VALIDATION_ERROR
    payload = _read_json(capsys)
    assert payload["error"] == "CONFIG_VALIDATION_ERROR"
    assert "allow_apply_default" in payload["message"]


@pytest.mark.unit
def test_config_rejects_forbidden_table_in_allowed_tables(
    tmp_path: Path, capsys
) -> None:
    path = _write_config(
        tmp_path,
        """
schema_version: context-import-local/v0
surreal_url: ws://127.0.0.1:8000/rpc
namespace: cdb_context_local
database: cdb_context_intel
auth_mode: none
timeout: 10
allow_apply_default: false
allowed_tables:
  - context_document
  - orders
forbidden_tables:
  - orders
  - fills
  - positions
  - balances
  - pnl
  - risk_state
  - execution_state
  - governance_event
  - governance_decision
  - governance_state
""",
    )

    exit_code = main(["plan", "--config", str(path)])

    assert exit_code == EXIT_VALIDATION_ERROR
    payload = _read_json(capsys)
    assert payload["error"] == "CONFIG_VALIDATION_ERROR"
    assert "orders" in payload["message"]


@pytest.mark.unit
def test_config_requires_explicit_forbidden_tables(tmp_path: Path, capsys) -> None:
    path = _write_config(
        tmp_path,
        """
schema_version: context-import-local/v0
surreal_url: ws://127.0.0.1:8000/rpc
namespace: cdb_context_local
database: cdb_context_intel
auth_mode: none
timeout: 10
allow_apply_default: false
allowed_tables:
  - context_document
forbidden_tables:
  - orders
""",
    )

    exit_code = main(["plan", "--config", str(path)])

    assert exit_code == EXIT_VALIDATION_ERROR
    payload = _read_json(capsys)
    assert payload["error"] == "CONFIG_VALIDATION_ERROR"
    assert "missing" in payload["message"]


@pytest.mark.unit
def test_apply_remains_hard_blocked_even_with_valid_config(capsys) -> None:
    exit_code = main(["apply", "--config", str(EXAMPLE_CONFIG)])

    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"
