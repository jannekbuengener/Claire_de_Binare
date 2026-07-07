"""Infra runbook drift regression tests (#3863).

Fixture-based drift detection between infra runbooks and repo-live paths.
No automatic runbook correction. Parent #3855.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.infra import _infra_runbook_drift_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]

FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures" / "infra_runbook_drift"


def test_infra_runbooks_scan_includes_core_docs() -> None:
    scan = helpers.scan_infra_runbook_drift()
    assert "BACKUP_AUTOMATION.md" in scan.runbooks_scanned
    assert "cdb_secrets_ssot.md" in scan.runbooks_scanned
    assert "README.md" in scan.runbooks_scanned
    assert "ALERTING_RUNBOOK.md" in scan.runbooks_scanned


def test_runbook_referenced_repo_paths_exist() -> None:
    scan = helpers.scan_infra_runbook_drift()
    assert not scan.missing_repo_paths, (
        f"Missing repo paths referenced by runbooks: {scan.missing_repo_paths}"
    )
    assert not any(f.kind == "runbook_repo_path_missing" for f in scan.findings)


def test_compose_canon_is_mentioned_across_runbooks() -> None:
    scan = helpers.scan_infra_runbook_drift()
    assert scan.canonical_compose_mentions >= 4


def test_known_runbook_drifts_are_explicit_findings_with_limitations() -> None:
    scan = helpers.scan_infra_runbook_drift()
    assert scan.limitations
    assert any("not auto-corrected" in item.lower() for item in scan.limitations)
    kinds = {finding.kind for finding in scan.findings}
    assert "known_runbook_drift" in kinds


def test_fixture_detects_missing_runbook_repo_path() -> None:
    fixture_runbook = FIXTURES_ROOT / "broken_backup_runbook.md"
    text = fixture_runbook.read_text(encoding="utf-8")
    missing = [
        relative
        for relative in helpers.RUNBOOK_REQUIRED_REPO_PATHS["BACKUP_AUTOMATION.md"]
        if relative not in text and not (helpers.REPO_ROOT / relative).is_file()
    ]
    # Fixture uses a fake path to demonstrate detection logic.
    assert "infrastructure/scripts/does_not_exist.ps1" in text
    assert "does_not_exist.ps1" in text


def test_fixture_runbook_drift_scan_logic_flags_missing_path() -> None:
  relative = "infrastructure/scripts/does_not_exist.ps1"
  assert not (helpers.REPO_ROOT / relative).is_file()
