"""Property tests for protection event identity (Issue #4186).

Protected rule: the protection event id must be a pure function of the
protection situation. Deterministic pseudo-random inputs are used instead of a
property-testing library (hypothesis is not a repo dependency) so failures stay
reproducible from the seed.
"""

from __future__ import annotations

import random
from dataclasses import replace
from decimal import Decimal

import pytest

from core.safety.stop_loss import (
    PositionSide,
    PositionSnapshot,
    StopLossTriggerConfig,
    evaluate_stop_loss_trigger,
)

from tests.unit.safety.stop_loss.conftest import NOW_MS, observation

_SEED = 4186
_CASES = 200


def _random_case(rng: random.Random) -> tuple[PositionSnapshot, Decimal, Decimal]:
    """Return (position, stop_loss_pct, breach_price) for a triggering case."""
    side = rng.choice([PositionSide.LONG, PositionSide.SHORT])
    entry = Decimal(rng.randrange(1_00, 5_000_00)).scaleb(-2)
    pct = Decimal(rng.randrange(1_000, 200_000)).scaleb(-6)
    position = PositionSnapshot(
        symbol=rng.choice(["BTCUSDT", "ETHUSDT", "SOLUSDT"]),
        side=side,
        quantity=Decimal(rng.randrange(1, 10_000)).scaleb(-4),
        entry_price=entry,
        position_id=f"pos-{rng.randrange(10**6)}",
        opened_at_ms=NOW_MS - rng.randrange(1, 10**6),
    )
    if side is PositionSide.LONG:
        breach = (entry * (Decimal(1) - pct) * Decimal("0.9")).quantize(
            Decimal("0.00000001")
        )
    else:
        breach = (entry * (Decimal(1) + pct) * Decimal("1.1")).quantize(
            Decimal("0.00000001")
        )
    return position, pct, breach


@pytest.mark.unit
def test_event_id_is_deterministic_for_identical_protection_situations():
    rng = random.Random(_SEED)
    for _ in range(_CASES):
        position, pct, breach = _random_case(rng)
        config = StopLossTriggerConfig(stop_loss_pct=pct)
        obs = observation(str(breach), symbol=position.symbol)

        first = evaluate_stop_loss_trigger(position, obs, config, now_ms=NOW_MS)
        second = evaluate_stop_loss_trigger(position, obs, config, now_ms=NOW_MS)

        assert first.triggered, f"expected trigger for {position} at {breach}"
        assert first.event.event_id == second.event.event_id
        assert first.event.fingerprint == second.event.fingerprint


@pytest.mark.unit
def test_event_id_is_independent_of_observing_tick():
    """Different ticks breaching the same armed stop map to one protection event."""
    rng = random.Random(_SEED + 1)
    for _ in range(_CASES):
        position, pct, breach = _random_case(rng)
        config = StopLossTriggerConfig(stop_loss_pct=pct)

        if position.side is PositionSide.LONG:
            deeper = (breach * Decimal("0.5")).quantize(Decimal("0.00000001"))
        else:
            deeper = (breach * Decimal("2")).quantize(Decimal("0.00000001"))

        first = evaluate_stop_loss_trigger(
            position,
            observation(
                str(breach), symbol=position.symbol, observed_at_ms=NOW_MS - 5_000
            ),
            config,
            now_ms=NOW_MS,
        )
        later = evaluate_stop_loss_trigger(
            position,
            observation(
                str(deeper), symbol=position.symbol, observed_at_ms=NOW_MS - 10
            ),
            config,
            now_ms=NOW_MS,
        )

        assert first.triggered and later.triggered
        assert first.event.event_id == later.event.event_id


@pytest.mark.unit
@pytest.mark.parametrize(
    "mutation",
    [
        {"position_id": "pos-other"},
        {"symbol": "ETHUSDT"},
        {"quantity": Decimal("0.75")},
        {"entry_price": Decimal("101.00")},
        {"opened_at_ms": NOW_MS - 999},
    ],
)
def test_distinct_protection_situations_get_distinct_event_ids(
    long_position, config, breach_observation, now_ms, mutation
):
    baseline = evaluate_stop_loss_trigger(
        long_position, breach_observation, config, now_ms=now_ms
    )
    mutated_position = replace(long_position, **mutation)
    symbol = mutated_position.symbol
    mutated = evaluate_stop_loss_trigger(
        mutated_position,
        observation("97.50", symbol=symbol),
        config,
        now_ms=now_ms,
    )

    assert baseline.triggered and mutated.triggered
    assert baseline.event.event_id != mutated.event.event_id


@pytest.mark.unit
def test_rearmed_stop_gets_a_new_event_id(long_position, breach_observation, now_ms):
    tight = evaluate_stop_loss_trigger(
        long_position,
        breach_observation,
        StopLossTriggerConfig(stop_loss_pct=Decimal("0.02")),
        now_ms=now_ms,
    )
    wide = evaluate_stop_loss_trigger(
        long_position,
        breach_observation,
        StopLossTriggerConfig(stop_loss_pct=Decimal("0.01")),
        now_ms=now_ms,
    )

    assert tight.triggered and wide.triggered
    assert tight.event.event_id != wide.event.event_id


@pytest.mark.unit
def test_long_and_short_never_share_an_event_id(long_position, config, now_ms):
    short = PositionSnapshot(
        symbol=long_position.symbol,
        side=PositionSide.SHORT,
        quantity=long_position.quantity,
        entry_price=long_position.entry_price,
        position_id=long_position.position_id,
        opened_at_ms=long_position.opened_at_ms,
    )
    long_result = evaluate_stop_loss_trigger(
        long_position, observation("97.50"), config, now_ms=now_ms
    )
    short_result = evaluate_stop_loss_trigger(
        short, observation("102.50"), config, now_ms=now_ms
    )

    assert long_result.event.event_id != short_result.event.event_id


@pytest.mark.unit
def test_event_identity_excludes_observation_fields(long_position, config, now_ms):
    result = evaluate_stop_loss_trigger(
        long_position, observation("97.50"), config, now_ms=now_ms
    )
    identity = result.event.identity()

    assert "observed_price" not in identity
    assert "observed_at_ms" not in identity
    assert "price_source" not in identity
    assert identity["position_opened_at_ms"] == long_position.opened_at_ms
