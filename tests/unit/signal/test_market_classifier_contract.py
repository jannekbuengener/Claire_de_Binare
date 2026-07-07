"""Market classifier contract tests (#3832)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.signal.market_classifier import MarketClassifier, MarketPhase

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def _seed_prices(classifier: MarketClassifier, *, count: int, start: float = 100.0) -> None:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(count):
        classifier.add_price_data(base + timedelta(minutes=i), start + i * 0.1)


def test_classify_returns_unknown_before_min_data_points() -> None:
    classifier = MarketClassifier(min_data_points=20)
    _seed_prices(classifier, count=5)
    metrics = classifier.classify_current_market()
    assert metrics.phase == MarketPhase.UNKNOWN
    assert metrics.confidence == 0.0


def test_should_trade_fail_closed_on_unknown_phase() -> None:
    classifier = MarketClassifier(min_data_points=20)
    recommendation = classifier.should_trade_in_current_conditions()
    assert recommendation["should_trade"] is False
    assert recommendation["current_phase"] == MarketPhase.UNKNOWN.value
    assert recommendation["risk_level"] == "high"


def test_should_trade_blocks_volatile_when_avoid_volatile_markets() -> None:
    classifier = MarketClassifier(
        volatility_threshold=0.001,
        min_data_points=20,
        lookback_periods={"medium": 20},
    )
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    price = 100.0
    for i in range(25):
        swing = 5.0 if i % 2 == 0 else -5.0
        classifier.add_price_data(base + timedelta(minutes=i), price + swing)
    recommendation = classifier.should_trade_in_current_conditions(
        min_confidence=0.0,
        avoid_volatile_markets=True,
    )
    assert recommendation["should_trade"] is False
    assert "Volatile" in recommendation["reason"] or recommendation["current_phase"] == "volatile"


def test_should_trade_requires_min_confidence() -> None:
    classifier = MarketClassifier(min_data_points=20)
    _seed_prices(classifier, count=25, start=100.0)
    recommendation = classifier.should_trade_in_current_conditions(min_confidence=0.99)
    assert recommendation["should_trade"] is False
    assert "confidence" in recommendation["reason"].lower()
