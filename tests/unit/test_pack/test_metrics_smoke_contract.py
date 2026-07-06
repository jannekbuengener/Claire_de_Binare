"""Metrics-smoke PASS/WARN/FAIL contract tests (#3878).

Parent #3872. Fixture-based evaluation — no live Prometheus/Grafana in CI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.unit.test_pack._test_pack_contract_helpers import (
    FIXTURES_ROOT,
    METRICS_MATRIX_DOC,
    METRICS_SMOKE_PS1,
    METRICS_SNAPSHOT_SCRIPT,
    VERDICT_VALUES,
    evaluate_chaos_assertions_from_snapshot,
    score_metrics_smoke_report,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_ROOT / name).read_text(encoding="utf-8"))


def test_metrics_snapshot_script_declares_experimental_helper_status() -> None:
    text = METRICS_SNAPSHOT_SCRIPT.read_text(encoding="utf-8")
    assert "experimental" in text.lower()
    assert "DEFAULT_QUERIES" in text
    assert "up_cdb" in text


def test_metrics_smoke_ps1_declares_experimental_and_todo_tracking() -> None:
    text = METRICS_SMOKE_PS1.read_text(encoding="utf-8")
    assert "experimental" in text.lower()
    assert "no-data" in text.lower() or "no data" in text.lower()
    assert "targets_active" in text or "activeTargets" in text


def test_metrics_matrix_doc_exists_for_cross_reference() -> None:
    assert METRICS_MATRIX_DOC.is_file()
    text = METRICS_MATRIX_DOC.read_text(encoding="utf-8")
    assert "prometheus" in text.lower() or "metric" in text.lower()


def test_metrics_smoke_pass_fixture_scores_pass() -> None:
    report = _load_fixture("metrics_smoke_pass.json")
    score = score_metrics_smoke_report(report)
    assert score.verdict == "PASS"
    assert score.prometheus_reachable is True
    assert score.grafana_reachable is True
    assert score.no_data_detected is False


def test_metrics_smoke_no_data_fixture_scores_warn() -> None:
    report = _load_fixture("metrics_smoke_no_data.json")
    score = score_metrics_smoke_report(report)
    assert score.verdict == "WARN"
    assert score.no_data_detected is True
    assert any("no data" in r.lower() or "zero active" in r.lower() for r in score.reasons)


def test_metrics_smoke_fail_fixture_scores_fail() -> None:
    report = _load_fixture("metrics_smoke_fail.json")
    score = score_metrics_smoke_report(report)
    assert score.verdict == "FAIL"
    assert score.prometheus_reachable is False
    assert score.grafana_reachable is False


def test_snapshot_pass_fixture_yields_evaluable_assertions_not_collection_only() -> None:
    snapshot = _load_fixture("metrics_snapshot_pass.json")
    evaluation = evaluate_chaos_assertions_from_snapshot(snapshot)
    assert evaluation.overall_pass is True
    assert evaluation.assertion_count >= 3


def test_snapshot_no_data_fixture_detects_missing_series() -> None:
    snapshot = _load_fixture("metrics_snapshot_no_data.json")
    evaluation = evaluate_chaos_assertions_from_snapshot(snapshot)
    assert evaluation.overall_pass is False
    assert len(evaluation.failed_ids) >= 1


@pytest.mark.parametrize("verdict", sorted(VERDICT_VALUES))
def test_metrics_smoke_verdict_domain_matches_operator_evidence_pack(verdict: str) -> None:
    assert verdict in {"PASS", "WARN", "FAIL"}


def test_contract_module_uses_unit_markers_not_live_monitoring() -> None:
    markers = {mark.name for mark in pytestmark}
    assert markers == {"unit", "contract"}
    assert "e2e" not in markers
    assert "local_only" not in markers
