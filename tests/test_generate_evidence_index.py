"""Tests for generate_evidence_index.py — evidence indexing for shadow-soak runs."""

import json
import sys
from pathlib import Path

import pytest

# Make infrastructure/scripts importable
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "infrastructure" / "scripts")
)

from generate_evidence_index import (
    detect_fetch_failure,
    generate_index,
    parse_prometheus_metric,
    scan_fetch_failures,
)

# ---------------------------------------------------------------------------
# Fixtures — minimal valid evidence directory
# ---------------------------------------------------------------------------

EXEC_METRICS = """\
# HELP execution_orders_received_total Anzahl eingegangener Orders
# TYPE execution_orders_received_total counter
execution_orders_received_total 0
# HELP execution_orders_filled_total Anzahl erfolgreich ausgefuehrter Orders
# TYPE execution_orders_filled_total counter
execution_orders_filled_total 0
# HELP execution_orders_rejected_total Anzahl abgelehnter Orders
# TYPE execution_orders_rejected_total counter
execution_orders_rejected_total 0
# HELP execution_invalid_payloads_total Anzahl invalid/malformed Payloads
# TYPE execution_invalid_payloads_total counter
execution_invalid_payloads_total 0
# HELP execution_shadow_blocked_total Orders blocked by shadow mode gate (LR-030)
# TYPE execution_shadow_blocked_total counter
execution_shadow_blocked_total 0
# HELP execution_uptime_seconds Service Laufzeit in Sekunden
# TYPE execution_uptime_seconds gauge
execution_uptime_seconds 1832.601103
"""

RISK_METRICS = """\
# HELP signals_received_total Signals empfangen (Redis PubSub)
# TYPE signals_received_total counter
signals_received_total 137
# HELP orders_approved_total Orders freigegeben
# TYPE orders_approved_total counter
orders_approved_total 0
# HELP orders_blocked_total Orders blockiert (Risk Checks)
# TYPE orders_blocked_total counter
orders_blocked_total 137
# HELP orders_skipped_total Orders uebersprungen
# TYPE orders_skipped_total counter
orders_skipped_total 0
# HELP risk_total_exposure_value Gesamtposition (Notional)
# TYPE risk_total_exposure_value gauge
risk_total_exposure_value 0.0
"""

RUN_SUMMARY = {
    "run_id": "12345",
    "run_url": "https://github.com/owner/repo/actions/runs/12345",
    "ref": "refs/heads/main",
    "commit": "abc123",
    "status": "success",
    "gate_status": "PASS",
    "mode": "full",
    "soak_minutes": 30,
    "ended_at": "2026-03-09T12:00:00Z",
}

EXEC_STATUS = {
    "mode": "mock",
    "service": "execution_service",
    "stats": {"shadow_blocked": 0, "orders_filled": 0},
}

RISK_STATUS = {
    "signals_received": 137,
    "orders_approved": 0,
    "orders_blocked": 137,
    "risk_state": {"total_exposure": 0.0, "circuit_breaker": False},
    "status": "running",
}


def _create_evidence_dir(tmp_path: Path, **overrides) -> Path:
    """Create a minimal valid evidence directory. Overrides allow omitting files."""
    edir = tmp_path / "evidence"
    edir.mkdir()
    endpoints = edir / "endpoints"
    endpoints.mkdir()

    if overrides.get("skip_run_summary") is not True:
        (edir / "run_summary.json").write_text(
            json.dumps(overrides.get("run_summary", RUN_SUMMARY)),
            encoding="utf-8",
        )

    if overrides.get("skip_exec_metrics") is not True:
        (endpoints / "execution_metrics.txt").write_text(
            overrides.get("exec_metrics", EXEC_METRICS),
            encoding="utf-8",
        )

    if overrides.get("skip_risk_metrics") is not True:
        (endpoints / "risk_metrics.txt").write_text(
            overrides.get("risk_metrics", RISK_METRICS),
            encoding="utf-8",
        )

    if overrides.get("include_exec_status"):
        (endpoints / "execution_status.json").write_text(
            json.dumps(overrides.get("exec_status", EXEC_STATUS)),
            encoding="utf-8",
        )

    if overrides.get("include_risk_status"):
        (endpoints / "risk_status.json").write_text(
            json.dumps(overrides.get("risk_status", RISK_STATUS)),
            encoding="utf-8",
        )

    if overrides.get("extra_files"):
        for name, content in overrides["extra_files"].items():
            (endpoints / name).write_text(content, encoding="utf-8")

    return edir


# ---------------------------------------------------------------------------
# Unit tests: parse_prometheus_metric
# ---------------------------------------------------------------------------


class TestParsePrometheusMetric:
    def test_existing_metric(self):
        assert (
            parse_prometheus_metric(EXEC_METRICS, "execution_orders_filled_total")
            == 0.0
        )

    def test_counter_with_value(self):
        assert parse_prometheus_metric(RISK_METRICS, "signals_received_total") == 137.0

    def test_gauge(self):
        assert parse_prometheus_metric(RISK_METRICS, "risk_total_exposure_value") == 0.0

    def test_missing_metric(self):
        assert parse_prometheus_metric(EXEC_METRICS, "nonexistent_metric") is None

    def test_empty_text(self):
        assert parse_prometheus_metric("", "any_metric") is None

    def test_comment_only(self):
        assert parse_prometheus_metric("# just a comment\n", "any") is None


# ---------------------------------------------------------------------------
# Unit tests: detect_fetch_failure
# ---------------------------------------------------------------------------


class TestDetectFetchFailure:
    def test_no_failure(self):
        assert detect_fetch_failure("some normal content") is None

    def test_failure_present(self):
        text = "EVIDENCE-FETCH-FAILED: execution_metrics (http://...) curl_exit=7"
        assert detect_fetch_failure(text) is not None
        assert "curl_exit=7" in detect_fetch_failure(text)


# ---------------------------------------------------------------------------
# Integration tests: generate_index
# ---------------------------------------------------------------------------


class TestGenerateIndexHappyPath:
    def test_minimal_required_sources(self, tmp_path):
        """Only required sources present — should produce valid index."""
        edir = _create_evidence_dir(tmp_path)
        index = generate_index(edir)

        assert index["schema_version"] == "1.0"
        assert index["run_id"] == "12345"
        assert index["commit"] == "abc123"
        assert index["mode"] == "full"
        assert index["soak_minutes"] == 30
        assert index["gate_status"] == "PASS"

        # Derived from metrics
        assert index["has_live_data"] is True
        assert index["zero_execution"] is True
        assert index["zero_exposure"] is True
        assert index["risk_blocked_all"] is True
        assert index["shadow_blocked_total"] == 0
        assert index["signals_received"] == 137
        assert index["orders_blocked"] == 137
        assert index["orders_approved"] == 0
        assert index["orders_filled"] == 0
        assert index["total_exposure"] == 0.0

        # Optional fields should be None without enrichment sources
        assert index["trading_mode"] is None
        assert index["kill_switch_active"] is None
        assert index["prometheus_targets_up"] is None

        # No fetch failures
        assert index["fetch_failures"] == []

        # Source integrity
        assert index["source_integrity"]["run_summary.json"] == "ok"
        assert index["source_integrity"]["endpoints/execution_metrics.txt"] == "ok"
        assert index["source_integrity"]["endpoints/risk_metrics.txt"] == "ok"
        assert index["source_integrity"]["endpoints/execution_status.json"] == "missing"
        assert index["source_integrity"]["endpoints/risk_status.json"] == "missing"

    def test_with_all_enrichment_sources(self, tmp_path):
        """All sources present — optional fields should be populated."""
        edir = _create_evidence_dir(
            tmp_path,
            include_exec_status=True,
            include_risk_status=True,
        )
        index = generate_index(edir)

        assert index["trading_mode"] == "mock"
        assert index["kill_switch_active"] is False
        assert index["source_integrity"]["endpoints/execution_status.json"] == "ok"
        assert index["source_integrity"]["endpoints/risk_status.json"] == "ok"


class TestGenerateIndexMissingRequired:
    def test_missing_run_summary(self, tmp_path):
        edir = _create_evidence_dir(tmp_path, skip_run_summary=True)
        with pytest.raises(SystemExit) as exc_info:
            generate_index(edir)
        assert exc_info.value.code == 1

    def test_missing_execution_metrics(self, tmp_path):
        edir = _create_evidence_dir(tmp_path, skip_exec_metrics=True)
        with pytest.raises(SystemExit) as exc_info:
            generate_index(edir)
        assert exc_info.value.code == 1

    def test_missing_risk_metrics(self, tmp_path):
        edir = _create_evidence_dir(tmp_path, skip_risk_metrics=True)
        with pytest.raises(SystemExit) as exc_info:
            generate_index(edir)
        assert exc_info.value.code == 1

    def test_fetch_failed_execution_metrics(self, tmp_path):
        """Required source with fetch-failure marker → exit 1."""
        edir = _create_evidence_dir(
            tmp_path,
            exec_metrics="EVIDENCE-FETCH-FAILED: execution_metrics curl_exit=7",
        )
        with pytest.raises(SystemExit) as exc_info:
            generate_index(edir)
        assert exc_info.value.code == 1


class TestGenerateIndexFetchFailures:
    def test_fetch_failure_in_optional_file(self, tmp_path):
        """Fetch failure in an optional endpoint file is recorded but not fatal."""
        edir = _create_evidence_dir(
            tmp_path,
            extra_files={
                "grafana_health.json": "EVIDENCE-FETCH-FAILED: grafana_health curl_exit=28",
            },
        )
        index = generate_index(edir)
        assert len(index["fetch_failures"]) == 1
        assert "grafana_health.json" in index["fetch_failures"][0]

    def test_multiple_fetch_failures(self, tmp_path):
        edir = _create_evidence_dir(
            tmp_path,
            extra_files={
                "grafana_health.json": "EVIDENCE-FETCH-FAILED: grafana curl_exit=28",
                "ws_health.json": "EVIDENCE-FETCH-FAILED: ws curl_exit=7",
            },
        )
        index = generate_index(edir)
        assert len(index["fetch_failures"]) == 2


class TestGenerateIndexEdgeCases:
    def test_zero_signals(self, tmp_path):
        """No signals received → has_live_data=False, risk_blocked_all=False."""
        risk_zero = RISK_METRICS.replace(
            "signals_received_total 137", "signals_received_total 0"
        ).replace("orders_blocked_total 137", "orders_blocked_total 0")
        edir = _create_evidence_dir(tmp_path, risk_metrics=risk_zero)
        index = generate_index(edir)

        assert index["has_live_data"] is False
        assert index["risk_blocked_all"] is False
        assert index["zero_execution"] is True
        assert index["zero_exposure"] is True

    def test_orders_approved_nonzero(self, tmp_path):
        """Some orders approved → risk_blocked_all=False."""
        risk_approved = RISK_METRICS.replace(
            "orders_approved_total 0", "orders_approved_total 5"
        )
        edir = _create_evidence_dir(tmp_path, risk_metrics=risk_approved)
        index = generate_index(edir)

        assert index["risk_blocked_all"] is False
        assert index["orders_approved"] == 5

    def test_orders_filled_nonzero(self, tmp_path):
        """Orders filled → zero_execution=False."""
        exec_filled = EXEC_METRICS.replace(
            "execution_orders_filled_total 0", "execution_orders_filled_total 3"
        )
        edir = _create_evidence_dir(tmp_path, exec_metrics=exec_filled)
        index = generate_index(edir)

        assert index["zero_execution"] is False
        assert index["orders_filled"] == 3

    def test_nonzero_exposure(self, tmp_path):
        """Nonzero exposure → zero_exposure=False."""
        risk_exposure = RISK_METRICS.replace(
            "risk_total_exposure_value 0.0", "risk_total_exposure_value 1500.50"
        )
        edir = _create_evidence_dir(tmp_path, risk_metrics=risk_exposure)
        index = generate_index(edir)

        assert index["zero_exposure"] is False
        assert index["total_exposure"] == 1500.50

    def test_fetch_failed_optional_status_still_produces_index(self, tmp_path):
        """Optional status file with fetch failure → index still generated, field is null."""
        edir = _create_evidence_dir(
            tmp_path,
            include_exec_status=True,
        )
        # Overwrite with fetch failure
        (edir / "endpoints" / "execution_status.json").write_text(
            "EVIDENCE-FETCH-FAILED: execution_status curl_exit=7"
        )
        index = generate_index(edir)
        assert index["trading_mode"] is None
        assert (
            index["source_integrity"]["endpoints/execution_status.json"]
            == "fetch_failed"
        )
        assert any("execution_status" in f for f in index["fetch_failures"])

    def test_kill_switch_active_from_risk_status(self, tmp_path):
        """risk_status with circuit_breaker=True → kill_switch_active is True."""
        risk_active = {
            **RISK_STATUS,
            "risk_state": {**RISK_STATUS["risk_state"], "circuit_breaker": True},
        }
        edir = _create_evidence_dir(
            tmp_path, include_risk_status=True, risk_status=risk_active
        )
        index = generate_index(edir)
        assert index["kill_switch_active"] is True

    def test_kill_switch_none_when_key_absent(self, tmp_path):
        """risk_status without circuit_breaker key → kill_switch_active is None."""
        risk_no_cb = {
            **RISK_STATUS,
            "risk_state": {"total_exposure": 0.0},
        }
        edir = _create_evidence_dir(
            tmp_path, include_risk_status=True, risk_status=risk_no_cb
        )
        index = generate_index(edir)
        assert index["kill_switch_active"] is None
