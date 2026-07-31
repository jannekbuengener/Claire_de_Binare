"""TLS and network overlay contract tests (#3860, #4120).

Static YAML/script classification only — no certificate generation, no network
creation, no productive TLS/network mutation. Parent #3855; quarantine #4120.
"""

from __future__ import annotations

import pytest

from tests.unit.infra import _tls_network_contract_helpers as helpers
from tests.unit.infra._compose_stack_contract_helpers import CANONICAL_RUNTIME_FILES

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_tls_and_network_overlays_parse() -> None:
    tls = helpers.load_overlay_yaml(helpers.TLS_OVERLAY_FILE)
    network = helpers.load_overlay_yaml(helpers.NETWORK_PROD_OVERLAY_FILE)
    assert tls.get("services")
    assert network.get("networks")


def test_tls_overlay_mounts_local_cert_paths_only() -> None:
    scan = helpers.scan_tls_network_contract()
    assert scan.tls_cert_mount_paths
    assert all(".cdb_local/tls" in mount or "/tls" in mount for mount in scan.tls_cert_mount_paths)


def test_tls_overlay_touches_expected_services() -> None:
    scan = helpers.scan_tls_network_contract()
    assert "cdb_redis" in scan.tls_overlay_services
    assert "cdb_postgres" in scan.tls_overlay_services


def test_network_prod_overlay_is_internal_and_nulls_public_ports() -> None:
    scan = helpers.scan_tls_network_contract()
    assert scan.network_prod_internal is True
    assert "cdb_grafana" in scan.network_prod_ports_nulled
    assert "cdb_prometheus" in scan.network_prod_ports_nulled
    assert "cdb_ws" in scan.network_prod_ports_nulled


def test_canonical_runtime_compose_uses_localhost_bindings() -> None:
    scan = helpers.scan_tls_network_contract()
    assert scan.canonical_localhost_bindings
    for binding in scan.canonical_localhost_bindings:
        assert binding.compose_file in CANONICAL_RUNTIME_FILES
        assert binding.kind == "localhost"


def test_public_exposure_is_explicit_finding_not_silent_pass() -> None:
    scan = helpers.scan_tls_network_contract()
    assert scan.public_exposure_findings
    exposed_files = {finding.compose_file for finding in scan.public_exposure_findings}
    assert exposed_files & helpers.KNOWN_PUBLIC_EXPOSURE_FILES


def test_cert_generation_scripts_classified_as_read_only_utilities() -> None:
    scan = helpers.scan_tls_network_contract()
    assert len(scan.cert_utilities) == len(helpers.CERT_UTILITY_SCRIPTS)
    for utility in scan.cert_utilities:
        assert utility.is_cert_utility
        assert utility.mutates_filesystem
        assert "read-only utility" in utility.detail


def test_network_setup_script_exists_but_is_not_executed_by_tests() -> None:
    assert helpers.network_setup_script_is_mutating()
    assert (helpers.REPO_ROOT / helpers.NETWORK_SETUP_SCRIPT).is_file()


def test_service_to_service_names_present_in_tls_and_monitoring_refs() -> None:
    scan = helpers.scan_tls_network_contract()
    assert "cdb_redis" in scan.service_name_references
    assert "cdb_prometheus" in scan.service_name_references


def test_scan_surfaces_limitations() -> None:
    scan = helpers.scan_tls_network_contract()
    assert scan.limitations
    assert any("no Docker network" in item for item in scan.limitations)
    assert any("never generate certificates" in item for item in scan.limitations)


# --- #4120 RETIRE_QUARANTINE -------------------------------------------------


def test_tls_overlay_carries_retire_quarantine_banner() -> None:
    """
    test_id: tc_tls_overlay_quarantine_banner_4120
    test_type: Wissens-Test
    rule_ref: INV-022
    issue_ref: #4120
    decision_ref: RETIRE_QUARANTINE
    """
    scan = helpers.scan_tls_quarantine_contract()
    assert scan.overlay_has_quarantine_banner


def test_tls_setup_guide_is_quarantined_not_implemented() -> None:
    """
    test_id: tc_tls_setup_quarantined_4120
    test_type: Wissens-Test
    rule_ref: INV-022
    issue_ref: #4120
    decision_ref: RETIRE_QUARANTINE
    """
    scan = helpers.scan_tls_quarantine_contract()
    assert scan.setup_is_quarantined
    assert not scan.setup_has_forbidden_active_start


def test_tls_setup_docker_stack_runbook_link_resolves() -> None:
    """
    test_id: tc_tls_setup_runbook_link_4120
    test_type: Wissens-Test
    issue_ref: #4120
    """
    scan = helpers.scan_tls_quarantine_contract()
    assert scan.setup_runbook_link_ok


def test_env_index_does_not_use_tls_setup_as_postgres_canon() -> None:
    """
    test_id: tc_env_index_no_tls_setup_postgres_canon_4120
    test_type: Wissens-Test
    issue_ref: #4120
    decision_ref: RETIRE_QUARANTINE
    """
    scan = helpers.scan_tls_quarantine_contract()
    assert not scan.env_index_points_tls_setup_as_postgres_canon


def test_stack_up_tls_flag_is_fail_closed_legacy_compat() -> None:
    """
    test_id: tc_stack_up_tls_fail_closed_4120
    test_type: Schutz-Test
    rule_ref: INV-022
    issue_ref: #4120
    decision_ref: RETIRE_QUARANTINE
    """
    scan = helpers.scan_tls_quarantine_contract()
    assert scan.stack_up_tls_fail_closed
    assert not scan.stack_up_still_appends_tls_overlay


def test_cdb_local_tls_refs_only_on_quarantined_surfaces() -> None:
    """
    test_id: tc_cdb_local_tls_quarantine_surfaces_4120
    test_type: Wissens-Test
    issue_ref: #4120
    """
    scan = helpers.scan_tls_quarantine_contract()
    # Allowed residual historical refs: overlay body + quarantined guide.
    # stack_up.ps1 and docs/env/index.md must not keep active .cdb_local/tls paths.
    assert helpers.TLS_OVERLAY_REL in scan.cdb_local_tls_refs
    assert helpers.TLS_SETUP_REL in scan.cdb_local_tls_refs
    assert helpers.STACK_UP_REL not in scan.cdb_local_tls_refs
    assert helpers.ENV_INDEX_REL not in scan.cdb_local_tls_refs


def test_tls_quarantine_scan_documents_limitations() -> None:
    scan = helpers.scan_tls_quarantine_contract()
    assert scan.limitations
    assert any("static" in item.lower() for item in scan.limitations)
