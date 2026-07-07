"""Legacy stack script quarantine contract tests (#3862).

Ensures infrastructure/scripts/legacy/ cannot be mistaken for current canon.
No legacy reactivation or topology repair. Parent #3855.
"""

from __future__ import annotations

import pytest

from tests.unit.infra import _legacy_quarantine_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_legacy_directory_lists_expected_scripts() -> None:
    scan = helpers.scan_legacy_quarantine()
    assert scan.legacy_scripts
    assert "stack_boot.ps1" in scan.legacy_scripts
    assert "stack_down.ps1" in scan.legacy_scripts
    assert "generate_stack_scripts.ps1" in scan.legacy_scripts


def test_all_legacy_scripts_carry_legacy_banner() -> None:
    scan = helpers.scan_legacy_quarantine()
    assert not scan.scripts_missing_banner, (
        f"Missing LEGACY banner: {scan.scripts_missing_banner}"
    )


def test_old_compose_path_markers_are_detected() -> None:
    scan = helpers.scan_legacy_quarantine()
    assert scan.compose_markers
    markers = {finding.marker for finding in scan.compose_markers}
    assert "base.yml" in markers
    assert "dev.yml" in markers


def test_old_secrets_path_markers_are_detected() -> None:
    scan = helpers.scan_legacy_quarantine()
    assert scan.secrets_markers
    markers = {finding.marker for finding in scan.secrets_markers}
    assert ".cdb_local/.secrets" in markers or ".cdb_local\\.secrets" in markers


def test_old_container_and_network_markers_are_detected() -> None:
    scan = helpers.scan_legacy_quarantine()
    assert scan.container_markers
    markers = {finding.marker for finding in scan.container_markers}
    assert "cdb_core" in markers or "claire_de_binare_cdb_network" in markers


def test_legacy_scripts_reference_canonical_runtime_hints() -> None:
    scan = helpers.scan_legacy_quarantine()
    assert scan.canonical_hints_in_legacy
    joined = "\n".join(scan.canonical_hints_in_legacy)
    assert "compose.blue.yml" in joined or "tools/cdb.ps1" in joined


def test_quarantine_scan_documents_limitations() -> None:
    scan = helpers.scan_legacy_quarantine()
    assert scan.limitations
    assert any("quarantined" in item.lower() for item in scan.limitations)
    assert any("reactivation" in item.lower() for item in scan.limitations)
