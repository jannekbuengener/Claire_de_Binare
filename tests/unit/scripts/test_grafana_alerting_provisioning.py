"""Validation tests for Grafana alerting provisioning YAML files.

Grafana's __expr__ threshold evaluator accepts only these operator types:
  gt, lt, within_range, outside_range

Any other value (e.g. gte, lte, eq, ne) causes a parse error during rule
evaluation, which surfaces as a DatasourceError alert instead of a real
rule evaluation — and can produce misleading incident-like notifications.

Issue #1265: circuit_breaker.yml had `type: gte` which caused DatasourceError
mails that looked like real Circuit Breaker incidents.

These tests pin the valid operator contract and document the regression
boundary so the bug cannot be silently reintroduced.
"""

from __future__ import annotations

import pathlib
from typing import Any

import yaml

ALERTING_DIR = (
    pathlib.Path(__file__).resolve().parents[3]
    / "infrastructure"
    / "monitoring"
    / "grafana"
    / "provisioning"
    / "alerting"
)

# Grafana's __expr__ threshold evaluator accepted operator types.
# Source: Grafana Alert Rule API / provisioning schema.
VALID_THRESHOLD_TYPES = {"gt", "lt", "within_range", "outside_range"}


def _load_alerting_files() -> dict[str, Any]:
    """Load all .yml files from the alerting provisioning directory."""
    result: dict[str, Any] = {}
    for path in sorted(ALERTING_DIR.glob("*.yml")):
        with path.open(encoding="utf-8") as fh:
            result[path.name] = yaml.safe_load(fh)
    return result


def _extract_threshold_evaluators(doc: Any) -> list[dict[str, Any]]:
    """Walk the document and collect all evaluator dicts from __expr__ rules."""
    evaluators: list[dict[str, Any]] = []
    for group in doc.get("groups", []):
        for rule in group.get("rules", []):
            for data_entry in rule.get("data", []):
                if data_entry.get("datasourceUid") != "__expr__":
                    continue
                for cond in data_entry.get("model", {}).get("conditions", []):
                    ev = cond.get("evaluator")
                    if ev:
                        evaluators.append(
                            {
                                "rule_uid": rule.get("uid", "unknown"),
                                "rule_title": rule.get("title", "unknown"),
                                "evaluator": ev,
                            }
                        )
    return evaluators


# ---------------------------------------------------------------------------
# YAML syntax
# ---------------------------------------------------------------------------


class TestAlertingYamlSyntax:
    """Each alerting provisioning file must be parseable YAML."""

    def test_circuit_breaker_parseable(self) -> None:
        docs = _load_alerting_files()
        assert "circuit_breaker.yml" in docs, "circuit_breaker.yml must exist"
        assert docs["circuit_breaker.yml"] is not None

    def test_high_error_rate_parseable(self) -> None:
        docs = _load_alerting_files()
        assert "high_error_rate.yml" in docs
        assert docs["high_error_rate.yml"] is not None

    def test_orders_rejected_parseable(self) -> None:
        docs = _load_alerting_files()
        assert "orders_rejected.yml" in docs
        assert docs["orders_rejected.yml"] is not None

    def test_all_files_parseable(self) -> None:
        docs = _load_alerting_files()
        assert len(docs) >= 3, "At least 3 alerting provisioning files expected"


# ---------------------------------------------------------------------------
# Threshold operator contract
# ---------------------------------------------------------------------------


class TestThresholdOperatorValidity:
    """All __expr__ evaluators must use a Grafana-accepted operator type.

    Invalid types cause DatasourceError during rule evaluation.
    Regression test for Issue #1265 (circuit_breaker had `type: gte`).
    """

    def test_no_invalid_operator_in_any_file(self) -> None:
        """No alerting file may contain an invalid threshold operator."""
        docs = _load_alerting_files()
        violations: list[str] = []
        for filename, doc in docs.items():
            for ev_info in _extract_threshold_evaluators(doc):
                op_type = ev_info["evaluator"].get("type")
                if op_type not in VALID_THRESHOLD_TYPES:
                    violations.append(
                        f"{filename} / {ev_info['rule_title']}: "
                        f"invalid type '{op_type}'"
                    )
        assert not violations, (
            "Invalid threshold operators found:\n" + "\n".join(violations)
        )

    def test_circuit_breaker_uses_gt_not_gte(self) -> None:
        """Regression for Issue #1265: circuit_breaker.yml must use 'gt', not 'gte'.

        'gte' is not a valid Grafana threshold operator and causes DatasourceError.
        """
        docs = _load_alerting_files()
        evs = _extract_threshold_evaluators(docs["circuit_breaker.yml"])
        assert len(evs) == 1, "Expected exactly one threshold evaluator"
        op_type = evs[0]["evaluator"]["type"]
        assert op_type == "gt", (
            f"circuit_breaker evaluator must be 'gt', got '{op_type}'"
        )
        assert op_type != "gte", "Old bug: 'gte' caused DatasourceError (Issue #1265)"

    def test_circuit_breaker_threshold_param_is_zero(self) -> None:
        """Semantic check: gt 0 fires when circuit_breaker_active > 0 (i.e. = 1).

        Old config: gte 1 (invalid operator, same semantics for binary metric).
        New config: gt 0 (valid, semantically equivalent for binary 0/1 metric).
        """
        docs = _load_alerting_files()
        evs = _extract_threshold_evaluators(docs["circuit_breaker.yml"])
        params = evs[0]["evaluator"]["params"]
        assert params == [0], (
            f"Expected threshold param [0] for 'gt' operator, got {params}"
        )

    def test_high_error_rate_uses_valid_operator(self) -> None:
        docs = _load_alerting_files()
        evs = _extract_threshold_evaluators(docs["high_error_rate.yml"])
        assert len(evs) == 1
        assert evs[0]["evaluator"]["type"] in VALID_THRESHOLD_TYPES

    def test_orders_rejected_uses_valid_operator(self) -> None:
        docs = _load_alerting_files()
        evs = _extract_threshold_evaluators(docs["orders_rejected.yml"])
        assert len(evs) == 1
        assert evs[0]["evaluator"]["type"] in VALID_THRESHOLD_TYPES

    def test_valid_threshold_types_constant_is_correct(self) -> None:
        """Document the accepted types from Grafana's provisioning schema."""
        assert VALID_THRESHOLD_TYPES == {"gt", "lt", "within_range", "outside_range"}
        assert "gte" not in VALID_THRESHOLD_TYPES
        assert "lte" not in VALID_THRESHOLD_TYPES


# ---------------------------------------------------------------------------
# Structural validity
# ---------------------------------------------------------------------------


class TestAlertingStructure:
    """Alert rules must have the expected structural shape."""

    def test_circuit_breaker_has_condition_C(self) -> None:
        docs = _load_alerting_files()
        rule = docs["circuit_breaker.yml"]["groups"][0]["rules"][0]
        assert rule["condition"] == "C"

    def test_circuit_breaker_datasource_uid_is_prometheus(self) -> None:
        docs = _load_alerting_files()
        rule = docs["circuit_breaker.yml"]["groups"][0]["rules"][0]
        ref_a = next(d for d in rule["data"] if d["refId"] == "A")
        assert ref_a["datasourceUid"] == "prometheus"

    def test_circuit_breaker_expr_is_correct_metric(self) -> None:
        """The PromQL expression must query circuit_breaker_active."""
        docs = _load_alerting_files()
        rule = docs["circuit_breaker.yml"]["groups"][0]["rules"][0]
        ref_a = next(d for d in rule["data"] if d["refId"] == "A")
        assert ref_a["model"]["expr"] == "circuit_breaker_active"

    def test_circuit_breaker_severity_is_critical(self) -> None:
        docs = _load_alerting_files()
        rule = docs["circuit_breaker.yml"]["groups"][0]["rules"][0]
        assert rule["labels"]["severity"] == "critical"


# ---------------------------------------------------------------------------
# Datasource URL and execErrState tests (Issue #1266 / #1267)
#
# Root cause: execErrState: Error caused Grafana to fire DatasourceError alerts
# (sent as high-severity mails) whenever cdb_prometheus was transiently
# unavailable (e.g. during Docker daemon restart / environment_interruption).
# Docker DNS removes a container's entry while it is stopped, so the window
# between stop and start produces a genuine "no such host" lookup failure.
#
# Fix: execErrState: KeepLast — during a datasource outage, alert rules
# retain their last evaluation state instead of flipping to Error.
#
# Root cause of the first failed attempt (PR #1273, reverted 2026-03-24):
# "KeepLastState" was used — but this string was never a valid Grafana unified
# alerting enum value. The correct string is "KeepLast" (models.KeepLastErrState
# in pkg/services/ngalert/models/alert_rule.go, added in Grafana 10.4/11.0).
# Grafana 11.4.7 accepts "KeepLast" in provisioning YAML without issue.
#
# The datasource URL http://cdb_prometheus:9090 is CORRECT: both cdb_grafana
# and cdb_prometheus are on cdb_network in compose.red.yml. The issue was the
# error-handling policy, not the URL.
# ---------------------------------------------------------------------------


# Valid execErrState values in Grafana unified alerting provisioning YAML.
# Source: pkg/services/ngalert/models/alert_rule.go (Grafana 11.4.7).
# Note: "KeepLastState" is NOT a valid value (legacy string from classic alerting).
VALID_EXEC_ERR_STATES = {"Error", "KeepLast", "Alerting", "OK"}

# Rules that use KeepLast to suppress noisy DatasourceError alerts during
# transient Prometheus restarts (Issue #1266/#1267, fixed 2026-03-26).
KEEP_LAST_STATE_RULES: set[str] = {"cdb-orders-rejected", "cdb_error_rate_high"}


class TestDatasourceUrlAndExecErrState:
    """Regression tests for Issues #1266 / #1267: noisy DatasourceError alerts."""

    # --- Datasource URL ---

    def test_prometheus_datasource_url_uses_container_name(self) -> None:
        """Datasource URL must reference cdb_prometheus (correct Docker service name).

        Both cdb_grafana and cdb_prometheus are on cdb_network in compose.red.yml.
        The URL http://cdb_prometheus:9090 is structurally correct.
        """
        ds_path = (
            pathlib.Path(__file__).resolve().parents[3]
            / "infrastructure"
            / "monitoring"
            / "grafana"
            / "provisioning"
            / "datasources"
            / "prometheus.yml"
        )
        with ds_path.open(encoding="utf-8") as fh:
            ds = yaml.safe_load(fh)
        datasources = ds.get("datasources", [])
        assert len(datasources) == 1, "Expected exactly one datasource"
        url = datasources[0].get("url", "")
        assert "cdb_prometheus" in url, (
            f"Datasource URL must reference cdb_prometheus, got: {url}"
        )
        assert url == "http://cdb_prometheus:9090", (
            f"Unexpected datasource URL: {url}"
        )

    def test_prometheus_datasource_uid_matches_alert_rules(self) -> None:
        """Datasource UID must be 'prometheus' to match datasourceUid in alert rules."""
        ds_path = (
            pathlib.Path(__file__).resolve().parents[3]
            / "infrastructure"
            / "monitoring"
            / "grafana"
            / "provisioning"
            / "datasources"
            / "prometheus.yml"
        )
        with ds_path.open(encoding="utf-8") as fh:
            ds = yaml.safe_load(fh)
        uid = ds["datasources"][0].get("uid")
        assert uid == "prometheus"

        # Every alert rule's ref A must use the same UID
        docs = _load_alerting_files()
        for filename, doc in docs.items():
            for group in doc.get("groups", []):
                for rule in group.get("rules", []):
                    for entry in rule.get("data", []):
                        if entry.get("refId") == "A":
                            assert entry.get("datasourceUid") == uid, (
                                f"{filename}/{rule.get('title')}: "
                                f"datasourceUid must be '{uid}'"
                            )

    # --- execErrState ---

    def test_orders_rejected_exec_err_state_is_keep_last(self) -> None:
        """Issue #1266: orders_rejected must use KeepLast to suppress noisy DatasourceError mails.

        KeepLast retains the last evaluation state when Prometheus is transiently unavailable
        (e.g. Docker DNS removes cdb_prometheus during environment_interruption restart).

        Note: "KeepLastState" (used in PR #1273, reverted) was never a valid unified alerting
        string. The correct value is "KeepLast" — supported in Grafana 11.4.7.
        """
        docs = _load_alerting_files()
        rule = docs["orders_rejected.yml"]["groups"][0]["rules"][0]
        assert rule["execErrState"] == "KeepLast", (
            f"orders_rejected must use KeepLast, got: {rule['execErrState']!r}"
        )

    def test_high_error_rate_exec_err_state_is_keep_last(self) -> None:
        """Issue #1267: high_error_rate must use KeepLast for the same reason as #1266."""
        docs = _load_alerting_files()
        rule = docs["high_error_rate.yml"]["groups"][0]["rules"][0]
        assert rule["execErrState"] == "KeepLast", (
            f"high_error_rate must use KeepLast, got: {rule['execErrState']!r}"
        )

    def test_keep_last_rules_use_keep_last_not_error(self) -> None:
        """Regression guard: KEEP_LAST_STATE_RULES must use KeepLast, not Error.

        Ensures that no future edit silently reverts these rules to the noisy Error state.
        """
        docs = _load_alerting_files()
        for filename, doc in docs.items():
            for group in doc.get("groups", []):
                for rule in group.get("rules", []):
                    if rule.get("uid") in KEEP_LAST_STATE_RULES:
                        assert rule["execErrState"] == "KeepLast", (
                            f"{filename}/{rule.get('title')}: "
                            f"must use KeepLast, got {rule['execErrState']!r}"
                        )

    def test_all_exec_err_states_are_valid(self) -> None:
        """All execErrState values must be in Grafana's allowed set."""
        docs = _load_alerting_files()
        for filename, doc in docs.items():
            for group in doc.get("groups", []):
                for rule in group.get("rules", []):
                    state = rule.get("execErrState")
                    assert state in VALID_EXEC_ERR_STATES, (
                        f"{filename}/{rule.get('title')}: "
                        f"invalid execErrState '{state}'"
                    )

    def test_noisy_error_state_is_fixed(self) -> None:
        """Regression: execErrState=Error on these rules caused DatasourceError spam.

        During environment_interruption restart, Docker DNS removes cdb_prometheus
        while it is stopped. Grafana alert evaluation gets 'no such host'.
        With execErrState=Error, Grafana fires immediately and sends mail.
        With execErrState=KeepLast, the rule retains its previous Normal/OK state.

        Fix applied 2026-03-26: KeepLast (correct unified alerting string).
        First attempt used "KeepLastState" — that string was never valid in unified alerting.
        """
        docs = _load_alerting_files()
        for filename in ("orders_rejected.yml", "high_error_rate.yml"):
            rule = docs[filename]["groups"][0]["rules"][0]
            assert rule["execErrState"] == "KeepLast", (
                f"{filename}: execErrState must be KeepLast (not Error or KeepLastState), "
                f"got {rule['execErrState']!r}"
            )
