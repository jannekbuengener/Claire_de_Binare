"""Shared helpers for monitoring config contract tests (#3861)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from tests.unit.scripts.test_grafana_alerting_provisioning import (
    VALID_EXEC_ERR_STATES,
    VALID_THRESHOLD_TYPES,
    _extract_threshold_evaluators,
    _load_alerting_files,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MONITORING_DIR = REPO_ROOT / "infrastructure" / "monitoring"
GRAFANA_PROVISIONING = MONITORING_DIR / "grafana" / "provisioning"
DATASOURCES_DIR = GRAFANA_PROVISIONING / "datasources"
DASHBOARDS_DIR = MONITORING_DIR / "grafana" / "dashboards"
DASHBOARD_PROVISIONING = GRAFANA_PROVISIONING / "dashboards" / "claire.yml"

VALID_DATASOURCE_TYPES = frozenset({"prometheus", "loki", "postgres", "alertmanager"})


@dataclass(frozen=True)
class MonitoringFinding:
    kind: str
    detail: str


@dataclass(frozen=True)
class MonitoringConfigScan:
    prometheus_jobs: tuple[str, ...]
    prometheus_service_targets: tuple[str, ...]
    datasource_rows: tuple[dict[str, Any], ...]
    datasource_uids: tuple[str, ...]
    datasources_missing_uid: tuple[str, ...]
    dashboard_json_files: tuple[str, ...]
    invalid_alert_operators: tuple[str, ...]
    invalid_exec_err_states: tuple[str, ...]
    alert_unknown_datasource_uids: tuple[str, ...]
    loki_parseable: bool
    promtail_parseable: bool
    limitations: tuple[str, ...]
    findings: tuple[MonitoringFinding, ...] = field(default_factory=tuple)


def load_yaml_file(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_prometheus_config() -> dict[str, Any]:
    data = load_yaml_file(MONITORING_DIR / "prometheus.yml")
    if not isinstance(data, dict):
        raise ValueError("prometheus.yml must parse to mapping")
    return data


def extract_prometheus_service_targets(config: dict[str, Any]) -> list[str]:
    targets: list[str] = []
    for job in config.get("scrape_configs") or []:
        if not isinstance(job, dict):
            continue
        for static_cfg in job.get("static_configs") or []:
            if not isinstance(static_cfg, dict):
                continue
            for target in static_cfg.get("targets") or []:
                host = str(target).split(":", 1)[0]
                if host.startswith("cdb_"):
                    targets.append(host)
    return sorted(set(targets))


def load_grafana_datasources() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(DATASOURCES_DIR.glob("*.yml")):
        doc = load_yaml_file(path)
        for row in doc.get("datasources") or []:
            if isinstance(row, dict):
                row = dict(row)
                row["_source_file"] = path.name
                rows.append(row)
    return rows


def load_dashboard_json_files() -> list[str]:
    return sorted(path.name for path in DASHBOARDS_DIR.glob("*.json"))


def parse_dashboard_json(filename: str) -> dict[str, Any]:
    path = DASHBOARDS_DIR / filename
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Dashboard JSON must be object: {filename}")
    return payload


def collect_invalid_alert_operators() -> list[str]:
    violations: list[str] = []
    for filename, doc in _load_alerting_files().items():
        for ev_info in _extract_threshold_evaluators(doc):
            op_type = ev_info["evaluator"].get("type")
            if op_type not in VALID_THRESHOLD_TYPES:
                violations.append(
                    f"{filename}/{ev_info['rule_title']}: invalid type '{op_type}'"
                )
    return violations


def collect_invalid_exec_err_states() -> list[str]:
    violations: list[str] = []
    for filename, doc in _load_alerting_files().items():
        for group in doc.get("groups", []):
            for rule in group.get("rules", []):
                state = rule.get("execErrState")
                if state not in VALID_EXEC_ERR_STATES:
                    violations.append(
                        f"{filename}/{rule.get('title')}: invalid execErrState '{state}'"
                    )
    return violations


def collect_alert_unknown_datasource_uids(
    known_uids: set[str],
) -> list[str]:
    unknown: list[str] = []
    for filename, doc in _load_alerting_files().items():
        for group in doc.get("groups", []):
            for rule in group.get("rules", []):
                for entry in rule.get("data", []):
                    uid = entry.get("datasourceUid")
                    if uid and uid != "__expr__" and uid not in known_uids:
                        unknown.append(
                            f"{filename}/{rule.get('title')}: unknown datasourceUid '{uid}'"
                        )
    return unknown


def scan_monitoring_config() -> MonitoringConfigScan:
    prometheus = load_prometheus_config()
    jobs = tuple(
        sorted(
            str(job.get("job_name"))
            for job in (prometheus.get("scrape_configs") or [])
            if isinstance(job, dict) and job.get("job_name")
        )
    )
    service_targets = tuple(extract_prometheus_service_targets(prometheus))

    datasource_rows = tuple(load_grafana_datasources())
    uids = tuple(
        sorted(
            str(row["uid"])
            for row in datasource_rows
            if isinstance(row.get("uid"), str) and row.get("uid")
        )
    )
    missing_uid = tuple(
        sorted(
            f"{row.get('_source_file')}:{row.get('name', 'unknown')}"
            for row in datasource_rows
            if not row.get("uid")
        )
    )

    dashboard_files = tuple(load_dashboard_json_files())

    invalid_ops = tuple(collect_invalid_alert_operators())
    invalid_exec = tuple(collect_invalid_exec_err_states())
    known_uids = set(uids) | {"__expr__", "prometheus"}
    unknown_ds = tuple(collect_alert_unknown_datasource_uids(known_uids))

    loki_parseable = False
    promtail_parseable = False
    try:
        load_yaml_file(MONITORING_DIR / "loki-config.yml")
        loki_parseable = True
    except (OSError, yaml.YAMLError, ValueError):
        pass
    try:
        load_yaml_file(MONITORING_DIR / "promtail-config.yml")
        promtail_parseable = True
    except (OSError, yaml.YAMLError, ValueError):
        pass

    findings: list[MonitoringFinding] = []
    if missing_uid:
        findings.append(
            MonitoringFinding(
                kind="datasource_missing_uid",
                detail=f"Datasources without uid: {', '.join(missing_uid)}",
            )
        )
    for violation in invalid_ops:
        findings.append(
            MonitoringFinding(kind="invalid_alert_operator", detail=violation)
        )
    for violation in unknown_ds:
        findings.append(
            MonitoringFinding(kind="invalid_alert_datasource", detail=violation)
        )

    limitations = (
        "Static YAML/JSON parse only; Grafana/Prometheus/Loki not started or queried.",
        "Datasource UID gaps are surfaced as findings, not auto-corrected.",
        "Alert operator contract reuses tests/unit/scripts/test_grafana_alerting_provisioning.py.",
        "Does not touch Dependabot PR #3755.",
    )

    return MonitoringConfigScan(
        prometheus_jobs=jobs,
        prometheus_service_targets=service_targets,
        datasource_rows=datasource_rows,
        datasource_uids=uids,
        datasources_missing_uid=missing_uid,
        dashboard_json_files=dashboard_files,
        invalid_alert_operators=invalid_ops,
        invalid_exec_err_states=invalid_exec,
        alert_unknown_datasource_uids=unknown_ds,
        loki_parseable=loki_parseable,
        promtail_parseable=promtail_parseable,
        limitations=limitations,
        findings=tuple(findings),
    )
