"""Regression tests: runtime signal_id collision path (#3970 / #3967)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.contracts.external_adapter_contracts import StrategySignalCandidate
from core.replay.correlation_ledger_insert import CorrelationLedgerInsertResult
from core.utils.uuid_gen import DeterministicUUIDGenerator, generate_uuid_hex

_services_signal = Path(__file__).resolve().parents[3] / "services" / "signal"
if str(_services_signal) not in sys.path:
    sys.path.insert(0, str(_services_signal))

from config import SignalConfig  # noqa: E402
from models import MarketData  # noqa: E402
from service import SignalEngine  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def _donchian_config() -> SignalConfig:
    return SignalConfig(
        strategy_id="donchian_breakout_v1",
        symbol="BTCUSDT",
        min_volume=100.0,
        entry_channel_bars=3,
        exit_channel_bars=2,
        min_minutes_between_entries=0,
        trade_side_mode="long_only",
        bot_id="np-donchian-diag-01",
    )


def _pb1_config() -> SignalConfig:
    return SignalConfig(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        min_volume=100.0,
        entry_lookback_minutes=5,
        exit_lookback_minutes=3,
        breakout_buffer=0.01,
        min_minutes_between_entries=0,
        trade_side_mode="long_only",
        bot_id="np-pb1-diag-01",
    )


def _tick_donchian_buy(engine: SignalEngine, ts: int, price: float) -> object | None:
    for idx, row in enumerate(
        (
            {"price": 100.0, "high": 100.0, "low": 99.0},
            {"price": 101.0, "high": 101.0, "low": 100.0},
            {"price": 102.0, "high": 102.0, "low": 101.0},
        )
    ):
        engine.process_market_data(
            {
                "symbol": "BTCUSDT",
                "timestamp": ts - (2 - idx) * 60_000,
                "price": row["price"],
                "close": row["price"],
                "high": row["high"],
                "low": row["low"],
                "volume": 200_000.0,
                "pct_change": 5.0,
            }
        )
    return engine.process_market_data(
        {
            "symbol": "BTCUSDT",
            "timestamp": ts,
            "price": price,
            "close": price,
            "high": price,
            "low": price - 1,
            "volume": 200_000.0,
            "pct_change": 5.0,
        }
    )


@pytest.mark.unit
def test_donchian_runtime_emission_preserves_strategy_signal_id() -> None:
    with patch("service.config", _donchian_config()):
        engine = SignalEngine()
    with patch(
        "service.format_runtime_signal_id",
        side_effect=lambda length=32: f"sig-{'a' * length}",
    ) as runtime_id:
        signal = _tick_donchian_buy(engine, 1_700_000_000_000, 110.0)
    assert signal is not None
    assert runtime_id.called
    assert signal.signal_id == f"sig-{'a' * 32}"
    assert signal.signal_id != f"sig-{generate_uuid_hex(length=32)}"


@pytest.mark.unit
def test_pb1_runtime_emission_uses_collision_safe_id_not_deterministic_counter() -> None:
    with patch("service.config", _pb1_config()):
        engine = SignalEngine()
    candidate = StrategySignalCandidate(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        side="BUY",
        reason="breakout_entry",
        signal_id="sig-runtime-preserved-pb1",
    )
    market_data = MarketData(
        symbol="BTCUSDT",
        price=50000.0,
        timestamp=1_700_000_000_000,
        pct_change=2.0,
        volume=500_000.0,
    )
    signal = engine._signal_from_candidate(candidate, market_data)
    assert signal.signal_id == "sig-runtime-preserved-pb1"
    deterministic = f"sig-{generate_uuid_hex(length=32)}"
    assert signal.signal_id != deterministic or signal.signal_id.startswith("sig-runtime")


@pytest.mark.unit
def test_restart_simulation_runtime_ids_do_not_reuse_deterministic_counter() -> None:
    gen_restart_a = DeterministicUUIDGenerator(seed=0)
    gen_restart_b = DeterministicUUIDGenerator(seed=0)
    deterministic_restart = f"sig-{gen_restart_a.generate().hex[:32]}"
    assert deterministic_restart == f"sig-{gen_restart_b.generate().hex[:32]}"

    with patch("service.config", _donchian_config()):
        engine_a = SignalEngine()
        engine_b = SignalEngine()
    with patch(
        "service.format_runtime_signal_id",
        side_effect=[f"sig-{'b' * 32}", f"sig-{'c' * 32}"],
    ):
        sig_a = _tick_donchian_buy(engine_a, 1_700_000_100_000, 110.0)
        sig_b = _tick_donchian_buy(engine_b, 1_700_000_200_000, 110.0)
    assert sig_a is not None and sig_b is not None
    assert sig_a.signal_id != sig_b.signal_id
    assert sig_a.signal_id != deterministic_restart


@pytest.mark.unit
def test_persist_correlation_event_reports_conflict_not_success() -> None:
    with patch("service.config", _donchian_config()):
        engine = SignalEngine()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 0
    mock_conn.cursor.return_value = mock_cursor

    from models import Signal

    signal = Signal(
        signal_id="sig-collision-test",
        symbol="BTCUSDT",
        side="BUY",
        reason="test",
        timestamp=1,
        ts_ms=1_700_000_000_000,
        price=1.0,
        strategy_id="donchian_breakout_v1",
        bot_id="np-donchian-diag-01",
    )
    with patch.object(engine, "_get_postgres_conn", return_value=mock_conn):
        result = engine._persist_correlation_event(signal, event_type="SIGNAL")
    assert result == CorrelationLedgerInsertResult.CONFLICT


@pytest.mark.unit
def test_supervisor_false_zero_risk_when_metrics_show_conflicts() -> None:
    from core.replay.correlation_ledger_insert import evaluate_false_zero_event_risk

    risk = evaluate_false_zero_event_risk(
        ledger_lane_count=0,
        insert_conflicts_total=4,
        signals_generated_total=10,
    )
    assert risk["false_zero_event_risk"] is True
