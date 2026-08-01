"""Reduce-only position non-increase contract tests for Issue #4184."""

from __future__ import annotations

from decimal import Decimal

import pytest

from services.execution.reduce_only import (
    REDUCE_ONLY_CONCURRENT_CLAIM_BLOCKED,
    REDUCE_ONLY_DUPLICATE_RESULT,
    REDUCE_ONLY_INVALID_QUANTITY,
    REDUCE_ONLY_NO_POSITION,
    REDUCE_ONLY_PARTIAL_FILL,
    REDUCE_ONLY_POSITION_INCREASE_BLOCKED,
    REDUCE_ONLY_POSITION_UNKNOWN,
    REDUCE_ONLY_QUANTITY_CLAMPED,
    REDUCE_ONLY_REJECTED,
    REDUCE_ONLY_SIDE_MISMATCH,
    apply_reduce_only_result,
    prepare_reduce_only,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


@pytest.mark.parametrize(
    ("position_before", "side"),
    [
        (Decimal("1.25"), "SELL"),
        (Decimal("-1.25"), "BUY"),
    ],
)
def test_full_exit_reaches_exact_zero(
    position_before: Decimal,
    side: str,
) -> None:
    preparation = prepare_reduce_only(
        position_before=position_before,
        side=side,
        requested_quantity=Decimal("1.25"),
    )

    outcome = apply_reduce_only_result(
        preparation,
        status="FILLED",
        filled_quantity=Decimal("1.25"),
    )

    assert preparation.allowed is True
    assert outcome.position_after == Decimal("0")
    assert outcome.position_increase_observed is False
    assert outcome.side_flip_observed is False


@pytest.mark.parametrize(
    ("position_before", "side", "expected_after"),
    [
        (Decimal("1.25"), "SELL", Decimal("0.75")),
        (Decimal("-1.25"), "BUY", Decimal("-0.75")),
    ],
)
def test_partial_fill_preserves_side_and_reduces_absolute_position(
    position_before: Decimal,
    side: str,
    expected_after: Decimal,
) -> None:
    preparation = prepare_reduce_only(
        position_before=position_before,
        side=side,
        requested_quantity=Decimal("1.25"),
    )

    outcome = apply_reduce_only_result(
        preparation,
        status="PARTIALLY_FILLED",
        filled_quantity=Decimal("0.50"),
    )

    assert outcome.position_after == expected_after
    assert outcome.remaining_position_quantity == Decimal("0.75")
    assert outcome.reason_code == REDUCE_ONLY_PARTIAL_FILL


def test_existing_persistent_claim_blocks_second_submission() -> None:
    preparation = prepare_reduce_only(
        position_before=Decimal("1"),
        side="SELL",
        requested_quantity=Decimal("0.4"),
        reserved_quantity=Decimal("0.4"),
    )

    assert preparation.allowed is False
    assert preparation.submitted_quantity == Decimal("0")
    assert preparation.reason_code == REDUCE_ONLY_CONCURRENT_CLAIM_BLOCKED


@pytest.mark.parametrize(
    ("position_before", "side"),
    [
        (Decimal("1"), "SELL"),
        (Decimal("-1"), "BUY"),
    ],
)
def test_oversized_exit_is_clamped_before_adapter_submission(
    position_before: Decimal,
    side: str,
) -> None:
    preparation = prepare_reduce_only(
        position_before=position_before,
        side=side,
        requested_quantity=Decimal("2.5"),
    )

    assert preparation.allowed is True
    assert preparation.submitted_quantity == Decimal("1")
    assert preparation.reason_code == REDUCE_ONLY_QUANTITY_CLAMPED


@pytest.mark.parametrize(
    ("position_before", "side", "reason_code"),
    [
        (None, "SELL", REDUCE_ONLY_POSITION_UNKNOWN),
        (Decimal("0"), "SELL", REDUCE_ONLY_NO_POSITION),
        (Decimal("1"), "BUY", REDUCE_ONLY_SIDE_MISMATCH),
        (Decimal("-1"), "SELL", REDUCE_ONLY_SIDE_MISMATCH),
    ],
)
def test_unknown_empty_or_wrong_side_position_blocks(
    position_before: Decimal | None,
    side: str,
    reason_code: str,
) -> None:
    preparation = prepare_reduce_only(
        position_before=position_before,
        side=side,
        requested_quantity=Decimal("0.5"),
    )

    assert preparation.allowed is False
    assert preparation.reason_code == reason_code
    assert preparation.submitted_quantity == Decimal("0")


@pytest.mark.parametrize(
    "quantity",
    [
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
    ],
)
def test_invalid_quantity_blocks(quantity: Decimal) -> None:
    preparation = prepare_reduce_only(
        position_before=Decimal("1"),
        side="SELL",
        requested_quantity=quantity,
    )

    assert preparation.allowed is False
    assert preparation.reason_code == REDUCE_ONLY_INVALID_QUANTITY


def test_rejection_keeps_position_visible_and_unchanged() -> None:
    preparation = prepare_reduce_only(
        position_before=Decimal("-1"),
        side="BUY",
        requested_quantity=Decimal("1"),
    )

    outcome = apply_reduce_only_result(
        preparation,
        status="REJECTED",
        filled_quantity=Decimal("0"),
    )

    assert outcome.position_after == Decimal("-1")
    assert outcome.reason_code == REDUCE_ONLY_REJECTED
    assert outcome.position_increase_observed is False
    assert outcome.side_flip_observed is False


def test_duplicate_result_is_a_noop() -> None:
    preparation = prepare_reduce_only(
        position_before=Decimal("1"),
        side="SELL",
        requested_quantity=Decimal("0.4"),
    )

    outcome = apply_reduce_only_result(
        preparation,
        status="FILLED",
        filled_quantity=Decimal("0.4"),
        already_applied=True,
        persisted_position=Decimal("0.6"),
    )

    assert outcome.position_after == Decimal("0.6")
    assert outcome.reason_code == REDUCE_ONLY_DUPLICATE_RESULT


@pytest.mark.parametrize(
    "position_before",
    [
        Decimal("-100"),
        Decimal("-1"),
        Decimal("-0.00000001"),
        Decimal("0.00000001"),
        Decimal("1"),
        Decimal("100"),
    ],
)
@pytest.mark.parametrize(
    "fill_fraction",
    [Decimal("0"), Decimal("0.1"), Decimal("0.5"), Decimal("1")],
)
def test_property_position_never_increases_or_flips(
    position_before: Decimal,
    fill_fraction: Decimal,
) -> None:
    quantity = abs(position_before)
    side = "SELL" if position_before > 0 else "BUY"
    preparation = prepare_reduce_only(
        position_before=position_before,
        side=side,
        requested_quantity=quantity,
    )
    outcome = apply_reduce_only_result(
        preparation,
        status="FILLED" if fill_fraction == 1 else "PARTIALLY_FILLED",
        filled_quantity=quantity * fill_fraction,
    )

    assert abs(outcome.position_after) <= abs(position_before)
    assert outcome.position_increase_observed is False
    assert outcome.side_flip_observed is False


def test_adapter_overfill_blocks_the_position_claim() -> None:
    preparation = prepare_reduce_only(
        position_before=Decimal("1"),
        side="SELL",
        requested_quantity=Decimal("1"),
    )

    outcome = apply_reduce_only_result(
        preparation,
        status="FILLED",
        filled_quantity=Decimal("1.1"),
    )

    assert outcome.applied is False
    assert outcome.position_after == Decimal("1")
    assert outcome.reason_code == REDUCE_ONLY_POSITION_INCREASE_BLOCKED


def test_unknown_adapter_status_blocks_the_position_claim() -> None:
    preparation = prepare_reduce_only(
        position_before=Decimal("1"),
        side="SELL",
        requested_quantity=Decimal("1"),
    )

    outcome = apply_reduce_only_result(
        preparation,
        status="VENUE_UNKNOWN",
        filled_quantity=Decimal("0.5"),
    )

    assert outcome.applied is False
    assert outcome.position_after == Decimal("1")
    assert outcome.reason_code == REDUCE_ONLY_POSITION_INCREASE_BLOCKED
