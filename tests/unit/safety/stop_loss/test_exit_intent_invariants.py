"""Exit intent invariant tests (Issue #4186).

Protected rule: a protective exit intent may only reduce a position. It must
never increase exposure, flip the side, or reach a productive adapter.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from core.safety.stop_loss import (
    EXIT_INTENT_SCHEMA_VERSION,
    DisabledProductiveExitAdapter,
    ExitIntentSink,
    PositionSide,
    RecordingExitIntentSink,
    StopLossContractError,
    StopLossReason,
    build_exit_intent_v1,
    evaluate_stop_loss_trigger,
)

from tests.unit.safety.stop_loss.conftest import NOW_MS, observation


@pytest.fixture
def long_event(long_position, config, breach_observation, now_ms):
    result = evaluate_stop_loss_trigger(
        long_position, breach_observation, config, now_ms=now_ms
    )
    assert result.triggered
    return result.event


@pytest.fixture
def short_event(short_position, config, now_ms):
    result = evaluate_stop_loss_trigger(
        short_position, observation("102.50"), config, now_ms=now_ms
    )
    assert result.triggered
    return result.event


@pytest.mark.unit
def test_schema_version_is_explicit(long_event):
    intent = build_exit_intent_v1(long_event, created_at_ms=NOW_MS)
    assert (
        intent.schema_version
        == EXIT_INTENT_SCHEMA_VERSION
        == "cdb-stop-loss-exit-intent/v1"
    )


@pytest.mark.unit
def test_long_position_exits_by_selling(long_event):
    intent = build_exit_intent_v1(long_event, created_at_ms=NOW_MS)

    assert intent.side == "SELL"
    assert intent.position_side is PositionSide.LONG
    assert intent.reduce_only is True
    assert intent.intent_kind == "PROTECTIVE_EXIT"


@pytest.mark.unit
def test_short_position_exits_by_buying(short_event):
    intent = build_exit_intent_v1(short_event, created_at_ms=NOW_MS)

    assert intent.side == "BUY"
    assert intent.position_side is PositionSide.SHORT


@pytest.mark.unit
def test_exit_quantity_never_exceeds_position(long_event):
    with pytest.raises(
        StopLossContractError, match=StopLossReason.EXIT_INTENT_INVALID.value
    ):
        build_exit_intent_v1(
            long_event,
            created_at_ms=NOW_MS,
            quantity=long_event.position_quantity + Decimal("0.00000001"),
        )


@pytest.mark.unit
def test_partial_exit_quantity_is_allowed(long_event):
    intent = build_exit_intent_v1(
        long_event, created_at_ms=NOW_MS, quantity=Decimal("0.25")
    )

    assert intent.quantity == Decimal("0.25")
    assert intent.quantity < long_event.position_quantity


@pytest.mark.unit
@pytest.mark.parametrize("quantity", [Decimal("0"), Decimal("-0.5")])
def test_non_positive_exit_quantity_is_rejected(long_event, quantity):
    with pytest.raises(StopLossContractError):
        build_exit_intent_v1(long_event, created_at_ms=NOW_MS, quantity=quantity)


@pytest.mark.unit
def test_float_exit_quantity_is_rejected(long_event):
    with pytest.raises(StopLossContractError, match="must be Decimal"):
        build_exit_intent_v1(long_event, created_at_ms=NOW_MS, quantity=0.25)


@pytest.mark.unit
def test_flat_or_unknown_position_side_has_no_reducing_side(long_event):
    for side in (PositionSide.FLAT, PositionSide.UNKNOWN):
        broken = replace(long_event, position_side=side)
        with pytest.raises(StopLossContractError, match="no reducing side"):
            build_exit_intent_v1(broken, created_at_ms=NOW_MS)


@pytest.mark.unit
def test_non_positive_position_quantity_is_rejected(long_event):
    broken = replace(long_event, position_quantity=Decimal("0"))
    with pytest.raises(StopLossContractError, match="position quantity must be"):
        build_exit_intent_v1(broken, created_at_ms=NOW_MS)


@pytest.mark.unit
def test_intent_id_is_deterministic_for_the_same_event(long_event):
    first = build_exit_intent_v1(long_event, created_at_ms=NOW_MS)
    later = build_exit_intent_v1(long_event, created_at_ms=NOW_MS + 60_000)

    assert first.intent_id == later.intent_id
    assert first.intent_id.startswith("slx-")


@pytest.mark.unit
def test_intent_id_differs_for_different_events(long_event, short_event):
    long_intent = build_exit_intent_v1(long_event, created_at_ms=NOW_MS)
    short_intent = build_exit_intent_v1(short_event, created_at_ms=NOW_MS)

    assert long_intent.intent_id != short_intent.intent_id


@pytest.mark.unit
def test_intent_dict_is_json_safe_and_declares_no_dispatch(long_event):
    payload = build_exit_intent_v1(long_event, created_at_ms=NOW_MS).to_dict()

    assert payload["dispatch_state"] == "NOT_DISPATCHED"
    assert payload["productive_adapter_enabled"] is False
    assert isinstance(payload["quantity"], str)
    assert isinstance(payload["stop_price"], str)
    assert payload["reduce_only"] is True


@pytest.mark.unit
def test_productive_exit_adapter_refuses_intents(long_event):
    intent = build_exit_intent_v1(long_event, created_at_ms=NOW_MS)
    adapter = DisabledProductiveExitAdapter()

    with pytest.raises(
        StopLossContractError, match=StopLossReason.PRODUCTIVE_ADAPTER_DISABLED.value
    ):
        adapter.accept(intent)


@pytest.mark.unit
def test_sinks_satisfy_the_sink_protocol():
    assert isinstance(RecordingExitIntentSink(), ExitIntentSink)
    assert isinstance(DisabledProductiveExitAdapter(), ExitIntentSink)
