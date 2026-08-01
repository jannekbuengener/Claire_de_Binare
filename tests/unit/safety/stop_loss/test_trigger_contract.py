"""Stop-loss price trigger contract tests (Issue #4186).

Protected rule: a protective trigger must be unambiguous and fail-closed. Any
unknown, invalid, or stale input must BLOCK, never silently report "no trigger".
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from core.safety.stop_loss import (
    STOP_LOSS_TRIGGER_CONTRACT_VERSION,
    PositionSide,
    PositionSnapshot,
    PriceObservation,
    StopLossContractError,
    StopLossReason,
    StopLossTriggerConfig,
    StopLossTriggerDecision,
    compute_stop_price,
    evaluate_stop_loss_trigger,
)
from core.safety.stop_loss.contracts import to_protection_decimal

from tests.unit.safety.stop_loss.conftest import observation


@pytest.mark.unit
def test_contract_version_is_explicit_and_versioned():
    assert STOP_LOSS_TRIGGER_CONTRACT_VERSION == "cdb-stop-loss-trigger/v1"


@pytest.mark.unit
def test_long_stop_price_is_below_entry(long_position, config):
    stop_price = compute_stop_price(
        side=PositionSide.LONG,
        entry_price=Decimal("100.00"),
        stop_loss_pct=Decimal("0.02"),
    )
    assert stop_price == Decimal("98.00000000")
    assert stop_price < Decimal("100.00")


@pytest.mark.unit
def test_short_stop_price_is_above_entry():
    stop_price = compute_stop_price(
        side=PositionSide.SHORT,
        entry_price=Decimal("100.00"),
        stop_loss_pct=Decimal("0.02"),
    )
    assert stop_price == Decimal("102.00000000")


@pytest.mark.unit
def test_stop_price_undefined_for_non_directional_side():
    with pytest.raises(StopLossContractError):
        compute_stop_price(
            side=PositionSide.FLAT,
            entry_price=Decimal("100"),
            stop_loss_pct=Decimal("0.02"),
        )


@pytest.mark.unit
def test_long_breach_triggers_with_event(
    long_position, config, breach_observation, now_ms
):
    result = evaluate_stop_loss_trigger(
        long_position, breach_observation, config, now_ms=now_ms
    )

    assert result.decision is StopLossTriggerDecision.TRIGGERED
    assert result.reason_code == StopLossReason.TRIGGERED.value
    assert result.event is not None
    assert result.event.event_id.startswith("slp-")
    assert result.event.stop_price == Decimal("98.00000000")
    assert result.event.position_side is PositionSide.LONG
    assert result.event.contract_version == STOP_LOSS_TRIGGER_CONTRACT_VERSION


@pytest.mark.unit
def test_long_price_exactly_at_stop_triggers(long_position, config, now_ms):
    result = evaluate_stop_loss_trigger(
        long_position, observation("98.00"), config, now_ms=now_ms
    )
    assert result.triggered is True


@pytest.mark.unit
def test_price_within_stop_does_not_trigger(
    long_position, config, safe_observation, now_ms
):
    result = evaluate_stop_loss_trigger(
        long_position, safe_observation, config, now_ms=now_ms
    )

    assert result.decision is StopLossTriggerDecision.NO_TRIGGER
    assert result.reason_code == StopLossReason.NO_TRIGGER_PRICE_ABOVE_STOP.value
    assert result.event is None


@pytest.mark.unit
def test_short_breach_triggers(short_position, config, now_ms):
    result = evaluate_stop_loss_trigger(
        short_position, observation("102.50"), config, now_ms=now_ms
    )
    assert result.triggered is True
    assert result.event.position_side is PositionSide.SHORT


@pytest.mark.unit
def test_short_price_below_stop_does_not_trigger(short_position, config, now_ms):
    result = evaluate_stop_loss_trigger(
        short_position, observation("101.00"), config, now_ms=now_ms
    )
    assert result.decision is StopLossTriggerDecision.NO_TRIGGER


@pytest.mark.unit
def test_flat_position_is_no_trigger_not_block(long_position, config, now_ms):
    flat = replace(long_position, side=PositionSide.FLAT)
    result = evaluate_stop_loss_trigger(
        flat, observation("1.00"), config, now_ms=now_ms
    )

    assert result.decision is StopLossTriggerDecision.NO_TRIGGER
    assert result.reason_code == StopLossReason.NO_OPEN_POSITION.value


@pytest.mark.unit
@pytest.mark.parametrize(
    ("mutation", "expected_reason"),
    [
        ({"side": PositionSide.UNKNOWN}, StopLossReason.POSITION_STATE_UNKNOWN),
        ({"quantity": None}, StopLossReason.POSITION_QUANTITY_UNKNOWN),
        ({"quantity": Decimal("0")}, StopLossReason.POSITION_QUANTITY_UNKNOWN),
        ({"quantity": 0.5}, StopLossReason.POSITION_QUANTITY_UNKNOWN),
        ({"entry_price": None}, StopLossReason.ENTRY_PRICE_UNKNOWN),
        ({"entry_price": Decimal("0")}, StopLossReason.ENTRY_PRICE_UNKNOWN),
        ({"entry_price": 100.0}, StopLossReason.ENTRY_PRICE_UNKNOWN),
        ({"position_id": None}, StopLossReason.POSITION_IDENTITY_UNKNOWN),
        ({"position_id": "   "}, StopLossReason.POSITION_IDENTITY_UNKNOWN),
    ],
)
def test_unknown_position_state_blocks(
    long_position, config, breach_observation, now_ms, mutation, expected_reason
):
    position = replace(long_position, **mutation)
    result = evaluate_stop_loss_trigger(
        position, breach_observation, config, now_ms=now_ms
    )

    assert result.decision is StopLossTriggerDecision.BLOCKED
    assert result.reason_code == expected_reason.value
    assert result.event is None


@pytest.mark.unit
@pytest.mark.parametrize(
    ("price", "expected_reason"),
    [
        (None, StopLossReason.PRICE_INVALID),
        (97.5, StopLossReason.PRICE_INVALID),
        (Decimal("0"), StopLossReason.PRICE_INVALID),
        (Decimal("-1"), StopLossReason.PRICE_INVALID),
        ("not-a-price", StopLossReason.PRICE_INVALID),
    ],
)
def test_invalid_price_blocks(long_position, config, now_ms, price, expected_reason):
    obs = PriceObservation(
        symbol="BTCUSDT", price=price, observed_at_ms=now_ms - 1_000, source="test"
    )
    result = evaluate_stop_loss_trigger(long_position, obs, config, now_ms=now_ms)

    assert result.blocked is True
    assert result.reason_code == expected_reason.value


@pytest.mark.unit
@pytest.mark.parametrize(
    "observed_at_ms",
    [None, "1800000000000", 1_800_000_000_001, 1_800_000_000_000 - 120_001],
)
def test_stale_or_future_price_blocks(long_position, config, now_ms, observed_at_ms):
    obs = PriceObservation(
        symbol="BTCUSDT",
        price=Decimal("97.50"),
        observed_at_ms=observed_at_ms,
        source="test",
    )
    result = evaluate_stop_loss_trigger(long_position, obs, config, now_ms=now_ms)

    assert result.blocked is True
    assert result.reason_code == StopLossReason.PRICE_STALE.value


@pytest.mark.unit
def test_symbol_mismatch_blocks(long_position, config, now_ms):
    result = evaluate_stop_loss_trigger(
        long_position, observation("97.50", symbol="ETHUSDT"), config, now_ms=now_ms
    )

    assert result.blocked is True
    assert result.reason_code == StopLossReason.SYMBOL_MISMATCH.value


@pytest.mark.unit
@pytest.mark.parametrize(
    "stop_loss_pct", [None, 0.02, Decimal("0"), Decimal("1"), Decimal("-0.02"), "abc"]
)
def test_invalid_stop_loss_pct_blocks(
    long_position, breach_observation, now_ms, stop_loss_pct
):
    result = evaluate_stop_loss_trigger(
        long_position,
        breach_observation,
        StopLossTriggerConfig(stop_loss_pct=stop_loss_pct),
        now_ms=now_ms,
    )

    assert result.blocked is True
    assert result.reason_code == StopLossReason.CONFIG_INVALID.value


@pytest.mark.unit
@pytest.mark.parametrize("max_price_age_ms", [0, -1, None, "120000"])
def test_invalid_price_age_config_blocks(
    long_position, breach_observation, now_ms, max_price_age_ms
):
    result = evaluate_stop_loss_trigger(
        long_position,
        breach_observation,
        StopLossTriggerConfig(
            stop_loss_pct=Decimal("0.02"), max_price_age_ms=max_price_age_ms
        ),
        now_ms=now_ms,
    )

    assert result.blocked is True
    assert result.reason_code == StopLossReason.CONFIG_INVALID.value


@pytest.mark.unit
def test_float_is_rejected_on_the_protection_path():
    with pytest.raises(StopLossContractError, match="must not be float"):
        to_protection_decimal(1.5, field="price")


@pytest.mark.unit
def test_bool_and_none_are_rejected_on_the_protection_path():
    with pytest.raises(StopLossContractError, match="must not be bool"):
        to_protection_decimal(True, field="price")
    with pytest.raises(StopLossContractError, match="must not be None"):
        to_protection_decimal(None, field="price")


@pytest.mark.unit
def test_decimal_string_price_is_accepted(long_position, config, now_ms):
    obs = PriceObservation(
        symbol="BTCUSDT", price="97.50", observed_at_ms=now_ms - 1, source="candles"
    )
    result = evaluate_stop_loss_trigger(long_position, obs, config, now_ms=now_ms)

    assert result.triggered is True
    assert result.event.observed_price == Decimal("97.50000000")


@pytest.mark.unit
def test_non_position_side_type_blocks(
    long_position, config, breach_observation, now_ms
):
    broken = PositionSnapshot(
        symbol=long_position.symbol,
        side="LONG",  # raw string is not an accepted protection-side type
        quantity=long_position.quantity,
        entry_price=long_position.entry_price,
        position_id=long_position.position_id,
    )
    result = evaluate_stop_loss_trigger(
        broken, breach_observation, config, now_ms=now_ms
    )

    assert result.blocked is True
    assert result.reason_code == StopLossReason.POSITION_STATE_UNKNOWN.value
