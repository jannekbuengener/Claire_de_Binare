"""TLS and network overlay contract tests (#3860).

Static YAML/script classification only — no certificate generation, no network
creation, no productive TLS/network mutation. Parent #3855.
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
