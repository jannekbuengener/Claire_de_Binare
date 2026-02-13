"""Unit tests for Decision Contract 0/1 v1 in risk service."""

import pytest

from services.risk import service as risk_service


def _base_inputs():
    now_ms = 1_700_000_000_000
    signal = {
        "signal_id": "sig-test-0001",  # Required for correlation backbone
        "symbol": "BTCUSDT",
        "pct_change_15m": 3.5,
        "volume_15m": 200000.0,
        "ts_ms": now_ms - 1000,
    }
    market_state = {
        "regime_id": 0,
        "return_1m": -1.0,
        "return_5m": -1.0,
        "price_change_5m": 5.0,
        "last_tick_ts_ms": now_ms - 500,
        "ts_ms": now_ms - 900,
    }
    account_state = {
        "daily_drawdown_pct": 1.0,
        "total_exposure_pct": 10.0,
        "ts_ms": now_ms - 800,
    }
    market_health = {"slippage_pct": 0.5, "ts_ms": now_ms - 700}
    return now_ms, signal, market_state, account_state, market_health


@pytest.mark.contract
def test_decision_allow():
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_ALLOW
    assert reason_code is None


@pytest.mark.contract
def test_decision_rc_002_panic_return_1m():
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    market_state["return_1m"] = -2.0
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_002"


@pytest.mark.contract
def test_decision_rc_002_panic_return_5m():
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    market_state["return_5m"] = -5.0
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_002"


@pytest.mark.contract
def test_decision_rc_002_panic_price_change():
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    market_state["price_change_5m"] = 10.1
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_002"


@pytest.mark.contract
def test_decision_rc_003_stale():
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


@pytest.mark.contract
def test_decision_rc_004_data_silence():
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    market_state["last_tick_ts_ms"] = now_ms - 31000
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_004"


@pytest.mark.contract
def test_decision_rc_001_regime_block():
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    market_state["regime_id"] = 2
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_001"


@pytest.mark.contract
def test_decision_rc_010_signal_thresholds():
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    # Threshold is 0.03 (3% as fraction), so 0.02 (2%) should trigger RC_010
    signal["pct_change_15m"] = 0.02
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_010"


@pytest.mark.contract
def test_decision_rc_020_daily_drawdown():
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    account_state["daily_drawdown_pct"] = 5.0
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_020"


@pytest.mark.contract
def test_decision_rc_021_exposure():
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    account_state["total_exposure_pct"] = 50.0
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_021"


@pytest.mark.contract
def test_decision_rc_022_slippage():
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    market_health["slippage_pct"] = 1.1
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_022"


@pytest.mark.contract
def test_decision_determinism():
    """Test that same inputs produce deterministic outputs (except for correlation IDs which are UUIDs)."""
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    first = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    second = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    # Decision and reason_code must be identical
    assert first[0] == second[0]
    assert first[1] == second[1]
    # Evidence must be identical except for correlation IDs (decision_id, trace_id)
    first_evidence = {
        k: v for k, v in first[2].items() if k not in ("decision_id", "trace_id")
    }
    second_evidence = {
        k: v for k, v in second[2].items() if k not in ("decision_id", "trace_id")
    }
    assert first_evidence == second_evidence
    # Correlation IDs must exist and be valid UUIDs
    assert first[2].get("decision_id") is not None
    assert first[2].get("trace_id") is not None
    assert second[2].get("decision_id") is not None
    assert second[2].get("trace_id") is not None


@pytest.mark.contract
def test_decision_first_fail_panic_wins():
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    market_state["return_1m"] = -2.0
    market_state["last_tick_ts_ms"] = now_ms - 31000
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_002"


@pytest.mark.contract
def test_decision_first_fail_stale_wins_over_regime():
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    market_state["regime_id"] = 2
    signal["ts_ms"] = now_ms - 6000
    market_state["ts_ms"] = now_ms - 6000
    account_state["ts_ms"] = now_ms - 6000
    market_health["ts_ms"] = now_ms - 6000
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_003"


@pytest.mark.contract
def test_decision_first_fail_regime_wins_over_signal():
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    market_state["regime_id"] = 2
    signal["pct_change_15m"] = 0.1
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_001"


@pytest.mark.contract
def test_decision_first_fail_drawdown_wins_over_exposure():
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    account_state["daily_drawdown_pct"] = 5.0
    account_state["total_exposure_pct"] = 50.0
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_020"
