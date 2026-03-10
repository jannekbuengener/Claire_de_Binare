"""Execution status transition contract for order lifecycle."""

from __future__ import annotations

from typing import Final

from .models import OrderStatus

_ALLOWED_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    OrderStatus.PENDING.value: frozenset(
        {
            OrderStatus.SUBMITTED.value,
            OrderStatus.REJECTED.value,
            OrderStatus.FAILED.value,
            OrderStatus.CANCELLED.value,
        }
    ),
    OrderStatus.SUBMITTED.value: frozenset(
        {
            OrderStatus.PARTIALLY_FILLED.value,
            OrderStatus.FILLED.value,
            OrderStatus.REJECTED.value,
            OrderStatus.FAILED.value,
            OrderStatus.CANCELLED.value,
        }
    ),
    OrderStatus.PARTIALLY_FILLED.value: frozenset(
        {
            OrderStatus.PARTIALLY_FILLED.value,
            OrderStatus.FILLED.value,
            OrderStatus.CANCELLED.value,
            OrderStatus.FAILED.value,
        }
    ),
    OrderStatus.FILLED.value: frozenset(),
    OrderStatus.REJECTED.value: frozenset(),
    OrderStatus.CANCELLED.value: frozenset(),
    OrderStatus.FAILED.value: frozenset(),
}


def is_valid_transition(from_status: str, to_status: str) -> bool:
    """Return True if the status transition is allowed by contract."""

    allowed_next = _ALLOWED_TRANSITIONS.get(from_status)
    if allowed_next is None:
        return False
    return to_status in allowed_next


def validate_transition(from_status: str, to_status: str) -> None:
    """Raise ValueError when status transition violates the contract."""

    if is_valid_transition(from_status, to_status):
        return

    allowed_next = sorted(_ALLOWED_TRANSITIONS.get(from_status, frozenset()))
    allowed_text = ", ".join(allowed_next) if allowed_next else "<none>"
    raise ValueError(
        "Invalid execution status transition: "
        f"{from_status} -> {to_status}. Allowed next: {allowed_text}."
    )
