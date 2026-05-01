"""Unit tests for the Context Importer CLI scaffold (#2068)."""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from tools.surrealdb.context_importer import (
    ALLOWED_OUTPUT_PREFIXES,
    EXIT_OK,
    EXIT_UNSUPPORTED_FORMAT,
    EXIT_USAGE_ERROR,
    EXIT_WRITE_DENIED,
    SCHEMA_VERSION,
    SUPPORTED_COMMANDS,
    WriteDeniedError,
    build_parser,
    main,
)


SCAFFOLD_COMMANDS_WITHOUT_APPLY = tuple(
    c for c in SUPPORTED_COMMANDS if c not in {"apply", "validate-jsonl"}
)


def _read_json(capsys) -> dict:
    out = capsys.readouterr().out.strip()
    return json.loads(out)


@pytest.mark.unit
def test_schema_version_constant_is_pinned() -> None:
    assert SCHEMA_VERSION == "context-importer/v0"


@pytest.mark.unit
def test_supported_commands_match_issue_2068_spec() -> None:
    assert SUPPORTED_COMMANDS == (
        "validate-jsonl",
        "plan",
        "dry-run",
        "apply",
        "audit",
        "rollback-plan",
    )


@pytest.mark.unit
def test_top_level_help_exits_zero(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr().out
    assert "context_importer" in captured
    # All v0 commands must appear in help output.
    for command in SUPPORTED_COMMANDS:
        assert command in captured


@pytest.mark.unit
@pytest.mark.parametrize("command", SUPPORTED_COMMANDS)
def test_subcommand_help_exits_zero(command: str, capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main([command, "--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert command in out
    assert "--dry-run" in out
    assert "--apply" in out


@pytest.mark.unit
@pytest.mark.parametrize("command", SCAFFOLD_COMMANDS_WITHOUT_APPLY)
def test_scaffold_commands_default_to_dry_run(command: str, capsys) -> None:
    exit_code = main([command])
    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["command"] == command
    assert payload["status"] == "scaffold-ack"
    assert payload["dry_run"] is True
    assert payload["apply_requested"] is False
    assert payload["surrealdb_connection"] == "disabled"
    assert payload["implemented"] is False


@pytest.mark.unit
def test_apply_subcommand_is_hard_blocked(capsys) -> None:
    exit_code = main(["apply"])
    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["status"] == "error"
    assert payload["error"] == "WRITE_DENIED"
    assert "apply" in payload["message"].lower()


@pytest.mark.unit
@pytest.mark.parametrize("command", SCAFFOLD_COMMANDS_WITHOUT_APPLY)
def test_apply_flag_is_hard_blocked_on_any_command(command: str, capsys) -> None:
    exit_code = main([command, "--apply"])
    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"


@pytest.mark.unit
def test_unknown_subcommand_exits_with_argparse_usage_error(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["does-not-exist"])
    # argparse uses exit code 2 for usage errors, which matches our contract.
    assert excinfo.value.code == EXIT_USAGE_ERROR


@pytest.mark.unit
def test_unsupported_format_is_rejected_by_argparse(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["plan", "--format", "xml"])
    # argparse rejects choices before we ever reach our handler.
    assert excinfo.value.code == EXIT_USAGE_ERROR


@pytest.mark.unit
def test_jsonl_format_renders_single_line(capsys) -> None:
    exit_code = main(["plan", "--format", "jsonl"])
    assert exit_code == EXIT_OK
    out = capsys.readouterr().out.strip()
    assert "\n" not in out
    payload = json.loads(out)
    assert payload["command"] == "plan"


@pytest.mark.unit
def test_markdown_format_renders_human_readable(capsys) -> None:
    exit_code = main(["plan", "--format", "markdown"])
    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert out.startswith("# context_importer: plan")
    assert "**status**" in out


@pytest.mark.unit
def test_report_output_path_outside_whitelist_is_rejected(capsys) -> None:
    exit_code = main(["plan", "--report-output", "etc/foo.json"])
    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"


@pytest.mark.unit
@pytest.mark.parametrize("prefix", ALLOWED_OUTPUT_PREFIXES)
def test_report_output_path_in_whitelist_is_accepted(prefix: str, capsys) -> None:
    exit_code = main(["plan", "--report-output", f"{prefix}/run/report.json"])
    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    assert payload["status"] == "scaffold-ack"


@pytest.mark.unit
def test_report_output_traversal_is_rejected(capsys) -> None:
    exit_code = main(
        ["plan", "--report-output", str(Path("artifacts") / ".." / "secret.json")]
    )
    assert exit_code == EXIT_WRITE_DENIED


@pytest.mark.unit
def test_absolute_report_output_is_rejected(capsys) -> None:
    # Use a path that is absolute on every platform.
    abs_path = "/etc/foo.json"
    exit_code = main(["plan", "--report-output", abs_path])
    assert exit_code == EXIT_WRITE_DENIED


@pytest.mark.unit
def test_no_socket_connection_is_attempted(monkeypatch, capsys) -> None:
    """The scaffold must not open any network socket."""

    def _boom(*args, **kwargs):  # pragma: no cover - safety net
        raise AssertionError(
            "context_importer scaffold must not open network sockets"
        )

    monkeypatch.setattr(socket.socket, "connect", _boom)
    monkeypatch.setattr(socket.socket, "connect_ex", _boom)

    for command in SCAFFOLD_COMMANDS_WITHOUT_APPLY:
        exit_code = main(
            [
                command,
                "--surreal-url",
                "ws://example.invalid:8000/rpc",
                "--namespace",
                "ns",
                "--database",
                "db",
            ]
        )
        assert exit_code == EXIT_OK
        payload = _read_json(capsys)
        assert payload["surrealdb_connection"] == "disabled"


@pytest.mark.unit
def test_no_filesystem_writes_in_scaffold(tmp_path, monkeypatch, capsys) -> None:
    """The scaffold must not create files even when --report-output is given."""

    target = tmp_path / "artifacts" / "report.json"
    monkeypatch.chdir(tmp_path)
    # Use a relative whitelisted path.
    rel = Path("artifacts") / "report.json"
    exit_code = main(["plan", "--report-output", str(rel)])
    assert exit_code == EXIT_OK
    assert not target.exists()
    assert not (tmp_path / "artifacts").exists()


@pytest.mark.unit
def test_write_denied_error_carries_exit_code() -> None:
    exc = WriteDeniedError("nope")
    assert exc.code == "WRITE_DENIED"
    assert exc.exit_code == EXIT_WRITE_DENIED


@pytest.mark.unit
def test_unsupported_format_exit_code_constant_is_unused_by_argparse() -> None:
    # argparse handles --format choices itself, but our internal renderer
    # keeps an UnsupportedFormatError path. The constant must stay distinct.
    assert EXIT_UNSUPPORTED_FORMAT == 4
    assert EXIT_USAGE_ERROR == 2


@pytest.mark.unit
def test_build_parser_returns_argparse_parser() -> None:
    parser = build_parser()
    # Smoke check: the parser knows about every documented command.
    helps = parser.format_help()
    for command in SUPPORTED_COMMANDS:
        assert command in helps
