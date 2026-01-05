"""Unit tests for the validation gate evaluator."""

from __future__ import annotations

import pytest

from services.validation.gate_evaluator import GateEvaluator, GateThresholds


@pytest.mark.unit
def test_gate_evaluator_pass() -> None:
    evaluator = GateEvaluator(
        thresholds=GateThresholds(
            min_orders=10,
            min_fill_rate=0.4,
            min_qty_sum=1.0,
        )
    )
    result = evaluator.evaluate(
        {
            "orders_total": 25,
            "filled_total": 20,
            "qty_sum": 5.0,
        }
    )

    assert result["overall_pass"] is True
    assert result["risk_assessment"] == "low"


@pytest.mark.unit
def test_gate_evaluator_fail() -> None:
    evaluator = GateEvaluator(
        thresholds=GateThresholds(
            min_orders=5,
            min_fill_rate=0.5,
            min_qty_sum=1.0,
        )
    )
    result = evaluator.evaluate(
        {
            "orders_total": 0,
            "filled_total": 0,
            "qty_sum": 0.0,
        }
    )

    assert result["overall_pass"] is False
    assert result["risk_assessment"] == "high"
