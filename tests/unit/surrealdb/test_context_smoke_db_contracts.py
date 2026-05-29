"""Contract tests for the fail-closed DB-backed context smoke (#2460).

Verifies:
- local_schema_check.py --hard-mode exits 1 when container is offline
- local_schema_check.py without --hard-mode exits 0 gracefully when offline (regression)
- context_query.py --min-count N exits 1 when count < N
- context_query.py --min-count 0 (default) does not enforce a floor
- context_query.py --min-count N exits 0 when count >= N
- Makefile context-smoke-db is in .PHONY
- Makefile context-smoke-db target uses --hard-mode for schema check
- Makefile context-smoke-db target uses --adapter surrealdb-local
- Makefile context-smoke-db target uses --hard-mode for query step
- Makefile context-smoke-db target uses --min-count for query step

No live DB, no Docker, no network. All assertions are unit-level or file-read
checks.

Issue: #2460
Epic: #1976
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers / constants
# ---------------------------------------------------------------------------

_MAKEFILE = Path(__file__).parents[3] / "Makefile"
_GEN_RUN_ID = Path(__file__).parents[3] / "tools" / "surrealdb" / "gen_run_id.py"
_EXAMPLE_QUERY_CONFIG = Path(
    "infrastructure/config/surrealdb/context_query.local.example.yaml"
)


def _read_makefile() -> str:
    assert _MAKEFILE.exists(), "Makefile not found"
    return _MAKEFILE.read_text(encoding="utf-8")


def _lines_for_target(content: str, target: str) -> list[str]:
    """Return recipe and conditional lines under a Makefile target."""
    lines = content.splitlines()
    in_target = False
    recipe: list[str] = []
    for line in lines:
        if line.startswith(f"{target}:"):
            in_target = True
            continue
        if in_target:
            if line.startswith("\t"):
                recipe.append(line)
            elif line.startswith("ifeq ") or line.startswith("else") or line.startswith("endif"):
                recipe.append(line)
            elif line.strip() == "" or line.startswith("#"):
                continue
            elif line and not line.startswith("\t") and ":" in line.split()[0]:
                break
            else:
                break
    return recipe


# ---------------------------------------------------------------------------
# 1. local_schema_check: --hard-mode exits 1 if container offline
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_local_schema_check_hard_mode_exits_nonzero_if_offline() -> None:
    """--hard-mode must exit 1 when the container is unreachable (#2460)."""
    from tools.surrealdb import local_schema_check

    with (
        patch.object(local_schema_check, "_health_check", return_value=False),
        patch("sys.argv", ["local_schema_check.py", "--hard-mode"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        local_schema_check.main()

    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# 2. local_schema_check: without --hard-mode exits 0 gracefully (regression)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_local_schema_check_without_hard_mode_exits_zero_if_offline() -> None:
    """Without --hard-mode, container offline must still exit 0 (regression guard)."""
    from tools.surrealdb import local_schema_check

    with (
        patch.object(local_schema_check, "_health_check", return_value=False),
        patch("sys.argv", ["local_schema_check.py"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        local_schema_check.main()

    assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# 3. context_query --min-count exits 1 when count < threshold
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_context_query_min_count_exits_nonzero_if_below_threshold(
    capsys: pytest.CaptureFixture,
) -> None:
    """--min-count 1 must cause exit 1 when query returns 0 records."""
    from tools.surrealdb.context_query import main

    empty_body = json.dumps([{"time": "0ns", "status": "OK", "result": []}]).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = empty_body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_opener = MagicMock()
    mock_opener.open.return_value = mock_resp

    with patch("urllib.request.build_opener", return_value=mock_opener):
        exit_code = main(
            [
                "--config",
                str(_EXAMPLE_QUERY_CONFIG),
                "--adapter",
                "surrealdb-local",
                "--hard-mode",
                "--min-count",
                "1",
                "--secrets-path",
                "/dev/null",
                "show-snapshot",
            ]
        )

    assert (
        exit_code != 0
    ), f"Expected non-zero exit when count=0 and --min-count=1, got {exit_code}"


# ---------------------------------------------------------------------------
# 4. context_query --min-count 0 (default) does not enforce a floor
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_context_query_min_count_default_zero_no_effect(
    capsys: pytest.CaptureFixture,
) -> None:
    """Default --min-count=0 must not cause exit 1 on empty results."""
    from tools.surrealdb.context_query import main, NoopQueryAdapter

    with patch(
        "tools.surrealdb.context_query.NoopQueryAdapter.execute",
        return_value=[],
    ):
        exit_code = main(
            [
                "--config",
                str(_EXAMPLE_QUERY_CONFIG),
                "--adapter",
                "noop",
                "show-snapshot",
            ]
        )

    assert (
        exit_code == 0
    ), f"Expected exit 0 with empty results and default --min-count, got {exit_code}"


# ---------------------------------------------------------------------------
# 5. context_query --min-count satisfied exits 0
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_context_query_min_count_satisfied_exits_zero(
    capsys: pytest.CaptureFixture,
) -> None:
    """--min-count 1 must exit 0 when query returns >= 1 record."""
    from tools.surrealdb.context_query import NoopQueryAdapter, main

    one_row = [{"artifact_id": "a-1", "run_id": "r-1"}]

    with patch.object(NoopQueryAdapter, "execute", return_value=one_row):
        exit_code = main(
            [
                "--config",
                str(_EXAMPLE_QUERY_CONFIG),
                "--adapter",
                "noop",
                "--min-count",
                "1",
                "show-snapshot",
            ]
        )

    assert (
        exit_code == 0
    ), f"Expected exit 0 when count=1 >= --min-count=1, got {exit_code}"


# ---------------------------------------------------------------------------
# 6. Makefile: context-smoke-db in .PHONY
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_makefile_context_smoke_db_in_phony() -> None:
    """context-smoke-db must be declared in .PHONY (#2460)."""
    content = _read_makefile()
    phony_lines = [line for line in content.splitlines() if line.startswith(".PHONY:")]
    assert phony_lines, ".PHONY line not found in Makefile"
    phony_text = " ".join(phony_lines)
    assert (
        "context-smoke-db" in phony_text
    ), "context-smoke-db not found in .PHONY line(s)"


# ---------------------------------------------------------------------------
# 7. Makefile: context-smoke-db uses --hard-mode in schema check step
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_makefile_context_smoke_db_uses_hard_mode_schema_check() -> None:
    """context-smoke-db target must invoke local_schema_check.py with --hard-mode."""
    content = _read_makefile()
    recipe = _lines_for_target(content, "context-smoke-db")
    assert recipe, "context-smoke-db target has no recipe lines"
    recipe_text = "\n".join(recipe)
    assert (
        "local_schema_check.py" in recipe_text
    ), "local_schema_check.py not found in context-smoke-db recipe"
    assert (
        "--hard-mode" in recipe_text
    ), "--hard-mode not found in context-smoke-db recipe (schema check step)"


# ---------------------------------------------------------------------------
# 8. Makefile: context-smoke-db uses --adapter surrealdb-local
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_makefile_context_smoke_db_uses_surrealdb_local_adapter() -> None:
    """context-smoke-db target must pass --adapter surrealdb-local to the importer."""
    content = _read_makefile()
    recipe = _lines_for_target(content, "context-smoke-db")
    recipe_text = "\n".join(recipe)
    assert (
        "--adapter surrealdb-local" in recipe_text
    ), "--adapter surrealdb-local not found in context-smoke-db recipe (import step)"


# ---------------------------------------------------------------------------
# 9. Makefile: context-smoke-db uses --hard-mode in query step
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_makefile_context_smoke_db_uses_hard_mode_query() -> None:
    """context-smoke-db target must pass --hard-mode to the query step."""
    content = _read_makefile()
    recipe = _lines_for_target(content, "context-smoke-db")
    recipe_text = "\n".join(recipe)
    assert (
        "context_query" in recipe_text
    ), "context_query invocation not found in context-smoke-db recipe"
    # Count --hard-mode occurrences: must appear at least twice
    # (once for schema check, once for query)
    occurrences = recipe_text.count("--hard-mode")
    assert (
        occurrences >= 2
    ), f"Expected --hard-mode at least twice in context-smoke-db recipe, found {occurrences}"


# ---------------------------------------------------------------------------
# 10. Makefile: context-smoke-db uses --min-count in query step
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_makefile_context_smoke_db_uses_min_count() -> None:
    """context-smoke-db target must pass --min-count to the query step."""
    content = _read_makefile()
    recipe = _lines_for_target(content, "context-smoke-db")
    recipe_text = "\n".join(recipe)
    assert (
        "--min-count" in recipe_text
    ), "--min-count not found in context-smoke-db recipe (query step)"


# ===========================================================================
# Windows-compatibility contract tests (#2587)
# ===========================================================================

# ---------------------------------------------------------------------------
# 11. Makefile: no POSIX ${SECRETS_PATH:-...} in affected context targets
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_makefile_no_posix_secrets_path_expansion() -> None:
    """No POSIX parameter-expansion default syntax in context smoke targets (#2587)."""
    content = _read_makefile()
    posix_pattern = "${SECRETS_PATH:-"
    targets = [
        "context-schema-apply",
        "context-schema-check",
        "context-import-local",
        "context-smoke-db",
    ]
    for target in targets:
        recipe = _lines_for_target(content, target)
        recipe_text = "\n".join(recipe)
        assert posix_pattern not in recipe_text, (
            f"POSIX secrets-path expansion '{posix_pattern}' still present in "
            f"'{target}' recipe — breaks cmd.exe"
        )


# ---------------------------------------------------------------------------
# 12. Makefile: SECRETS_PATH Make variable defined in preamble
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_makefile_secrets_path_make_variable_defined() -> None:
    """SECRETS_PATH must be defined as a Make variable (not shell expansion) (#2587)."""
    content = _read_makefile()
    assert "SECRETS_PATH ?=" in content, (
        "SECRETS_PATH Make variable not found — required for Windows cmd.exe compat"
    )


# ---------------------------------------------------------------------------
# 13. Makefile: context-scan uses Python pathlib, not mkdir -p
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_makefile_context_scan_no_mkdir_p() -> None:
    """context-scan must not use 'mkdir -p' (POSIX only) (#2587)."""
    content = _read_makefile()
    recipe = _lines_for_target(content, "context-scan")
    assert recipe, "context-scan target has no recipe lines"
    recipe_text = "\n".join(recipe)
    assert "mkdir -p" not in recipe_text, (
        "'mkdir -p' found in context-scan recipe — use Python pathlib instead"
    )
    assert "pathlib" in recipe_text, (
        "Python pathlib not found in context-scan recipe — needed to replace mkdir -p"
    )


# ---------------------------------------------------------------------------
# 14. Makefile: context-smoke-db uses gen_run_id.py for run-id
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_makefile_context_smoke_db_run_id_uses_gen_run_id() -> None:
    """context-smoke-db must use gen_run_id.py for run-id, not shell command substitution (#2587)."""
    content = _read_makefile()
    recipe = _lines_for_target(content, "context-smoke-db")
    recipe_text = "\n".join(recipe)
    assert "gen_run_id.py" in recipe_text, (
        "gen_run_id.py not found in context-smoke-db recipe — required for Windows compat"
    )
    assert "$$($(PYTHON) -c" not in recipe_text, (
        "Shell command substitution '$$($(PYTHON) -c ...)' still present in "
        "context-smoke-db — breaks cmd.exe"
    )


@pytest.mark.unit
def test_makefile_context_smoke_db_run_id_not_parse_time_shell() -> None:
    """run-id must be resolved after context-scan, not via parse-time $(shell ...) (#2603)."""
    content = _read_makefile()
    recipe = _lines_for_target(content, "context-smoke-db")
    recipe_text = "\n".join(recipe)
    assert (
        "$(shell $(PYTHON) tools/surrealdb/gen_run_id.py $(CONTEXT_SNAP_DIR)/snapshot.json)"
        not in recipe_text
    ), (
        "parse-time $(shell gen_run_id.py snapshot.json) causes run_id_mismatch "
        "after context-scan refreshes snapshot.json"
    )


# ---------------------------------------------------------------------------
# 15. Makefile: context-import-local uses gen_run_id.py, not $(date ...)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_makefile_context_import_local_no_posix_date() -> None:
    """context-import-local must not use '$(date ...)' (POSIX only) (#2587)."""
    content = _read_makefile()
    recipe = _lines_for_target(content, "context-import-local")
    assert recipe, "context-import-local target has no recipe lines"
    recipe_text = "\n".join(recipe)
    assert "$(date " not in recipe_text, (
        "'$(date ...)' found in context-import-local recipe — 'date' not in cmd.exe"
    )
    assert "gen_run_id.py" in recipe_text, (
        "gen_run_id.py not found in context-import-local recipe — needed to replace $(date)"
    )


# ---------------------------------------------------------------------------
# 16–17. gen_run_id.py unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_gen_run_id_file_exists() -> None:
    """tools/surrealdb/gen_run_id.py must exist (#2587)."""
    assert _GEN_RUN_ID.exists(), f"gen_run_id.py not found at {_GEN_RUN_ID}"


@pytest.mark.unit
def test_gen_run_id_generates_timestamp_without_args() -> None:
    """gen_run_id with no args must return a 14-digit YYYYMMDDHHMMSS string (#2587)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("gen_run_id", _GEN_RUN_ID)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    result = mod._timestamp_run_id()
    assert result.isdigit(), f"Expected all-digits timestamp, got: {result!r}"
    assert len(result) == 14, f"Expected 14-digit timestamp YYYYMMDDHHMMSS, got: {result!r}"
    # No % characters (cmd.exe safety)
    assert "%" not in result, f"Timestamp contains '%' character: {result!r}"


# ---------------------------------------------------------------------------
# 18. Makefile: context-smoke-db passes smoke scope config to context-scan (#2592)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_makefile_context_smoke_db_uses_smoke_scope_config() -> None:
    """context-smoke-db must override CONTEXT_SCOPE_CONFIG with the smoke scope file (#2592)."""
    content = _read_makefile()
    recipe = _lines_for_target(content, "context-smoke-db")
    assert recipe, "context-smoke-db target has no recipe lines"
    recipe_text = "\n".join(recipe)
    assert "context_ingestion_scope.smoke.yaml" in recipe_text, (
        "context-smoke-db does not pass context_ingestion_scope.smoke.yaml "
        "to context-scan — canonical scope would scan test/service code and "
        "block on content_forbidden_pattern (#2592)"
    )
    # The override must be on the context-scan line, not an unrelated step.
    scan_lines = [line for line in recipe if "context-scan" in line]
    assert scan_lines, "No context-scan call found in context-smoke-db recipe"
    assert any("context_ingestion_scope.smoke.yaml" in line for line in scan_lines), (
        "context-scan invocation in context-smoke-db does not include the "
        "smoke scope config override"
    )


@pytest.mark.unit
def test_gen_run_id_reads_run_id_from_snapshot(tmp_path: Path) -> None:
    """gen_run_id with a snapshot.json arg must return run_id from that file (#2587)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("gen_run_id", _GEN_RUN_ID)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(
        json.dumps({"run_id": "20260520120000", "scope": "smoke"}), encoding="utf-8"
    )
    result = mod._run_id_from_snapshot(str(snapshot))
    assert result == "20260520120000", f"Unexpected run_id: {result!r}"
