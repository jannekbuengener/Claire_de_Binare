"""Risk decision matrix contract tests (#3834).

Mirrors the canonical decide_trade matrix under tests/unit/risk/.
"""

from __future__ import annotations

import pytest

from services.risk import service as risk_service

from tests.contract.test_decision_contract import _base_inputs

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_decision_allow_baseline() -> None:
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_ALLOW
    assert reason_code is None


@pytest.mark.parametrize(
    ("field", "value", "expected_rc"),
    [
        ("return_1m", -2.0, "RC_002"),
        ("return_5m", -5.0, "RC_002"),
        ("price_change_5m", 10.1, "RC_002"),
    ],
)
def test_decision_rc_002_panic_matrix(field: str, value: float, expected_rc: str) -> None:
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    market_state[field] = value
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == expected_rc


def test_decision_rc_003_stale_matrix() -> None:
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    signal["ts_ms"] = now_ms - 6000
    market_state["ts_ms"] = now_ms - 6000
    account_state["ts_ms"] = now_ms - 6000
    market_health["ts_ms"] = now_ms - 6000
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_003"


def test_decision_rc_004_data_silence_matrix() -> None:
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    market_state["last_tick_ts_ms"] = now_ms - 31000
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_004"


@pytest.mark.parametrize("regime_id", [2, 3])
def test_decision_rc_001_blocked_regimes(regime_id: int) -> None:
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    market_state["regime_id"] = regime_id
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_001"


def test_decision_rc_010_signal_quality() -> None:
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    signal["pct_change_15m"] = 0.05
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_010"


def test_decision_rc_020_drawdown() -> None:
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    account_state["daily_drawdown_pct"] = 5.0
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_020"


def test_decision_rc_021_exposure() -> None:
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    account_state["total_exposure_pct"] = 50.0
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_021"


def test_decision_rc_022_slippage_skip_when_health_missing() -> None:
    now_ms, signal, market_state, account_state, _ = _base_inputs()
    decision, reason_code, evidence = risk_service.decide_trade(
        signal, market_state, account_state, None, now_ms
    )
    assert evidence.get("slippage_pct") is None
    assert reason_code != "RC_022"
