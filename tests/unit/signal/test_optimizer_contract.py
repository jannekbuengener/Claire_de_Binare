"""Optimizer contract tests (#3833).

ParameterOptimizer is currently a stub — tests fix the expected contract shape.
"""

from __future__ import annotations

import pytest

from services.signal.optimizer import ParameterOptimizer

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_optimizer_returns_deterministic_result_shape() -> None:
    optimizer = ParameterOptimizer()
    first = optimizer.optimize_parameters()
    second = optimizer.optimize_parameters()
    assert first == second
    assert first["optimized"] is True
    assert first["win_rate"] >= optimizer.min_win_rate


def test_optimizer_min_win_rate_boundary_is_fail_closed_default() -> None:
    optimizer = ParameterOptimizer()
    result = optimizer.optimize_parameters()
    assert result["win_rate"] >= 0.5
