"""Monitoring config / Grafana / Prometheus provisioning contract tests (#3861).

Static parse checks only — no Grafana/Prometheus/Loki live start or query.
Does not touch Dependabot PR #3755. Parent #3855.
"""

from __future__ import annotations

import pytest

from tests.unit.infra import _monitoring_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_prometheus_config_parseable_with_service_targets() -> None:
    scan = helpers.scan_monitoring_config()
    assert scan.prometheus_jobs
    assert "cdb_execution" in scan.prometheus_service_targets
    assert "cdb_signal" in scan.prometheus_service_targets


def test_grafana_datasource_files_parseable() -> None:
    scan = helpers.scan_monitoring_config()
    assert scan.datasource_rows
    names = {row.get("name") for row in scan.datasource_rows}
    assert {"Prometheus", "PostgreSQL", "Loki"}.issubset(names)


def test_prometheus_datasource_uid_is_canonical() -> None:
    scan = helpers.scan_monitoring_config()
    assert "prometheus" in scan.datasource_uids


def test_datasource_missing_uid_is_explicit_finding() -> None:
    scan = helpers.scan_monitoring_config()
    assert scan.datasources_missing_uid
    assert any("loki.yml" in item.lower() for item in scan.datasources_missing_uid)
    assert any(f.kind == "datasource_missing_uid" for f in scan.findings)


def test_no_invalid_alert_threshold_operators() -> None:
    scan = helpers.scan_monitoring_config()
    assert not scan.invalid_alert_operators


def test_no_invalid_exec_err_states() -> None:
    scan = helpers.scan_monitoring_config()
    assert not scan.invalid_exec_err_states


def test_alert_rules_do_not_reference_unknown_datasource_uids() -> None:
    scan = helpers.scan_monitoring_config()
    assert not scan.alert_unknown_datasource_uids


def test_dashboard_json_files_parseable() -> None:
    scan = helpers.scan_monitoring_config()
    assert scan.dashboard_json_files
    for filename in scan.dashboard_json_files:
        payload = helpers.parse_dashboard_json(filename)
        assert "title" in payload or "panels" in payload or "dashboard" in payload


def test_dashboard_provisioning_yaml_parseable() -> None:
    doc = helpers.load_yaml_file(helpers.DASHBOARD_PROVISIONING)
    providers = doc.get("providers") or []
    assert providers
    assert providers[0].get("type") == "file"


def test_loki_and_promtail_configs_parseable() -> None:
    scan = helpers.scan_monitoring_config()
    assert scan.loki_parseable
    assert scan.promtail_parseable


def test_promtail_pushes_to_cdb_loki_service() -> None:
    promtail = helpers.load_yaml_file(helpers.MONITORING_DIR / "promtail-config.yml")
    clients = promtail.get("clients") or []
    assert clients
    assert "cdb_loki" in str(clients[0].get("url", ""))


def test_scan_surfaces_limitations_and_does_not_start_monitoring() -> None:
    scan = helpers.scan_monitoring_config()
    assert scan.limitations
    assert any("not started" in item.lower() for item in scan.limitations)
    assert any("#3755" in item for item in scan.limitations)
