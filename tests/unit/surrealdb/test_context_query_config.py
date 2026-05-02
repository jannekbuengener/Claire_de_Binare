"""Unit tests for the Context Query local config loader (#2080/#2081)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.surrealdb.context_query import (
    CONFIG_SCHEMA_VERSION,
    EXIT_INPUT_NOT_FOUND,
    EXIT_VALIDATION_ERROR,
    FORBIDDEN_CONTEXT_QUERY_TABLES,
    ConfigValidationError,
    InputNotFoundError,
    load_config,
    main,
)


EXAMPLE_CONFIG = Path("infrastructure/config/surrealdb/context_query.local.example.yaml")


def _write_config(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "context_query.local.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def _valid_config(extra: str = "") -> str:
    return f"""
schema_version: context-query-local/v0
mode:
  surrealdb_apply: forbidden
  surrealdb_write: forbidden
  read_only: true
surreal_url: ws://127.0.0.1:8000/rpc
namespace: cdb_context_local
database: cdb_context_intel
auth_mode: none
timeout: 10
read_only: true
max_limit_default: 100
max_limit_hard: 1000
allowed_tables:
  - repo_artifact
  - doc_chunk
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
{extra}
"""


@pytest.mark.unit
def test_example_config_loads_successfully() -> None:
    config = load_config(EXAMPLE_CONFIG)

    assert config.schema_version == CONFIG_SCHEMA_VERSION
    assert config.read_only is True
    assert config.mode_read_only is True
    assert config.surrealdb_write == "forbidden"
    assert config.surrealdb_apply == "forbidden"
    assert config.max_limit_default <= config.max_limit_hard
    assert set(FORBIDDEN_CONTEXT_QUERY_TABLES).issubset(config.forbidden_tables)
    assert not set(config.allowed_tables).intersection(FORBIDDEN_CONTEXT_QUERY_TABLES)


@pytest.mark.unit
def test_missing_config_returns_exit_3() -> None:
    missing = Path("does-not-exist.yaml")

    with pytest.raises(InputNotFoundError) as excinfo:
        load_config(missing)

    assert excinfo.value.exit_code == EXIT_INPUT_NOT_FOUND
    assert main(["--config", str(missing), "classify", "--statement", "SELECT * FROM doc_chunk"]) == EXIT_INPUT_NOT_FOUND


@pytest.mark.unit
def test_wrong_schema_version_is_validation_failure(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path,
        _valid_config().replace(
            "schema_version: context-query-local/v0", "schema_version: wrong/v0"
        ),
    )

    with pytest.raises(ConfigValidationError):
        load_config(path)
    assert main(["--config", str(path), "classify", "--statement", "SELECT * FROM doc_chunk"]) == EXIT_VALIDATION_ERROR


@pytest.mark.unit
def test_top_level_read_only_false_is_rejected(tmp_path: Path) -> None:
    path = _write_config(tmp_path, _valid_config().replace("read_only: true", "read_only: false", 1))

    with pytest.raises(ConfigValidationError) as excinfo:
        load_config(path)

    assert "read_only" in excinfo.value.message


@pytest.mark.unit
def test_mode_read_only_false_is_rejected(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path,
        _valid_config().replace("  read_only: true", "  read_only: false", 1),
    )

    with pytest.raises(ConfigValidationError) as excinfo:
        load_config(path)

    assert "mode.read_only" in excinfo.value.message


@pytest.mark.unit
def test_mode_surrealdb_write_must_be_forbidden(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path,
        _valid_config().replace("surrealdb_write: forbidden", "surrealdb_write: allowed"),
    )

    with pytest.raises(ConfigValidationError) as excinfo:
        load_config(path)

    assert "surrealdb_write" in excinfo.value.message


@pytest.mark.unit
def test_mode_surrealdb_apply_must_be_forbidden(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path,
        _valid_config().replace("surrealdb_apply: forbidden", "surrealdb_apply: allowed"),
    )

    with pytest.raises(ConfigValidationError) as excinfo:
        load_config(path)

    assert "surrealdb_apply" in excinfo.value.message


@pytest.mark.unit
@pytest.mark.parametrize(
    "field",
    [
        "password",
        "token",
        "api_key",
        "secret",
        "credential",
        "db_password",
        "db-password",
        "client.secret",
        "access_token",
        "accessToken",
        "client_secret",
        "clientSecret",
        "credential_file",
        "credentialFile",
        "apiKey",
    ],
)
def test_secret_fields_are_rejected(tmp_path: Path, field: str) -> None:
    path = _write_config(tmp_path, _valid_config(extra=f"{field}: nope\n"))

    with pytest.raises(ConfigValidationError) as excinfo:
        load_config(path)

    assert field in excinfo.value.message


@pytest.mark.unit
def test_allowed_forbidden_overlap_is_rejected(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path,
        _valid_config().replace("  - governance_state", "  - governance_state\n  - doc_chunk"),
    )

    with pytest.raises(ConfigValidationError) as excinfo:
        load_config(path)

    assert "both allowed_tables and forbidden_tables" in excinfo.value.message


@pytest.mark.unit
def test_trading_state_in_allowed_tables_is_rejected(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path,
        _valid_config().replace("  - doc_chunk", "  - doc_chunk\n  - orders", 1),
    )

    with pytest.raises(ConfigValidationError) as excinfo:
        load_config(path)

    assert "orders" in excinfo.value.message


@pytest.mark.unit
def test_governance_mirror_in_allowed_tables_is_rejected(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path,
        _valid_config().replace(
            "  - doc_chunk", "  - doc_chunk\n  - governance_event", 1
        ),
    )

    with pytest.raises(ConfigValidationError) as excinfo:
        load_config(path)

    assert "governance_event" in excinfo.value.message


@pytest.mark.unit
def test_max_limit_default_may_not_exceed_hard_limit(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path,
        _valid_config().replace("max_limit_default: 100", "max_limit_default: 1001"),
    )

    with pytest.raises(ConfigValidationError) as excinfo:
        load_config(path)

    assert "max_limit_default" in excinfo.value.message


@pytest.mark.unit
def test_forbidden_tables_must_include_all_blocked_tables(tmp_path: Path) -> None:
    path = _write_config(tmp_path, _valid_config().replace("  - execution_state\n", ""))

    with pytest.raises(ConfigValidationError) as excinfo:
        load_config(path)

    assert "missing" in excinfo.value.message
