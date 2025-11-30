import math

import pytest

from backoffice.services.adaptive_intensity.dry_wet import (
    ParamBounds,
    ScoreWeights,
    Trade,
    clamp,
    compute_kpis,
    compute_score,
    derive_parameters,
)


def test_compute_kpis_and_score_strong_performance():
    trades = [Trade(pnl=1.0, timestamp=0)] * 180 + [Trade(pnl=-0.2, timestamp=0)] * 120
    winrate, pf, dd, n = compute_kpis(trades)
    assert n == 300
    assert winrate > 0.55
    assert pf > 1.0
    score = compute_score(winrate, pf, dd, ScoreWeights(winrate=0.4, profit_factor=0.4, drawdown=0.2))
    assert 60 <= score <= 100


def test_compute_kpis_and_score_weak_performance():
    trades = [Trade(pnl=-1.0, timestamp=0)] * 200 + [Trade(pnl=0.1, timestamp=0)] * 100
    winrate, pf, dd, n = compute_kpis(trades)
    assert n == 300
    assert winrate < 0.35
    score = compute_score(winrate, pf, dd, ScoreWeights())
    assert 0 <= score <= 40


def test_derive_parameters_monotonic():
    bounds = ParamBounds(
        threshold_min=2.0,
        threshold_max=1.0,
        exposure_min=0.4,
        exposure_max=0.8,
        position_min=0.08,
        position_max=0.12,
    )
    low = derive_parameters(0, bounds)
    high = derive_parameters(100, bounds)
    assert low["signal_threshold_pct"] > high["signal_threshold_pct"]
    assert low["max_exposure_pct"] < high["max_exposure_pct"]
    assert low["max_position_pct"] < high["max_position_pct"]


def test_clamp_bounds():
    assert clamp(-1) == 0
    assert clamp(2) == 1
    assert math.isclose(clamp(0.5), 0.5)
