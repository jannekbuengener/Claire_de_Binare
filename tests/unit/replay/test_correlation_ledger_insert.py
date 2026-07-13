"""Unit tests for correlation ledger insert classification (#3970)."""

from __future__ import annotations

import pytest

from core.replay.correlation_ledger_insert import (
    CorrelationLedgerInsertResult,
    classify_insert_rowcount,
    evaluate_false_zero_event_risk,
    parse_prometheus_counter,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_classify_insert_rowcount_inserted() -> None:
    assert classify_insert_rowcount(1) == CorrelationLedgerInsertResult.INSERTED


def test_classify_insert_rowcount_conflict_on_zero() -> None:
    assert classify_insert_rowcount(0) == CorrelationLedgerInsertResult.CONFLICT


def test_evaluate_false_zero_event_risk_when_conflicts_without_ledger_rows() -> None:
    result = evaluate_false_zero_event_risk(
        ledger_lane_count=0,
        insert_conflicts_total=3,
        signals_generated_total=10,
    )
    assert result["false_zero_event_risk"] is True
    assert result["interpretation"] == "ledger_insert_conflict_or_signal_without_ledger_row"


def test_evaluate_false_zero_event_risk_clear_when_ledger_has_rows() -> None:
    result = evaluate_false_zero_event_risk(
        ledger_lane_count=5,
        insert_conflicts_total=0,
        signals_generated_total=5,
    )
    assert result["false_zero_event_risk"] is False


def test_parse_prometheus_counter_sums_labeled_series() -> None:
    body = (
        "# HELP correlation_ledger_insert_conflicts_total conflicts\n"
        "# TYPE correlation_ledger_insert_conflicts_total counter\n"
        'correlation_ledger_insert_conflicts_total{error_type="ledger_insert_conflict"} 2\n'
        "correlation_ledger_insert_conflicts_total 5\n"
    )
    assert parse_prometheus_counter(body, "correlation_ledger_insert_conflicts_total") == 7
