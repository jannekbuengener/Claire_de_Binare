"""Unit tests for the Context Indexer CLI scaffold."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from tools.surrealdb.context_indexer import (
    EVIDENCE_REF_TEST_FILE_CONFIDENCE,
    SCHEMA_VERSION,
    IndexerResult,
    ScopeConfigSummary,
    TestCase,
    WriteDeniedError,
    _evidence_refs_from_test_cases,
    build_snapshot,
    jsonl_records,
    load_scope_config,
    main,
    resolve_input_path,
    run_indexer,
    stable_id,
    validate_output_path,
    write_jsonl_exports,
    EXPORT_FILES,
)


SCOPE_CONFIG = Path("infrastructure/config/surrealdb/context_ingestion_scope.yaml")
FIXTURE_ROOT = Path("tests/fixtures/surrealdb/context_indexer")


def _copy_scope_config(tmp_path: Path) -> Path:
    scope_config = tmp_path / SCOPE_CONFIG
    scope_config.parent.mkdir(parents=True)
    source_config = Path(__file__).parents[3] / SCOPE_CONFIG
    scope_config.write_text(source_config.read_text(encoding="utf-8"), encoding="utf-8")
    return scope_config


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
    assert payload["status"] == "completed"
    assert payload["dry_run"] is True
    assert payload["write_requested"] is False
    assert payload["surrealdb_connection"] == "disabled"


@pytest.mark.unit
@pytest.mark.parametrize(
    "command", ["scan", "plan", "snapshot"]
)
def test_command_payloads_return_offline_results(command: str, capsys) -> None:
    exit_code = main([command, "--scope-config", str(SCOPE_CONFIG), "--dry-run"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == command
    assert payload["status"] == "completed"
    assert payload["surrealdb_connection"] == "disabled"


@pytest.mark.unit
def test_markdown_format_renders_without_writing(
    tmp_path: Path, capsys
) -> None:
    fixture_root = _copy_fixture_repo(tmp_path, "repo_clean")
    exit_code = main(
        [
            "validate",
            "--root",
            str(fixture_root),
            "--scope-config",
            str(fixture_root / "infrastructure/config/surrealdb/context_ingestion_scope.yaml"),
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
    assert "Context Indexer CLI" in capsys.readouterr().out

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
def test_apply_writes_rejects_symlink_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        Path("artifacts").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    with pytest.raises(WriteDeniedError):
        validate_output_path(Path("artifacts/result.json"), apply_writes=True)


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
    scope_config = _copy_scope_config(tmp_path)
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
    scope_config = _copy_scope_config(tmp_path)
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
    scope_config = _copy_scope_config(tmp_path)
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
def test_write_error_returns_structured_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
    scope_config = _copy_scope_config(tmp_path)
    output_parent = Path("artifacts/context-indexer")
    output_parent.parent.mkdir(parents=True)
    output_parent.write_text("not a directory", encoding="utf-8")

    exit_code = main(
        [
            "scan",
            "--scope-config",
            str(scope_config),
            "--apply-writes",
            "--output",
            "artifacts/context-indexer/result.json",
        ]
    )

    assert exit_code == 5
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "output_write_failed"
    assert "output write failed" in payload["message"]


@pytest.mark.unit
@pytest.mark.parametrize("approved_root", ["artifacts", "temp"])
def test_symlinked_approved_root_returns_structured_containment_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
    approved_root: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    scope_config = _copy_scope_config(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside-root"
    outside.mkdir()
    try:
        Path(approved_root).symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    exit_code = main(
        [
            "scan",
            "--scope-config",
            str(scope_config),
            "--apply-writes",
            "--output",
            f"{approved_root}/context-indexer/result.json",
        ]
    )

    assert exit_code == 5
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "output_path_outside_allowed_roots"


@pytest.mark.unit
@pytest.mark.parametrize("approved_root", ["artifacts", "temp"])
def test_symlinked_child_returns_structured_containment_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
    approved_root: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    scope_config = _copy_scope_config(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside-child"
    outside.mkdir()
    root_dir = tmp_path / approved_root
    root_dir.mkdir()
    try:
        (root_dir / "escape").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    exit_code = main(
        [
            "scan",
            "--scope-config",
            str(scope_config),
            "--apply-writes",
            "--output",
            f"{approved_root}/escape/result.json",
        ]
    )

    assert exit_code == 5
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "output_path_outside_allowed_roots"


@pytest.mark.unit
def test_parent_directory_creation_failure_returns_structured_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
    scope_config = _copy_scope_config(tmp_path)
    original_mkdir = Path.mkdir

    def failing_mkdir(self: Path, *args: object, **kwargs: object) -> None:
        if self == Path("artifacts/context-indexer"):
            raise PermissionError("mkdir blocked for test")
        original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", failing_mkdir)

    exit_code = main(
        [
            "scan",
            "--scope-config",
            str(scope_config),
            "--apply-writes",
            "--output",
            "artifacts/context-indexer/result.json",
        ]
    )

    assert exit_code == 5
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "output_write_failed"
    assert "mkdir blocked for test" in payload["message"]


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
forbidden_patterns: {}
limits:
  max_file_size_bytes: 1024
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


def _copy_fixture_repo(tmp_path: Path, fixture_name: str) -> Path:
    source_root = Path(__file__).parents[3] / FIXTURE_ROOT / fixture_name
    target_root = tmp_path / fixture_name
    shutil.copytree(source_root, target_root)
    return target_root


@pytest.mark.unit
def test_discovery_classification_and_hashing_with_fixture_repo(tmp_path: Path) -> None:
    fixture_root = _copy_fixture_repo(tmp_path, "repo_clean")
    result = run_indexer(
        fixture_root,
        fixture_root / "infrastructure/config/surrealdb/context_ingestion_scope.yaml",
    )

    assert result.run_id.startswith("context-indexer-")
    assert len(result.included_files) == 3
    assert len(result.skipped_files) == 1
    assert len(result.forbidden_files) == 1

    artifact_map = {artifact.source_path: artifact for artifact in result.repo_artifacts}
    assert "docs/guide.md" in artifact_map
    assert "docs/eol_lf.md" in artifact_map
    assert "docs/eol_crlf.md" in artifact_map
    assert "docs/blocked/private.md" not in artifact_map


@pytest.mark.unit
def test_markdown_chunking_keeps_heading_context_and_chunk_links(tmp_path: Path) -> None:
    fixture_root = _copy_fixture_repo(tmp_path, "repo_clean")
    result = run_indexer(
        fixture_root,
        fixture_root / "infrastructure/config/surrealdb/context_ingestion_scope.yaml",
    )

    guide_sections = [section for section in result.doc_sections if section.source_path == "docs/guide.md"]
    assert guide_sections
    assert any(section.heading_path == ["Guide", "Section Alpha"] for section in guide_sections)

    chunks = [chunk for chunk in result.doc_chunks if chunk.source_path == "docs/guide.md"]
    assert chunks
    chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    for section in guide_sections:
        section_chunks = sorted(
            [chunk for chunk in chunks if chunk.section_id == section.section_id],
            key=lambda item: item.chunk_index,
        )
        for index, chunk in enumerate(section_chunks):
            expected_prev = section_chunks[index - 1].chunk_id if index > 0 else None
            expected_next = (
                section_chunks[index + 1].chunk_id
                if index + 1 < len(section_chunks)
                else None
            )
            assert chunk.previous_chunk_id == expected_prev
            assert chunk.next_chunk_id == expected_next
            if chunk.previous_chunk_id is not None:
                assert chunk.previous_chunk_id in chunk_by_id
            if chunk.next_chunk_id is not None:
                assert chunk.next_chunk_id in chunk_by_id


@pytest.mark.unit
def test_jsonl_export_snapshot_and_validation_in_fixture_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture_root = _copy_fixture_repo(tmp_path, "repo_clean")
    monkeypatch.chdir(fixture_root)
    output_dir = Path("artifacts/context-indexer")

    export_exit = main(
        [
            "export-jsonl",
            "--root",
            ".",
            "--scope-config",
            "infrastructure/config/surrealdb/context_ingestion_scope.yaml",
            "--apply-writes",
            "--output",
            str(output_dir),
        ]
    )
    assert export_exit == 0

    for filename in (
        "repo_artifacts.jsonl",
        "doc_pages.jsonl",
        "doc_sections.jsonl",
        "doc_chunks.jsonl",
        "skipped_files.jsonl",
        "forbidden_files.jsonl",
        "evidence_refs.jsonl",
        "claims.jsonl",
        "decision_events.jsonl",
        "agent_memories.jsonl",
        "snapshot.json",
        "validation_report.json",
    ):
        assert (fixture_root / output_dir / filename).exists()

    lines = (fixture_root / output_dir / "repo_artifacts.jsonl").read_text(encoding="utf-8").splitlines()
    assert lines
    first_record = json.loads(lines[0])
    assert first_record["schema_version"] == SCHEMA_VERSION

    snapshot = json.loads((fixture_root / output_dir / "snapshot.json").read_text(encoding="utf-8"))
    assert snapshot["schema_version"] == SCHEMA_VERSION
    assert snapshot["validation"]["blocking_count"] == 0

    validate_exit = main(
        [
            "validate",
            "--root",
            ".",
            "--scope-config",
            "infrastructure/config/surrealdb/context_ingestion_scope.yaml",
            "--format",
            "json",
        ]
    )
    assert validate_exit == 0


@pytest.mark.unit
def test_validation_blocks_secret_pattern_in_included_content(tmp_path: Path) -> None:
    fixture_root = _copy_fixture_repo(tmp_path, "repo_with_secret")
    result = run_indexer(
        fixture_root,
        fixture_root / "infrastructure/config/surrealdb/context_ingestion_scope.yaml",
    )
    report = build_snapshot(result)
    assert report["validation"]["blocking_count"] > 0
    codes = {finding.code for finding in result.blocking_findings}
    assert "content_forbidden_pattern" in codes


@pytest.mark.unit
def test_jsonl_records_and_snapshot_are_consistent(tmp_path: Path) -> None:
    fixture_root = _copy_fixture_repo(tmp_path, "repo_clean")
    result = run_indexer(
        fixture_root,
        fixture_root / "infrastructure/config/surrealdb/context_ingestion_scope.yaml",
    )
    records = jsonl_records(result)
    snapshot = build_snapshot(result)

    assert snapshot["artifact_count"] == len(records["repo_artifacts"])
    assert snapshot["page_count"] == len(records["doc_pages"])
    assert snapshot["section_count"] == len(records["doc_sections"])
    assert snapshot["chunk_count"] == len(records["doc_chunks"])


@pytest.mark.unit
def test_hashing_normalizes_line_endings_in_fixture_repo(tmp_path: Path) -> None:
    fixture_root = _copy_fixture_repo(tmp_path, "repo_clean")
    (fixture_root / "docs/eol_lf.md").write_bytes(b"line one\nline two\n")
    (fixture_root / "docs/eol_crlf.md").write_bytes(b"line one\r\nline two\r\n")

    result = run_indexer(
        fixture_root,
        fixture_root / "infrastructure/config/surrealdb/context_ingestion_scope.yaml",
    )
    artifact_map = {artifact.source_path: artifact for artifact in result.repo_artifacts}
    assert artifact_map["docs/eol_lf.md"].raw_sha256 != artifact_map["docs/eol_crlf.md"].raw_sha256
    assert (
        artifact_map["docs/eol_lf.md"].normalized_sha256
        == artifact_map["docs/eol_crlf.md"].normalized_sha256
    )


_SCOPE_CONFIG_RELATIVE = Path("infrastructure/config/surrealdb/context_ingestion_scope.yaml")

_SCOPE_CONFIG_YAML_TEMPLATE = """\
schema_version: context-ingestion-scope/v0
include_paths:
  - path: {include_path}
    sensitivity_class: public_context
conditional_paths: []
exclude_paths:
  - path: docs/blocked/
    reason: blocked_fixture_path
allowed_file_types:
  - extension: .md
    type: markdown
sensitivity_classes:
  public_context: {{}}
  internal_context: {{}}
  sensitive_metadata: {{}}
  forbidden: {{}}
forbidden_patterns: {{}}
limits:
  max_file_size_bytes: {max_file_size}
guardrails: []
"""


def _make_minimal_repo(base: Path, include_path: str, max_file_size: int = 1048576) -> Path:
    """Create a minimal repo-like directory with a scope config and one doc."""
    config_path = base / _SCOPE_CONFIG_RELATIVE
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        _SCOPE_CONFIG_YAML_TEMPLATE.format(
            include_path=include_path, max_file_size=max_file_size
        ),
        encoding="utf-8",
    )
    doc_dir = base / include_path.rstrip("/")
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir / "readme.md").write_text("# Hello\n\nThis is a test doc.\n", encoding="utf-8")
    return base


@pytest.mark.unit
def test_resolve_input_path_prefers_root_over_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P1: relative scope config must resolve against --root, not caller cwd.

    When both the caller cwd repo and the target root repo contain the same
    relative config path, resolve_input_path must return the path under root.
    """
    caller_repo = tmp_path / "caller_repo"
    target_repo = tmp_path / "target_repo"

    # caller_repo uses docs/ with max_file_size 111111 (distinguishable)
    _make_minimal_repo(caller_repo, include_path="docs/", max_file_size=111111)
    # target_repo uses content/ with max_file_size 999999 (distinguishable)
    _make_minimal_repo(target_repo, include_path="content/", max_file_size=999999)

    # Simulate the caller being cwd — so cwd-first resolution would pick caller_repo config
    monkeypatch.chdir(caller_repo)

    resolved = resolve_input_path(_SCOPE_CONFIG_RELATIVE, target_repo)

    # Must resolve inside target_repo, not caller_repo
    assert resolved.is_relative_to(target_repo), (
        f"Expected path inside target_repo ({target_repo}), got {resolved}"
    )
    assert not resolved.is_relative_to(caller_repo), (
        f"Path must not resolve to caller_repo ({caller_repo}), got {resolved}"
    )

    # Loading the config proves the target repo policy is active, not caller's
    scope = load_scope_config(resolved)
    assert scope.max_file_size_bytes == 999999, (
        f"Expected target_repo max_file_size_bytes=999999, got {scope.max_file_size_bytes}"
    )


@pytest.mark.unit
def test_export_files_includes_wave14_artifacts() -> None:
    wave14_keys = {"evidence_refs", "claims", "decision_events", "agent_memories"}
    missing = wave14_keys - set(EXPORT_FILES)
    assert not missing, f"EXPORT_FILES is missing Wave-14 keys: {missing}"


@pytest.mark.unit
def test_jsonl_records_wave14_non_evidence_placeholders_are_always_empty(tmp_path: Path) -> None:
    """claims, decision_events, agent_memories are always empty regardless of input."""
    fixture_root = _copy_fixture_repo(tmp_path, "repo_clean")
    result = run_indexer(
        fixture_root,
        fixture_root / "infrastructure/config/surrealdb/context_ingestion_scope.yaml",
    )
    records = jsonl_records(result)
    for artifact in ("claims", "decision_events", "agent_memories"):
        assert artifact in records, f"jsonl_records() is missing key: {artifact}"
        assert records[artifact] == [], (
            f"expected empty list for {artifact}, got {records[artifact]!r}"
        )


@pytest.mark.unit
def test_write_jsonl_exports_writes_wave14_files(tmp_path: Path) -> None:
    fixture_root = _copy_fixture_repo(tmp_path, "repo_clean")
    result = run_indexer(
        fixture_root,
        fixture_root / "infrastructure/config/surrealdb/context_ingestion_scope.yaml",
    )
    output_dir = tmp_path / "output"
    write_jsonl_exports(result, output_dir)
    for filename in (
        "evidence_refs.jsonl",
        "claims.jsonl",
        "decision_events.jsonl",
        "agent_memories.jsonl",
    ):
        path = output_dir / filename
        assert path.exists(), f"write_jsonl_exports() did not create {filename}"
        assert path.is_file(), f"{filename} is not a regular file"
        assert path.read_bytes() == b"", f"{filename} should be empty for Wave-14 placeholder"


@pytest.mark.unit
def test_indexer_output_passes_importer_jsonl_file_missing_check(tmp_path: Path) -> None:
    from tools.surrealdb.context_importer import validate_jsonl  # noqa: PLC0415

    fixture_root = _copy_fixture_repo(tmp_path, "repo_clean")
    result = run_indexer(
        fixture_root,
        fixture_root / "infrastructure/config/surrealdb/context_ingestion_scope.yaml",
    )
    output_dir = tmp_path / "output"
    write_jsonl_exports(result, output_dir)

    report = validate_jsonl(output_dir)
    wave14_artifacts = {"evidence_refs", "claims", "decision_events", "agent_memories"}
    file_missing = [
        f
        for f in report.findings
        if f.code == "jsonl_file_missing" and f.artifact in wave14_artifacts
    ]
    assert not file_missing, (
        f"validate_jsonl() produced {len(file_missing)} jsonl_file_missing finding(s) "
        f"for Wave-14 artifacts after write_jsonl_exports: {file_missing}"
    )


# ── Wave-14 evidence_ref generator tests ─────────────────────────────────────

# Minimal fixture factories — avoid running the full indexer pipeline for
# generator-focused unit tests.

_MINIMAL_SCOPE = ScopeConfigSummary(
    path="infrastructure/config/surrealdb/context_ingestion_scope.yaml",
    schema_version="context-ingestion-scope/v0",
    include_paths=[],
    conditional_paths=[],
    exclude_paths=[],
    sensitivity_classes=[],
    include_rules=[],
    conditional_rules=[],
    exclude_rules=[],
    file_type_rules=[],
    forbidden_patterns=[],
    max_file_size_bytes=1048576,
)

# Valid 64-char lowercase hex strings — satisfies importer sha256 format check.
_HASH_ALPHA = "a" * 64
_HASH_BETA = "b" * 64


def _make_result_with_test_cases(test_cases: list[TestCase]) -> IndexerResult:
    return IndexerResult(
        root=Path("."),
        scope_config=_MINIMAL_SCOPE,
        git_commit=None,
        generated_at="2024-01-01T00:00:00Z",
        run_id="run-unit-test-001",
        state_hash="deadbeef",
        files=[],
        repo_artifacts=[],
        doc_pages=[],
        doc_sections=[],
        doc_chunks=[],
        validation_findings=[],
        test_cases=test_cases,
    )


def _make_test_case(source_path: str, source_hash: str, name: str) -> TestCase:
    return TestCase(
        test_id=stable_id("test_case", source_path, name),
        source_path=source_path,
        source_hash=source_hash,
        symbol_id=stable_id("symbol", source_path, name),
        name=name,
        qualified_name=f"{source_path}::{name}",
        line_start=1,
        line_end=10,
        test_type="unit",
        parent_class=None,
        confidence="high",
        inferred=False,
    )


@pytest.mark.unit
def test_evidence_refs_from_test_files_are_deterministic() -> None:
    tc1a = _make_test_case("tests/unit/test_alpha.py", _HASH_ALPHA, "test_foo")
    tc1b = _make_test_case("tests/unit/test_alpha.py", _HASH_ALPHA, "test_bar")
    tc2 = _make_test_case("tests/unit/test_beta.py", _HASH_BETA, "test_baz")
    result = _make_result_with_test_cases([tc1a, tc1b, tc2])

    records_a = _evidence_refs_from_test_cases(result)
    records_b = _evidence_refs_from_test_cases(result)

    assert records_a == records_b
    assert [r["evidence_id"] for r in records_a] == [r["evidence_id"] for r in records_b]


@pytest.mark.unit
def test_evidence_refs_are_per_test_file_not_per_test_case() -> None:
    tcs = [
        _make_test_case("tests/unit/test_alpha.py", _HASH_ALPHA, "test_one"),
        _make_test_case("tests/unit/test_alpha.py", _HASH_ALPHA, "test_two"),
        _make_test_case("tests/unit/test_alpha.py", _HASH_ALPHA, "test_three"),
        _make_test_case("tests/unit/test_beta.py", _HASH_BETA, "test_x"),
    ]
    result = _make_result_with_test_cases(tcs)
    records = _evidence_refs_from_test_cases(result)

    assert len(records) == 2, f"expected 2 records (one per file), got {len(records)}"
    source_paths = [r["source_path"] for r in records]
    assert source_paths == sorted(source_paths), "records must be sorted by source_path"
    assert "tests/unit/test_alpha.py" in source_paths
    assert "tests/unit/test_beta.py" in source_paths


@pytest.mark.unit
def test_evidence_refs_contain_required_fields() -> None:
    tc = _make_test_case("tests/unit/test_alpha.py", _HASH_ALPHA, "test_foo")
    result = _make_result_with_test_cases([tc])
    records = _evidence_refs_from_test_cases(result)

    assert len(records) == 1
    rec = records[0]
    for field in ("schema_version", "run_id", "evidence_id", "created_at"):
        assert field in rec and rec[field], f"required field missing or empty: {field}"
    assert rec["schema_version"] == SCHEMA_VERSION
    assert rec["run_id"] == "run-unit-test-001"
    assert rec["evidence_type"] == "test_file"
    assert rec["source_path"] == "tests/unit/test_alpha.py"
    assert rec["source_hash"] == _HASH_ALPHA
    assert rec["confidence"] == EVIDENCE_REF_TEST_FILE_CONFIDENCE
    assert rec["created_at"] == "2024-01-01T00:00:00Z"


@pytest.mark.unit
def test_evidence_refs_do_not_infer_claim_or_decision_links() -> None:
    tc = _make_test_case("tests/unit/test_alpha.py", _HASH_ALPHA, "test_foo")
    result = _make_result_with_test_cases([tc])
    records = _evidence_refs_from_test_cases(result)

    assert records
    rec = records[0]
    for forbidden_field in ("validates", "invalidates", "related_decisions", "claim_refs"):
        value = rec.get(forbidden_field)
        assert not value, (
            f"evidence_ref must not infer {forbidden_field!r}, got {value!r}"
        )
    comment = rec.get("comment", "")
    for forbidden_phrase in ("human-go", "lr-go", "echtgeld", "live", "approved"):
        assert forbidden_phrase.lower() not in comment.lower(), (
            f"comment must not contain {forbidden_phrase!r}: {comment!r}"
        )


@pytest.mark.unit
def test_wave14_non_evidence_placeholders_remain_empty_with_generator_active() -> None:
    tc = _make_test_case("tests/unit/test_alpha.py", _HASH_ALPHA, "test_foo")
    result = _make_result_with_test_cases([tc])
    records = jsonl_records(result)

    assert records["claims"] == [], "claims must remain empty"
    assert records["decision_events"] == [], "decision_events must remain empty"
    assert records["agent_memories"] == [], "agent_memories must remain empty"
    assert len(records["evidence_refs"]) == 1, "evidence_refs should be populated"


@pytest.mark.unit
def test_evidence_refs_empty_when_no_test_cases() -> None:
    result = _make_result_with_test_cases([])
    records = _evidence_refs_from_test_cases(result)
    assert records == [], f"expected empty list, got {records!r}"


@pytest.mark.unit
def test_generated_evidence_ref_records_pass_importer_field_validation(
    tmp_path: Path,
) -> None:
    """Evidence ref records produced by the generator satisfy importer field requirements.

    Uses direct JSONL file writing (not IndexerResult.write_jsonl_exports) to avoid
    cross-reference violations between synthetic test_cases and absent code_symbols.
    Evidence refs are not subject to source_hash cross-reference checks.
    """
    import json as _json

    from tools.surrealdb.context_importer import (  # noqa: PLC0415
        EXPECTED_JSONL_FILES,
        validate_jsonl,
    )

    tc = _make_test_case("tests/unit/test_alpha.py", _HASH_ALPHA, "test_foo")
    result = _make_result_with_test_cases([tc])
    evidence_records = _evidence_refs_from_test_cases(result)

    for artifact, filename in EXPECTED_JSONL_FILES.items():
        out_file = tmp_path / filename
        if artifact == "evidence_refs":
            lines = [_json.dumps(r) for r in evidence_records]
            out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            out_file.write_bytes(b"")

    report = validate_jsonl(tmp_path, expected_run_id="run-unit-test-001")
    blocking = [f for f in report.findings if f.severity == "blocking"]
    assert not blocking, (
        f"Unexpected blocking findings for generated evidence_refs records: {blocking}"
    )

