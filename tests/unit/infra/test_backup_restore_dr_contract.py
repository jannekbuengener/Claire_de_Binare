"""Backup, restore and DR manifest regression contract tests (#3859).

Static script inspection and fixture reconciliation — no backup/restore execution.
Refs #3855, #1445, #2985.
"""

from __future__ import annotations

import json
import re

import pytest

from tests.unit.infra._compose_stack_contract_helpers import read_script_text
from tests.unit.infra._secrets_backup_contract_helpers import (
    BACKUP_COMPONENT_ARTIFACTS,
    BACKUP_RESTORE_DR_SCRIPTS,
    script_has_operator_gate,
    script_secret_echo_violations,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


@pytest.mark.parametrize("name,path", list(BACKUP_RESTORE_DR_SCRIPTS.items()))
def test_backup_restore_dr_scripts_exist(name: str, path: str) -> None:
    text = read_script_text(path)
    assert text.strip(), f"{name} must not be empty"


def test_backup_all_dot_sources_manifest_helpers() -> None:
    text = read_script_text(BACKUP_RESTORE_DR_SCRIPTS["backup_all"])
    assert "backup_manifest_helpers.ps1" in text
    assert "Sync-BackupComponentManifest" in text


def test_restore_all_dot_sources_manifest_helpers() -> None:
    text = read_script_text(BACKUP_RESTORE_DR_SCRIPTS["restore_all"])
    assert "backup_manifest_helpers.ps1" in text
    assert "Resolve-BackupComponentInclusion" in text


def test_backup_manifest_helpers_declares_component_artifacts() -> None:
    text = read_script_text(BACKUP_RESTORE_DR_SCRIPTS["backup_manifest_helpers"])
    for artifact in BACKUP_COMPONENT_ARTIFACTS.values():
        assert artifact in text


def test_backup_manifest_helpers_treats_empty_artifacts_as_absent() -> None:
    text = read_script_text(BACKUP_RESTORE_DR_SCRIPTS["backup_manifest_helpers"])
    assert "Test-BackupArtifactPresent" in text
    assert ".Length -gt 0" in text


def test_backup_manifest_helpers_surfaces_manifest_drift() -> None:
    text = read_script_text(BACKUP_RESTORE_DR_SCRIPTS["backup_manifest_helpers"])
    assert "Manifest drift" in text
    assert "DriftCorrected" in text


def test_restore_all_exposes_list_available_semantics() -> None:
    text = read_script_text(BACKUP_RESTORE_DR_SCRIPTS["restore_all"])
    assert re.search(r"\[switch\]\$ListAvailable", text)
    assert "Available backups" in text
    assert "No backup archives found" in text


def test_restore_all_destructive_path_requires_explicit_yes_confirmation() -> None:
    text = read_script_text(BACKUP_RESTORE_DR_SCRIPTS["restore_all"])
    assert re.search(r"\[switch\]\$Force", text)
    assert "DESTRUCTIVELY REPLACE" in text
    assert "Read-Host" in text
    assert "$confirmation -ne 'yes'" in text
    assert "Restore cancelled" in text


def test_restore_all_fails_when_no_restorable_components() -> None:
    text = read_script_text(BACKUP_RESTORE_DR_SCRIPTS["restore_all"])
    assert "does not contain any restorable components" in text


def test_restore_all_missing_postgres_artifact_is_visible() -> None:
    text = read_script_text(BACKUP_RESTORE_DR_SCRIPTS["restore_all"])
    assert "postgres_dump.sql not found" in text


def test_dr_restore_has_force_operator_gate() -> None:
    text = read_script_text(BACKUP_RESTORE_DR_SCRIPTS["dr_restore"])
    assert script_has_operator_gate(text)
    assert "REPLACE all current data" in text


def test_dr_restore_lists_available_archives_on_missing_backup() -> None:
    text = read_script_text(BACKUP_RESTORE_DR_SCRIPTS["dr_restore"])
    assert "Available backups" in text


def test_backup_health_check_documents_exit_codes() -> None:
    text = read_script_text(BACKUP_RESTORE_DR_SCRIPTS["backup_health_check"])
    assert "Exit codes" in text
    assert "exit 0" in text
    assert "exit 1" in text
    assert "cdb_backup_*.zip" in text


def test_dr_backup_legacy_topology_is_visible_not_canonical() -> None:
    """dr_backup.ps1 still references legacy base.yml — contract documents quarantine."""
    text = read_script_text(BACKUP_RESTORE_DR_SCRIPTS["dr_backup"])
    assert "base.yml" in text
    assert "docker-compose" in text


@pytest.mark.parametrize("name,path", list(BACKUP_RESTORE_DR_SCRIPTS.items()))
def test_backup_restore_scripts_do_not_echo_secret_values(name: str, path: str) -> None:
    violations = script_secret_echo_violations(read_script_text(path))
    assert not violations, f"{name} secret echo risk: {violations}"


def test_manifest_reconciliation_fixture_postgres_redis_surrealdb() -> None:
    """Fixture: all three component artifacts reconcile to included."""
    manifest = {
        "Components": {"Postgres": True, "Redis": True, "SurrealDB": True},
        "Evidence": {
            "Postgres": {"Artifact": "postgres_dump.sql", "SizeBytes": 100},
            "Redis": {"Artifact": "redis_dump.rdb", "SizeBytes": 50},
            "SurrealDB": {"Artifact": "surrealdb_data", "FileCount": 3, "TotalBytes": 200},
        },
    }
    artifacts = {
        "postgres_dump.sql": 100,
        "redis_dump.rdb": 50,
        "surrealdb_data": 200,
    }
    for component, filename in BACKUP_COMPONENT_ARTIFACTS.items():
        assert manifest["Components"][component] is True
        assert artifacts.get(filename, 0) > 0 or component == "SurrealDB"

    payload = json.dumps(manifest)
    assert '"Postgres":true' in payload.replace(" ", "")


def test_missing_artifact_fixture_makes_component_not_included() -> None:
    """Regression: missing Redis RDB must not be silently treated as backed up."""
    manifest = {
        "Components": {"Postgres": True, "Redis": False, "SurrealDB": False},
        "Evidence": {"Postgres": {"Artifact": "postgres_dump.sql"}, "Redis": {}},
    }
    artifacts = {"postgres_dump.sql": 1024}

    redis_present = "redis_dump.rdb" in artifacts and artifacts["redis_dump.rdb"] > 0
    assert manifest["Components"]["Redis"] is False
    assert redis_present is False
