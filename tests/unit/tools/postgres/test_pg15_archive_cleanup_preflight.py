"""Unit tests for PG15 archive cleanup preflight (#3612)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from tools.postgres import pg15_archive_cleanup_preflight as preflight

pytestmark = pytest.mark.unit


def _ready_inputs(**overrides: object) -> preflight.PreflightInputs:
    base = {
        "check_as_of": date(2026, 7, 31),
        "backup_health_pass": True,
        "fresh_backup_reference": "F:/Claire_Backups/cdb_backup_20260731_120000.zip",
        "backup_reference_verified": True,
        "pg_image": "postgres:18.4-alpine@sha256:ecafd34249b5",
        "pg_healthy": True,
        "pg_isready": True,
        "active_cluster_path": "/data/18/",
        "archive_referenced_by_runtime": False,
        "row_counts": dict(preflight.MIGRATION_BASELINE_ROW_COUNTS),
    }
    base.update(overrides)
    return preflight.PreflightInputs(**base)  # type: ignore[arg-type]


def test_all_checks_green_ready_without_mutation() -> None:
    report = preflight.evaluate_preflight(_ready_inputs())
    assert report.status == preflight.READY_FOR_OPERATOR_CLEANUP_GO
    assert report.reason_codes == (preflight.READY_FOR_OPERATOR_CLEANUP_GO,)
    assert report.cleanup_target_candidate == preflight.ARCHIVE_PATH
    assert report.operator_go_required is True
    assert report.destructive_operations == ()
    assert all(check.passed for check in report.checks)


def test_missing_backup_not_ready() -> None:
    report = preflight.evaluate_preflight(
        _ready_inputs(
            backup_health_pass=False,
            fresh_backup_reference=None,
            backup_reference_verified=False,
        )
    )
    assert report.status == preflight.NOT_READY_BACKUP
    assert preflight.NOT_READY_BACKUP in report.reason_codes


def test_wrong_active_cluster_path_not_ready() -> None:
    report = preflight.evaluate_preflight(
        _ready_inputs(active_cluster_path="/var/lib/postgresql/data/")
    )
    assert report.status == preflight.NOT_READY_CLUSTER_PATH
    assert preflight.NOT_READY_CLUSTER_PATH in report.reason_codes


def test_row_count_divergence_not_ready() -> None:
    counts = dict(preflight.MIGRATION_BASELINE_ROW_COUNTS)
    counts["orders"] = 1
    report = preflight.evaluate_preflight(_ready_inputs(row_counts=counts))
    assert report.status == preflight.NOT_READY_ROW_COUNTS
    assert preflight.NOT_READY_ROW_COUNTS in report.reason_codes


def test_archive_referenced_by_runtime_not_ready() -> None:
    report = preflight.evaluate_preflight(
        _ready_inputs(
            archive_referenced_by_runtime=True,
            runtime_config_snippet="volumes:\n  - .pg15_archived:/data/.pg15_archived:ro",
        )
    )
    assert report.status == preflight.NOT_READY_ARCHIVE_REFERENCE
    assert preflight.NOT_READY_ARCHIVE_REFERENCE in report.reason_codes


def test_retention_before_earliest_date_not_ready() -> None:
    report = preflight.evaluate_preflight(_ready_inputs(check_as_of=date(2026, 7, 1)))
    assert report.status == preflight.NOT_READY_RETENTION
    assert preflight.NOT_READY_RETENTION in report.reason_codes


def test_pg18_health_failure_not_ready() -> None:
    report = preflight.evaluate_preflight(
        _ready_inputs(pg_image="postgres:15.18-alpine", pg_healthy=False)
    )
    assert report.status == preflight.NOT_READY_PG18_HEALTH
    assert preflight.NOT_READY_PG18_HEALTH in report.reason_codes


def test_no_generated_command_contains_volume_deletion() -> None:
    report = preflight.evaluate_preflight(_ready_inputs())
    combined = "\n".join(report.informational_commands)
    violations = preflight.collect_forbidden_command_violations(combined)
    assert violations == []


def test_module_source_has_no_destructive_commands() -> None:
    source = preflight.module_source_path().read_text(encoding="utf-8")
    preflight.assert_no_destructive_commands_in_source(source)


def test_inputs_from_mapping_roundtrip() -> None:
    payload = {
        "check_as_of": "2026-07-31",
        "backup_health_pass": True,
        "fresh_backup_reference": "F:/Claire_Backups/cdb_backup_20260731_120000.zip",
        "backup_reference_verified": True,
        "pg_image": "postgres:18.4-alpine",
        "pg_healthy": True,
        "pg_isready": True,
        "active_cluster_path": "/data/18/",
        "row_counts": preflight.MIGRATION_BASELINE_ROW_COUNTS,
    }
    inputs = preflight.inputs_from_mapping(payload)
    report = preflight.evaluate_preflight(inputs)
    assert report.status == preflight.READY_FOR_OPERATOR_CLEANUP_GO


def test_cli_json_output(tmp_path: Path) -> None:
    payload = {
        "check_as_of": "2026-07-31",
        "backup_health_pass": True,
        "fresh_backup_reference": "F:/Claire_Backups/cdb_backup_20260731_120000.zip",
        "backup_reference_verified": True,
        "pg_image": "postgres:18.4-alpine",
        "pg_healthy": True,
        "pg_isready": True,
        "active_cluster_path": "/data/18/",
        "row_counts": preflight.MIGRATION_BASELINE_ROW_COUNTS,
    }
    input_path = tmp_path / "inputs.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    exit_code = preflight.main(["--input", str(input_path), "--json"])
    assert exit_code == 0


def test_all_reason_codes_declared() -> None:
    assert set(preflight.ALL_REASON_CODES) == {
        preflight.READY_FOR_OPERATOR_CLEANUP_GO,
        preflight.NOT_READY_RETENTION,
        preflight.NOT_READY_BACKUP,
        preflight.NOT_READY_PG18_HEALTH,
        preflight.NOT_READY_CLUSTER_PATH,
        preflight.NOT_READY_ROW_COUNTS,
        preflight.NOT_READY_ARCHIVE_REFERENCE,
    }
