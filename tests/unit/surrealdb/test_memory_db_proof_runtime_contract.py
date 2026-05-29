"""#2603 unit contracts for memory DB proof runtime CLI and env parity.

No live SurrealDB. Fail-closed without adapter / env / confirm.

Issue: #2603
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.surrealdb.memory_db_proof_local_dev import (
    ENV_REAL_SURREALDB_MEMORY_SMOKE,
    QUERY_CONFIG_REL,
)
from tools.surrealdb.memory_db_proof_runtime import (
    RUNTIME_SCHEMA_VERSION,
    check_memory_db_proof_preconditions,
)

_MAKEFILE = Path(__file__).parents[3] / "Makefile"
_CLI = Path(__file__).parents[3] / "tools" / "surrealdb" / "memory_db_proof_cli.py"
_RUNTIME = (
    Path(__file__).parents[3] / "tools" / "surrealdb" / "memory_db_proof_runtime.py"
)


def _read_makefile() -> str:
    return _MAKEFILE.read_text(encoding="utf-8")


@pytest.mark.unit
def test_runtime_and_cli_modules_exist() -> None:
    assert _CLI.is_file()
    assert _RUNTIME.is_file()


@pytest.mark.unit
def test_env_constant_matches_local_tests() -> None:
    from tests.local.surrealdb import memory_db_proof_helpers

    assert (
        memory_db_proof_helpers.ENV_REAL_SURREALDB_MEMORY_SMOKE
        == ENV_REAL_SURREALDB_MEMORY_SMOKE
    )
    assert ENV_REAL_SURREALDB_MEMORY_SMOKE == "CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE"


@pytest.mark.unit
def test_preflight_fail_closed_without_confirm_or_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ENV_REAL_SURREALDB_MEMORY_SMOKE, raising=False)
    with patch(
        "tools.surrealdb.memory_db_proof_runtime.http_status",
        return_value=200,
    ):
        with patch(
            "tools.surrealdb.memory_db_proof_runtime.resolve_secrets_path",
            return_value=None,
        ):
            result = check_memory_db_proof_preconditions(confirm=False)
    assert result["schema_version"] == RUNTIME_SCHEMA_VERSION
    assert result["ok"] is False
    assert any(ENV_REAL_SURREALDB_MEMORY_SMOKE in err for err in result["errors"])


@pytest.mark.unit
def test_preflight_ok_with_confirm_when_health_and_config_ok(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(ENV_REAL_SURREALDB_MEMORY_SMOKE, raising=False)
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "SURREALDB_ENV").write_text(
        "SURREAL_USER=x\nSURREAL_PASS=y\n", encoding="utf-8"
    )
    fake_root = tmp_path / "repo"
    config_dir = fake_root / QUERY_CONFIG_REL.parent
    config_dir.mkdir(parents=True)
    (config_dir / QUERY_CONFIG_REL.name).write_text(
        "schema_version: context-query-local/v0\n", encoding="utf-8"
    )
    with patch(
        "tools.surrealdb.memory_db_proof_runtime.http_status",
        return_value=200,
    ):
        with patch(
            "tools.surrealdb.memory_db_proof_runtime.resolve_secrets_path",
            return_value=secrets,
        ):
            with patch(
                "tools.surrealdb.memory_db_proof_runtime.repo_root",
                return_value=fake_root,
            ):
                result = check_memory_db_proof_preconditions(confirm=True)
    assert result["ok"] is True
    assert result["errors"] == []


@pytest.mark.unit
def test_cli_preflight_exit_codes() -> None:
    from tools.surrealdb.memory_db_proof_cli import EXIT_OK, EXIT_RUNTIME, main

    with patch(
        "tools.surrealdb.memory_db_proof_cli.check_memory_db_proof_preconditions",
        return_value={"ok": True},
    ):
        assert main(["preflight", "--confirm"]) == EXIT_OK
    with patch(
        "tools.surrealdb.memory_db_proof_cli.check_memory_db_proof_preconditions",
        return_value={"ok": False, "errors": ["x"]},
    ):
        assert main(["preflight", "--confirm"]) == EXIT_RUNTIME


@pytest.mark.unit
def test_cli_run_proof_success_prints_json() -> None:
    from tools.surrealdb.memory_db_proof_cli import EXIT_OK, main

    payload = {"schema_version": RUNTIME_SCHEMA_VERSION, "status": "ok"}
    with patch(
        "tools.surrealdb.memory_db_proof_cli.run_memory_db_proof_cycle",
        return_value=payload,
    ):
        with patch("builtins.print") as mock_print:
            code = main(["run-proof", "--confirm"])
    assert code == EXIT_OK
    printed = mock_print.call_args[0][0]
    parsed = json.loads(printed)
    assert parsed["status"] == "ok"


@pytest.mark.unit
def test_makefile_context_memory_db_proof_depends_on_env_check() -> None:
    content = _read_makefile()
    assert "context-memory-db-proof: context-env-check" in content
