"""Unit tests for the Context Indexer CLI scaffold."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.surrealdb.context_indexer import (
    SCHEMA_VERSION,
    WriteDeniedError,
    load_scope_config,
    main,
    validate_output_path,
)


SCOPE_CONFIG = Path("infrastructure/config/surrealdb/context_ingestion_scope.yaml")


@pytest.mark.unit
def test_scope_config_loads_canonical_file() -> None:
    summary = load_scope_config(SCOPE_CONFIG)

    assert summary.schema_version == "context-ingestion-scope/v0"
    assert summary.sensitivity_classes == [
        "forbidden",
        "internal_context",
        "public_context",
        "sensitive_metadata",
    ]
    assert "docs/" in summary.include_paths
    assert "tmp/" in summary.exclude_paths


@pytest.mark.unit
def test_scan_defaults_to_dry_run_and_never_connects_to_surrealdb(capsys) -> None:
    exit_code = main(["scan", "--scope-config", str(SCOPE_CONFIG)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["command"] == "scan"
    assert payload["status"] == "scaffolded"
    assert payload["dry_run"] is True
    assert payload["write_requested"] is False
    assert payload["surrealdb_connection"] == "disabled"
    assert "full_file_discovery" in payload["deferred"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "command", ["scan", "plan", "export-jsonl", "snapshot", "validate"]
)
def test_all_command_stubs_return_scaffold_payload(command: str, capsys) -> None:
    exit_code = main([command, "--scope-config", str(SCOPE_CONFIG), "--dry-run"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == command
    assert payload["status"] == "scaffolded"
    assert payload["surrealdb_connection"] == "disabled"


@pytest.mark.unit
def test_markdown_format_renders_without_writing(capsys) -> None:
    exit_code = main(
        [
            "validate",
            "--scope-config",
            str(SCOPE_CONFIG),
            "--format",
            "markdown",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "# Context Indexer validate" in output
    assert "SurrealDB connection: disabled" in output


@pytest.mark.unit
def test_help_works_for_top_level_and_command(capsys) -> None:
    with pytest.raises(SystemExit) as top_level:
        main(["--help"])
    assert top_level.value.code == 0
    assert "Context Indexer CLI scaffold" in capsys.readouterr().out

    with pytest.raises(SystemExit) as command_help:
        main(["scan", "--help"])
    assert command_help.value.code == 0
    assert "Path to context_ingestion_scope.yaml" in capsys.readouterr().out


@pytest.mark.unit
def test_apply_writes_requires_explicit_output() -> None:
    with pytest.raises(WriteDeniedError):
        validate_output_path(None, apply_writes=True)


@pytest.mark.unit
@pytest.mark.parametrize(
    "output",
    [
        Path("tmp/context-indexer/result.json"),
        Path("reports/context-indexer/result.json"),
        Path("../artifacts/result.json"),
        Path("C:/temp/context-indexer/result.json"),
    ],
)
def test_apply_writes_rejects_unapproved_output_roots(output: Path) -> None:
    with pytest.raises(WriteDeniedError):
        validate_output_path(output, apply_writes=True)


@pytest.mark.unit
@pytest.mark.parametrize(
    "output",
    [
        Path("artifacts/context-indexer/result.json"),
        Path("temp/context-indexer/result.json"),
    ],
)
def test_apply_writes_allows_approved_output_roots(output: Path) -> None:
    assert validate_output_path(output, apply_writes=True) == output


@pytest.mark.unit
@pytest.mark.parametrize("output", [Path("artifacts"), Path("temp")])
def test_apply_writes_rejects_directory_only_output_paths(output: Path) -> None:
    with pytest.raises(WriteDeniedError):
        validate_output_path(output, apply_writes=True)


@pytest.mark.unit
def test_apply_writes_directory_output_returns_structured_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
    scope_config = tmp_path / SCOPE_CONFIG
    scope_config.parent.mkdir(parents=True)
    source_config = Path(__file__).parents[3] / SCOPE_CONFIG
    scope_config.write_text(source_config.read_text(encoding="utf-8"), encoding="utf-8")
    Path("artifacts").mkdir()

    exit_code = main(
        [
            "scan",
            "--scope-config",
            str(scope_config),
            "--apply-writes",
            "--output",
            "artifacts",
        ]
    )

    assert exit_code == 5
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "write_denied"
    assert "output must include a file name" in payload["message"]


@pytest.mark.unit
def test_apply_writes_reports_not_dry_run_and_writes_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
    scope_config = tmp_path / SCOPE_CONFIG
    scope_config.parent.mkdir(parents=True)
    source_config = Path(__file__).parents[3] / SCOPE_CONFIG
    scope_config.write_text(source_config.read_text(encoding="utf-8"), encoding="utf-8")
    output = Path("artifacts/context-indexer/result.json")

    exit_code = main(
        [
            "scan",
            "--scope-config",
            str(scope_config),
            "--apply-writes",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    written_payload = json.loads((tmp_path / output).read_text(encoding="utf-8"))
    assert payload["dry_run"] is False
    assert payload["write_requested"] is True
    assert written_payload["dry_run"] is False
    assert written_payload["write_requested"] is True


@pytest.mark.unit
def test_explicit_dry_run_suppresses_apply_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
    scope_config = tmp_path / SCOPE_CONFIG
    scope_config.parent.mkdir(parents=True)
    source_config = Path(__file__).parents[3] / SCOPE_CONFIG
    scope_config.write_text(source_config.read_text(encoding="utf-8"), encoding="utf-8")
    output = Path("artifacts/context-indexer/result.json")

    exit_code = main(
        [
            "scan",
            "--scope-config",
            str(scope_config),
            "--apply-writes",
            "--dry-run",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["dry_run"] is True
    assert payload["write_requested"] is True
    assert not (tmp_path / output).exists()


@pytest.mark.unit
def test_missing_scope_config_returns_input_not_found(capsys) -> None:
    exit_code = main(
        ["scan", "--scope-config", "missing/context_ingestion_scope.yaml"]
    )

    assert exit_code == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "scope_config_not_found"


@pytest.mark.unit
def test_directory_scope_config_returns_structured_validation_error(
    tmp_path: Path, capsys
) -> None:
    config_dir = tmp_path / "scope-dir"
    config_dir.mkdir()

    exit_code = main(["validate", "--scope-config", str(config_dir)])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "scope_config_invalid"
    assert "scope config is not a file" in payload["message"]


@pytest.mark.unit
def test_invalid_sensitivity_classes_fail_closed(tmp_path: Path, capsys) -> None:
    config = tmp_path / "scope.yaml"
    config.write_text(
        """
schema_version: context-ingestion-scope/v0
include_paths: []
conditional_paths: []
exclude_paths: []
allowed_file_types: []
sensitivity_classes:
  public_context: {}
guardrails: []
""".strip(),
        encoding="utf-8",
    )

    exit_code = main(["validate", "--scope-config", str(config)])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "scope_config_invalid"
    assert "sensitivity classes mismatch" in payload["message"]
