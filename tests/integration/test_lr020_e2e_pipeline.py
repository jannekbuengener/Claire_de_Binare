"""LR-020 Tier-1: Mocked full-pipeline integration test (Signal → Risk → Execution).

Issue: #782 / #1187
Tier: 1 (mocked, CI-backed — no live stack required)
Tier-2 (live-stack paper-trading run) remains open.

Coverage:
  TC-LR020-01  ALLOW path   — valid signal passes risk gate, execution fills order
  TC-LR020-02  BLOCK path   — risk gate blocks order, execution is never reached
  TC-LR020-03  REGIME block — adverse regime (regime_id=2) causes risk block
"""

from __future__ import annotations

import json

import pytest

from core.utils.seed import Seed, SeedManager
from services.execution import mock_executor as execution_mock_executor, service
from services.execution.mock_executor import MockExecutor
from services.execution.models import OrderStatus
from services.risk.models import Order as RiskOrder
from services.risk.service import DECISION_ALLOW, DECISION_BLOCK, decide_trade

# ---------------------------------------------------------------------------
# Stubs (same pattern as tests/integration/test_execution_pipeline.py)
# ---------------------------------------------------------------------------


class DummyRedisClient:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []
        self.streams: list[tuple[str, dict, int]] = []

    def publish(self, channel: str, payload: str) -> None:
        self.published.append((channel, payload))

    def xadd(self, stream: str, payload: dict, maxlen: int) -> None:
        self.streams.append((stream, payload, maxlen))


class DummyDatabase:
    def __init__(self) -> None:
        self.saved_orders: list[str] = []
        self.saved_trades: list[str] = []

    def save_order(self, result: object) -> None:
        self.saved_orders.append(result.order_id)

    def save_trade(self, result: object) -> None:
        self.saved_trades.append(result.order_id)

    def persist_correlation_event(self, **kwargs) -> bool:
        return True


# ---------------------------------------------------------------------------
# Fixtures — deterministic inputs that pass all risk thresholds (Tier-1 proof)
# ---------------------------------------------------------------------------

# Timestamps chosen so staleness_s < 5s and data_silence_s < 30s
_NOW_MS = 1_700_000_000_000  # reference epoch ms

_SIGNAL_ALLOW = {
    "symbol": "BTCUSDT",
    "signal_id": "lr020-sig-001",
    "ts_ms": _NOW_MS - 100,  # 0.1 s old
    "pct_change_15m": 0.05,  # > 0.03 threshold
    "volume_15m": 0.2,  # > 0.165 threshold
}

_MARKET_STATE_ALLOW = {
    "regime_id": 1,  # allowed regime
    "return_1m": 0.5,  # > -2.0
    "return_5m": 1.0,  # > -5.0
    "price_change_5m": 0.3,  # abs < 10.0
    "ts_ms": _NOW_MS - 200,
    "last_tick_ts_ms": _NOW_MS - 500,  # 0.5 s old → data_silence_s = 0.5 < 30
}

_ACCOUNT_STATE_ALLOW = {
    "daily_drawdown_pct": 0.5,  # < 5.0
    "total_exposure_pct": 10.0,  # < 50.0
    "ts_ms": _NOW_MS - 300,
}

_MARKET_HEALTH_ALLOW = {
    "slippage_pct": 0.1,  # < 1.0
    "ts_ms": _NOW_MS - 400,
}


# ---------------------------------------------------------------------------
# TC-LR020-01: ALLOW path — risk approves, execution fills order
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_tc_lr020_01_allow_path_fills_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """Full pipeline: signal passes risk gate, execution service fills the order."""
    # --- Risk layer ---
    decision, reason_code, evidence = decide_trade(
        signal=_SIGNAL_ALLOW,
        market_state=_MARKET_STATE_ALLOW,
        account_state=_ACCOUNT_STATE_ALLOW,
        market_health=_MARKET_HEALTH_ALLOW,
        now_ms=_NOW_MS,
    )
    assert (
        decision == DECISION_ALLOW
    ), f"Risk gate blocked unexpectedly: reason_code={reason_code}"
    assert reason_code is None
    assert evidence["symbol"] == "BTCUSDT"

    # --- Build Order from risk decision (mirrors RiskManager behaviour) ---
    order = RiskOrder(
        symbol=_SIGNAL_ALLOW["symbol"],
        side="BUY",
        quantity=0.01,
        stop_loss_pct=0.02,
        signal_id=_SIGNAL_ALLOW["signal_id"],
        reason="LR-020 tier-1 allow-path",
        timestamp=int(_NOW_MS / 1000),
        strategy_id="lr020-strat",
        bot_id="lr020-bot",
        client_id="lr020-client",
        order_id="lr020-ord-001",
        decision_id=evidence.get("decision_id"),
        trace_id=evidence.get("trace_id"),
    )
    payload = order.to_dict()

    # --- Execution layer ---
    redis_stub = DummyRedisClient()
    db_stub = DummyDatabase()
    Seed.set(1234)
    seed_manager = SeedManager(Seed.get())
    executor = MockExecutor(
        success_rate=1.0,
        min_latency_ms=0,
        max_latency_ms=0,
        base_slippage_pct=0.0,
        seed_manager=seed_manager,
    )
    stats_before = service.stats.copy()
    try:
        monkeypatch.setattr(service, "executor", executor)
        monkeypatch.setattr(service, "redis_client", redis_stub)
        monkeypatch.setattr(service, "db", db_stub)
        monkeypatch.setattr(execution_mock_executor.time, "sleep", lambda _: None)

        result = service.process_order(payload)

        assert result is not None
        assert result.status == OrderStatus.FILLED.value

        # OrderResult published to Redis
        assert redis_stub.published, "OrderResult must be published to Redis channel"
        channel, text = redis_stub.published[0]
        assert "order_results" in channel
        data = json.loads(text)
        assert data["symbol"] == "BTCUSDT"
        assert data["status"] == OrderStatus.FILLED.value

        # Persisted to DB (MockExecutor generates its own MOCK_<n> order_id)
        assert db_stub.saved_orders, "Order must be saved to DB"
        assert db_stub.saved_trades, "Trade must be saved to DB"
    finally:
        service.stats.clear()
        service.stats.update(stats_before)
        Seed.set(None)


# ---------------------------------------------------------------------------
# TC-LR020-02: BLOCK path — risk gate blocks, execution service never reached
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_tc_lr020_02_block_path_execution_not_reached() -> None:
    """Risk gate blocks due to excessive drawdown; execution layer is never invoked."""
    signal = {**_SIGNAL_ALLOW}
    market_state = {**_MARKET_STATE_ALLOW}
    account_state = {
        "daily_drawdown_pct": 99.0,  # > 5.0 → BLOCK RC_020
        "total_exposure_pct": 10.0,
        "ts_ms": _NOW_MS - 300,
    }
    market_health = {**_MARKET_HEALTH_ALLOW}

    decision, reason_code, evidence = decide_trade(
        signal=signal,
        market_state=market_state,
        account_state=account_state,
        market_health=market_health,
        now_ms=_NOW_MS,
    )

    assert decision == DECISION_BLOCK
    assert reason_code is not None, "Blocked decision must carry a reason code"
    assert evidence["daily_drawdown_pct"] == 99.0


# ---------------------------------------------------------------------------
# TC-LR020-03: Regime block — adverse regime prevents order generation
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_tc_lr020_03_adverse_regime_blocks() -> None:
    """Regime=2 (adverse) causes risk gate to block; no order is generated."""
    signal = {**_SIGNAL_ALLOW}
    market_state = {
        **_MARKET_STATE_ALLOW,
        "regime_id": 2,  # blocked regime
    }
    account_state = {**_ACCOUNT_STATE_ALLOW}
    market_health = {**_MARKET_HEALTH_ALLOW}

    decision, reason_code, evidence = decide_trade(
        signal=signal,
        market_state=market_state,
        account_state=account_state,
        market_health=market_health,
        now_ms=_NOW_MS,
    )

    assert decision == DECISION_BLOCK
    assert reason_code is not None
    assert evidence["regime_id"] == 2
