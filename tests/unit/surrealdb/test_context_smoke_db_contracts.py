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
_LOCAL_SCHEMA_CHECK = Path(__file__).parents[3] / "tools" / "surrealdb" / "local_schema_check.py"
_EXAMPLE_QUERY_CONFIG = Path(
    "infrastructure/config/surrealdb/context_query.local.example.yaml"
)


def _read_makefile() -> str:
    assert _MAKEFILE.exists(), "Makefile not found"
    return _MAKEFILE.read_text(encoding="utf-8")


def _lines_for_target(content: str, target: str) -> list[str]:
    """Return all indented recipe lines under a Makefile target."""
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
            elif line.strip() == "" or line.startswith("#"):
                continue
            else:
                # New non-indented line = new target or variable; stop.
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

    with patch(
        "urllib.request.build_opener", return_value=mock_opener
    ):
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

    assert exit_code != 0, f"Expected non-zero exit when count=0 and --min-count=1, got {exit_code}"


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

    assert exit_code == 0, f"Expected exit 0 with empty results and default --min-count, got {exit_code}"


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

    assert exit_code == 0, (
        f"Expected exit 0 when count=1 >= --min-count=1, got {exit_code}"
    )


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
    assert "context-smoke-db" in phony_text, (
        "context-smoke-db not found in .PHONY line(s)"
    )


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
    assert "local_schema_check.py" in recipe_text, (
        "local_schema_check.py not found in context-smoke-db recipe"
    )
    assert "--hard-mode" in recipe_text, (
        "--hard-mode not found in context-smoke-db recipe (schema check step)"
    )


# ---------------------------------------------------------------------------
# 8. Makefile: context-smoke-db uses --adapter surrealdb-local
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_makefile_context_smoke_db_uses_surrealdb_local_adapter() -> None:
    """context-smoke-db target must pass --adapter surrealdb-local to the importer."""
    content = _read_makefile()
    recipe = _lines_for_target(content, "context-smoke-db")
    recipe_text = "\n".join(recipe)
    assert "--adapter surrealdb-local" in recipe_text, (
        "--adapter surrealdb-local not found in context-smoke-db recipe (import step)"
    )


# ---------------------------------------------------------------------------
# 9. Makefile: context-smoke-db uses --hard-mode in query step
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_makefile_context_smoke_db_uses_hard_mode_query() -> None:
    """context-smoke-db target must pass --hard-mode to the query step."""
    content = _read_makefile()
    recipe = _lines_for_target(content, "context-smoke-db")
    recipe_text = "\n".join(recipe)
    assert "context_query" in recipe_text, (
        "context_query invocation not found in context-smoke-db recipe"
    )
    # Count --hard-mode occurrences: must appear at least twice
    # (once for schema check, once for query)
    occurrences = recipe_text.count("--hard-mode")
    assert occurrences >= 2, (
        f"Expected --hard-mode at least twice in context-smoke-db recipe, found {occurrences}"
    )


# ---------------------------------------------------------------------------
# 10. Makefile: context-smoke-db uses --min-count in query step
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_makefile_context_smoke_db_uses_min_count() -> None:
    """context-smoke-db target must pass --min-count to the query step."""
    content = _read_makefile()
    recipe = _lines_for_target(content, "context-smoke-db")
    recipe_text = "\n".join(recipe)
    assert "--min-count" in recipe_text, (
        "--min-count not found in context-smoke-db recipe (query step)"
    )
