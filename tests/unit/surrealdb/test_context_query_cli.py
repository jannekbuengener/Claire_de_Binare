"""CLI smoke tests for Context Query scaffold (#2080)."""

from __future__ import annotations

import json
import socket

import pytest

from tools.surrealdb.context_query import (
    EXIT_INPUT_NOT_FOUND,
    EXIT_OK,
    EXIT_USAGE_ERROR,
    EXIT_WRITE_DENIED,
    main,
)

EXAMPLE_CONFIG = "infrastructure/config/surrealdb/context_query.local.example.yaml"


def _read_json(capsys) -> dict:
    out = capsys.readouterr().out.strip()
    return json.loads(out)


@pytest.mark.unit
def test_help_exits_zero(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])

    assert excinfo.value.code == 0
    assert "context_query" in capsys.readouterr().out


@pytest.mark.unit
def test_classify_requires_config(capsys) -> None:
    exit_code = main(["classify", "--statement", "SELECT * FROM doc_chunk"])

    assert exit_code == EXIT_INPUT_NOT_FOUND
    payload = _read_json(capsys)
    assert payload["error"] == "INPUT_NOT_FOUND"
    assert "--config is required" in payload["message"]


@pytest.mark.unit
def test_classify_select_exits_zero(capsys) -> None:
    exit_code = main(
        [
            "--config",
            EXAMPLE_CONFIG,
            "classify",
            "--statement",
            "SELECT * FROM doc_chunk",
        ]
    )

    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    assert payload["status"] == "ok"
    assert payload["surrealdb_connection"] == "noop-no-network"
    assert payload["classification"]["operation"] == "SELECT"


@pytest.mark.unit
def test_classify_forbidden_table_exits_write_denied(capsys) -> None:
    exit_code = main(
        [
            "--config",
            EXAMPLE_CONFIG,
            "classify",
            "--statement",
            "SELECT * FROM orders",
        ]
    )

    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"
    assert "forbidden table" in payload["message"]


@pytest.mark.unit
def test_classify_unknown_table_exits_write_denied(capsys) -> None:
    exit_code = main(
        [
            "--config",
            EXAMPLE_CONFIG,
            "classify",
            "--statement",
            "SELECT * FROM unknown_sensitive_table",
        ]
    )

    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"
    assert "outside allowed_tables" in payload["message"]


@pytest.mark.unit
def test_classify_delete_exits_write_denied(capsys) -> None:
    exit_code = main(
        [
            "--config",
            EXAMPLE_CONFIG,
            "classify",
            "--statement",
            "DELETE doc_chunk",
        ]
    )

    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"


@pytest.mark.unit
def test_unsupported_format_exits_argparse_usage_error() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--format", "xml", "classify", "--statement", "SELECT * FROM doc_chunk"])

    assert excinfo.value.code == EXIT_USAGE_ERROR


@pytest.mark.unit
def test_no_network_socket_is_used(monkeypatch, capsys) -> None:
    def _boom(*args, **kwargs):  # pragma: no cover - safety net
        raise AssertionError("context_query must not open network sockets")

    monkeypatch.setattr(socket.socket, "connect", _boom)
    monkeypatch.setattr(socket.socket, "connect_ex", _boom)

    exit_code = main(
        [
            "--config",
            EXAMPLE_CONFIG,
            "classify",
            "--statement",
            "INFO FOR TABLE doc_chunk",
        ]
    )

    assert exit_code == EXIT_OK
    assert _read_json(capsys)["surrealdb_connection"] == "noop-no-network"


@pytest.mark.unit
def test_find_symbol_requires_config(capsys) -> None:
    exit_code = main(["find-symbol", "--name", "example"])
    assert exit_code == EXIT_INPUT_NOT_FOUND
    payload = _read_json(capsys)
    assert payload["error"] == "INPUT_NOT_FOUND"


@pytest.mark.unit
def test_find_symbol_exits_zero(capsys) -> None:
    exit_code = main(
        [
            "--config",
            EXAMPLE_CONFIG,
            "find-symbol",
            "--name",
            "example",
        ]
    )
    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    assert payload["status"] == "ok"
    assert payload["command"] == "find-symbol"


@pytest.mark.unit
def test_show_symbol_requires_symbol_id(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--config", EXAMPLE_CONFIG, "show-symbol"])
    assert excinfo.value.code == EXIT_USAGE_ERROR


@pytest.mark.unit
def test_show_symbol_exits_zero(capsys) -> None:
    exit_code = main(
        [
            "--config",
            EXAMPLE_CONFIG,
            "show-symbol",
            "--symbol-id",
            "symbol-example",
        ]
    )
    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    assert payload["status"] == "ok"
    assert payload["command"] == "show-symbol"


@pytest.mark.unit
def test_find_imports_requires_config(capsys) -> None:
    exit_code = main(["find-imports", "--module", "json"])
    assert exit_code == EXIT_INPUT_NOT_FOUND
    payload = _read_json(capsys)
    assert payload["error"] == "INPUT_NOT_FOUND"


@pytest.mark.unit
def test_find_imports_exits_zero(capsys) -> None:
    exit_code = main(
        [
            "--config",
            EXAMPLE_CONFIG,
            "find-imports",
            "--module",
            "json",
        ]
    )
    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    assert payload["status"] == "ok"
    assert payload["command"] == "find-imports"


@pytest.mark.unit
def test_show_imports_for_artifact_requires_source_hash(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--config", EXAMPLE_CONFIG, "show-imports-for-artifact"])
    assert excinfo.value.code == EXIT_USAGE_ERROR


@pytest.mark.unit
def test_show_imports_for_artifact_exits_zero(capsys) -> None:
    exit_code = main(
        [
            "--config",
            EXAMPLE_CONFIG,
            "show-imports-for-artifact",
            "--source-hash",
            "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
        ]
    )
    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    assert payload["status"] == "ok"
    assert payload["command"] == "show-imports-for-artifact"
