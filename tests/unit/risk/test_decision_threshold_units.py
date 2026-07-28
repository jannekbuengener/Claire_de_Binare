"""Decision threshold unit conversion from RiskConfig (Issue #4152 / S4)."""

from __future__ import annotations

import pytest

from services.risk.config import RiskConfig
from services.risk.service import (
    build_decision_thresholds,
    risk_config_fraction_to_decision_pct_points,
)


@pytest.mark.unit
def test_fraction_to_percentage_points_conversion():
    assert risk_config_fraction_to_decision_pct_points(0.30) == 30.0
    assert risk_config_fraction_to_decision_pct_points(0.05) == 5.0
    assert risk_config_fraction_to_decision_pct_points(0.10) == 10.0


@pytest.mark.unit
def test_decision_thresholds_derived_from_risk_config_not_hardcoded_50():
    cfg = RiskConfig(max_total_exposure_pct=0.30, max_daily_drawdown_pct=0.05)
    thresholds = build_decision_thresholds(cfg)
    assert thresholds["total_exposure_pct_max"] == 30.0
    assert thresholds["daily_drawdown_pct_max"] == 5.0
    # Must not retain the former conflicting hardcode of 50.0 percentage points.
    assert thresholds["total_exposure_pct_max"] != 50.0


@pytest.mark.unit
def test_decision_thresholds_harden_when_config_is_tighter():
    cfg = RiskConfig(max_total_exposure_pct=0.20, max_daily_drawdown_pct=0.03)
    thresholds = build_decision_thresholds(cfg)
    assert thresholds["total_exposure_pct_max"] == 20.0
    assert thresholds["daily_drawdown_pct_max"] == 3.0
