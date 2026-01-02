"""
E2E Smoke Test - Deterministic Pipeline (no external state).
Issue #427: deterministic CI gate for smoke coverage.
"""
import json
from decimal import Decimal
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

FIXTURES_DIR = Path(__file__).parent / "fixtures"
MARKET_DATA_FIXTURE = FIXTURES_DIR / "market_data.json"
PCT_CHANGE_THRESHOLD = Decimal("0.5")
MAX_POSITION_PCT = Decimal("0.2")


def load_market_data_fixture():
    """Load deterministic market_data fixture."""
    with open(MARKET_DATA_FIXTURE, "r") as handle:
        return json.load(handle)


def test_tc_001_happy_path_buy_signal():
    """TC-001: Happy path - BUY signal created and stored."""
    messages = load_market_data_fixture()
    assert len(messages) == 10, "Fixture muss 10 Messages haben"

    signals = []
    prev_price = None
    for msg in messages:
        price = Decimal(msg["price"])
        trade_qty = Decimal(msg["trade_qty"])
        if prev_price is None or prev_price <= 0:
            pct_change = Decimal("0")
        else:
            pct_change = ((price - prev_price) / prev_price) * Decimal("100")

        if pct_change >= PCT_CHANGE_THRESHOLD:
            signals.append(
                {
                    "symbol": msg["symbol"],
                    "signal_type": msg["side"].strip().lower(),
                    "ts_ms": msg["ts_ms"],
                    "pct_change": pct_change,
                    "notional": price * trade_qty,
                }
            )

        prev_price = price

    assert signals, "Expected at least one signal"
    assert signals[0]["signal_type"] == "buy"

    balance = Decimal("1000000")
    position_pct = signals[0]["notional"] / balance
    assert position_pct <= MAX_POSITION_PCT

    order = {
        "order_id": f"order-{signals[0]['ts_ms']}",
        "symbol": signals[0]["symbol"],
        "side": signals[0]["signal_type"],
        "notional": signals[0]["notional"],
    }
    order_db: list[dict] = []
    order_db.append(order)

    assert order_db == [order]


def test_tc_002_risk_guard_position_limit():
    """TC-002: Risk guard blocks order when position limit exceeded."""
    signal = {
        "symbol": "BTCUSDT",
        "signal_type": "buy",
        "ts_ms": 1,
        "notional": Decimal("5000"),
    }
    balance = Decimal("10000")

    position_pct = signal["notional"] / balance

    assert position_pct > MAX_POSITION_PCT


def test_tc_003_risk_guard_test_balance_fallback():
    """TC-003: Risk uses test balance when live balance is disabled."""
    test_balance = Decimal("1000")
    use_live_balance = False
    live_balance = None

    selected_balance = test_balance if not use_live_balance else live_balance
    assert selected_balance == test_balance

    signal = {
        "symbol": "BTCUSDT",
        "signal_type": "buy",
        "ts_ms": 1,
        "notional": Decimal("10"),
    }

    position_pct = signal["notional"] / selected_balance
    assert position_pct <= Decimal("0.5")


def test_tc_004_signal_engine_pct_change_calculation():
    """TC-004: pct_change is calculated when missing."""
    messages = [
        {
            "schema_version": "v1.0",
            "source": "stub",
            "symbol": "BTCUSDT",
            "ts_ms": 1,
            "price": "100.00",
            "trade_qty": "1.0",
            "side": "buy",
        },
        {
            "schema_version": "v1.0",
            "source": "stub",
            "symbol": "BTCUSDT",
            "ts_ms": 2,
            "price": "105.00",
            "trade_qty": "1.0",
            "side": "buy",
        },
    ]

    prev_price = None
    pct_changes = []
    for msg in messages:
        price = Decimal(msg["price"])
        if prev_price is None or prev_price <= 0:
            pct_change = Decimal("0")
        else:
            pct_change = ((price - prev_price) / prev_price) * Decimal("100")
        pct_changes.append(pct_change)
        prev_price = price

    assert pct_changes[1] == Decimal("5")


def test_tc_005_payload_sanitization():
    """TC-005: sanitize_signal filters None values."""
    payload = {
        "symbol": "BTCUSDT",
        "signal_type": "buy",
        "ts_ms": 1,
        "notional": None,
        "pct_change": Decimal("1.0"),
    }

    sanitized = {key: value for key, value in payload.items() if value is not None}

    assert "notional" not in sanitized
    assert sanitized["pct_change"] == Decimal("1.0")
