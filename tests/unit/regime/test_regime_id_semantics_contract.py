"""Regime ID semantics and downstream boundary contract (#3832)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

import services.market.service as market_svc
from services.risk import service as risk_service

from tests.contract.test_decision_contract import _base_inputs

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_unknown_regime_lookup_blocks_decide_trade_rc_001() -> None:
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    market_state.pop("regime_id", None)
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_001"


def test_stale_regime_stream_returns_none_at_lookup_boundary() -> None:
    stale_ts = str(int(time.time()) - 10_000)
    regime_entries = [
        (
            "1-0",
            {
                "ts": stale_ts,
                "symbol": "BTCUSDT",
                "timeframe": "60s",
                "regime": "TREND",
            },
        )
    ]
    mock_redis = MagicMock()

    def xrevrange(stream, start, stop, count=None):
        if stream == market_svc.MARKET_REGIME_STREAM:
            return regime_entries
        return []

    mock_redis.xrevrange.side_effect = xrevrange
    assert market_svc._lookup_regime_id("BTCUSDT", mock_redis) is None


@pytest.mark.parametrize("regime_id", [2, 3])
def test_blocked_regime_ids_fail_closed_at_risk_boundary(regime_id: int) -> None:
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    market_state["regime_id"] = regime_id
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_001"
