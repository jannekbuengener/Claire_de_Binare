"""Secrets SSOT / SECRETS_PATH contract tests (#3858).

Static and fixture-backed guards — no real secrets read, no secret writes.
Refs #3855, #1445, #2985.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.unit.infra._secrets_backup_contract_helpers import (
    ACTIVE_SECRETS_SCRIPTS,
    CANONICAL_COMPOSE_RUNTIME,
    compose_requires_secrets_path,
    read_repo_text,
    script_promotes_legacy_secrets_path,
    script_secret_echo_violations,
    script_uses_canonical_secrets_path,
)
from tests.unit.infra._compose_stack_contract_helpers import read_script_text

pytestmark = [pytest.mark.unit, pytest.mark.contract]


@pytest.mark.parametrize("name,path", list(ACTIVE_SECRETS_SCRIPTS.items()))
def test_active_secrets_scripts_exist(name: str, path: str) -> None:
    text = read_script_text(path)
    assert text.strip(), f"{name} must not be empty"


@pytest.mark.parametrize("name,path", list(ACTIVE_SECRETS_SCRIPTS.items()))
def test_active_secrets_scripts_use_canonical_documents_path(name: str, path: str) -> None:
    text = read_script_text(path)
    assert script_uses_canonical_secrets_path(text), (
        f"{name} must reference ~/Documents/.secrets/.cdb (or SECRETS_PATH)"
    )


@pytest.mark.parametrize("name,path", list(ACTIVE_SECRETS_SCRIPTS.items()))
def test_active_secrets_scripts_do_not_promote_legacy_cdb_local(name: str, path: str) -> None:
    text = read_script_text(path)
    assert not script_promotes_legacy_secrets_path(text), (
        f"{name} must not use legacy .cdb_local/.secrets as current canon"
    )


@pytest.mark.parametrize("compose_path", CANONICAL_COMPOSE_RUNTIME)
def test_canonical_compose_fail_closed_on_missing_secrets_path(compose_path: str) -> None:
    text = read_repo_text(compose_path)
    assert compose_requires_secrets_path(text), (
        f"{compose_path} must require SECRETS_PATH via :?SECRETS_PATH must be set"
    )


def test_gitignore_quarantines_env_runtime_exports() -> None:
    gitignore = read_repo_text(".gitignore")
    assert "*.env.runtime" in gitignore


def test_rotate_secrets_documents_env_runtime_as_optional_export() -> None:
    text = read_script_text(ACTIVE_SECRETS_SCRIPTS["rotate_secrets"])
    assert ".env.runtime" in text
    readme = read_repo_text("tools/secrets/README.md")
    assert "No `.env.runtime` required for normal operation" in readme


def test_tools_secrets_readme_marks_legacy_paths_as_deprecated() -> None:
    readme = read_repo_text("tools/secrets/README.md")
    assert "LEGACY" in readme
    assert ".cdb_local" in readme
    assert "nicht mehr kanonisch" in readme or "NICHT VERWENDEN" in readme


def test_manage_secrets_validate_reports_length_not_payload() -> None:
    text = read_script_text(ACTIVE_SECRETS_SCRIPTS["manage_secrets"])
    assert "$length = $content.Trim().Length" in text
    assert "SET ($length chars)" in text
    assert "Write-Host $content" not in text


@pytest.mark.parametrize("name,path", list(ACTIVE_SECRETS_SCRIPTS.items()))
def test_secrets_scripts_do_not_echo_secret_values(name: str, path: str) -> None:
    violations = script_secret_echo_violations(read_script_text(path))
    assert not violations, f"{name} secret echo risk: {violations}"


def test_core_secrets_module_uses_docker_secrets_and_env_fallback() -> None:
    text = read_repo_text("core/secrets.py")
    assert "/run/secrets/" in text
    assert "os.getenv" in text
    assert "Never logs secret values" in text


def test_core_domain_secrets_module_uses_docker_then_env() -> None:
    text = read_repo_text("core/domain/secrets.py")
    assert "/run/secrets/" in text
    assert "os.getenv" in text


def test_secrets_ssot_runbook_points_to_external_store_only() -> None:
    runbook = read_repo_text("docs/runbooks/cdb_secrets_ssot.md")
    assert ".secrets" in runbook
    assert "Never store secret values in repository" in runbook
    assert "never values" in runbook.lower() or "never values" in runbook


def test_candidate_secrets_paths_prefers_env_over_default(tmp_path: Path, monkeypatch) -> None:
    from tools.surrealdb.memory_db_proof_local_dev import (
        candidate_secrets_paths,
        resolve_secrets_path,
    )

    synthetic = tmp_path / "synthetic-secrets"
    synthetic.mkdir()
    (synthetic / "SURREALDB_ENV").write_text("SURREAL_USER=test\n", encoding="utf-8")

    monkeypatch.setenv("SECRETS_PATH", str(synthetic))
    paths = candidate_secrets_paths()
    assert paths[0] == synthetic

    resolved = resolve_secrets_path()
    assert resolved == synthetic


def test_resolve_secrets_path_returns_none_when_no_synthetic_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tools.surrealdb.memory_db_proof_local_dev import resolve_secrets_path

    monkeypatch.delenv("SECRETS_PATH", raising=False)
    monkeypatch.delenv("CDB_CONTEXT_SECRETS_PATH", raising=False)
    missing = Path(os.devnull) / "no-such-secrets-dir"
    monkeypatch.setattr(
        "tools.surrealdb.memory_db_proof_local_dev.candidate_secrets_paths",
        lambda: [missing],
    )
    assert resolve_secrets_path() is None


def test_audit_trail_resolve_secrets_path_uses_documents_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tools.surrealdb.audit_trail_t3_common import resolve_secrets_path

    monkeypatch.delenv("SECRETS_PATH", raising=False)
    default = resolve_secrets_path()
    assert default == Path.home() / "Documents" / ".secrets" / ".cdb"
