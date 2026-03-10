import pytest

from services.execution.models import OrderStatus
from services.execution.state_machine import is_valid_transition, validate_transition

ALL_STATUSES = [status.value for status in OrderStatus]

ALLOWED_TRANSITIONS = {
    (OrderStatus.PENDING.value, OrderStatus.SUBMITTED.value),
    (OrderStatus.PENDING.value, OrderStatus.REJECTED.value),
    (OrderStatus.PENDING.value, OrderStatus.FAILED.value),
    (OrderStatus.PENDING.value, OrderStatus.CANCELLED.value),
    (OrderStatus.SUBMITTED.value, OrderStatus.PARTIALLY_FILLED.value),
    (OrderStatus.SUBMITTED.value, OrderStatus.FILLED.value),
    (OrderStatus.SUBMITTED.value, OrderStatus.REJECTED.value),
    (OrderStatus.SUBMITTED.value, OrderStatus.FAILED.value),
    (OrderStatus.SUBMITTED.value, OrderStatus.CANCELLED.value),
    (OrderStatus.PARTIALLY_FILLED.value, OrderStatus.PARTIALLY_FILLED.value),
    (OrderStatus.PARTIALLY_FILLED.value, OrderStatus.FILLED.value),
    (OrderStatus.PARTIALLY_FILLED.value, OrderStatus.CANCELLED.value),
    (OrderStatus.PARTIALLY_FILLED.value, OrderStatus.FAILED.value),
}

FORBIDDEN_TRANSITIONS = sorted(
    {
        (from_status, to_status)
        for from_status in ALL_STATUSES
        for to_status in ALL_STATUSES
        if (from_status, to_status) not in ALLOWED_TRANSITIONS
    }
)


@pytest.mark.parametrize(("from_status", "to_status"), sorted(ALLOWED_TRANSITIONS))
def test_allowed_transitions_are_valid(from_status: str, to_status: str) -> None:
    assert is_valid_transition(from_status, to_status) is True
    validate_transition(from_status, to_status)


@pytest.mark.parametrize(("from_status", "to_status"), FORBIDDEN_TRANSITIONS)
def test_forbidden_transitions_are_invalid(from_status: str, to_status: str) -> None:
    assert is_valid_transition(from_status, to_status) is False
    with pytest.raises(ValueError, match="Invalid execution status transition"):
        validate_transition(from_status, to_status)


@pytest.mark.parametrize(
    "terminal_status",
    [
        OrderStatus.FILLED.value,
        OrderStatus.REJECTED.value,
        OrderStatus.CANCELLED.value,
        OrderStatus.FAILED.value,
    ],
)
def test_terminal_states_have_no_outgoing_transitions(terminal_status: str) -> None:
    for target_status in ALL_STATUSES:
        assert is_valid_transition(terminal_status, target_status) is False


def test_partially_filled_self_transition_is_idempotent_and_allowed() -> None:
    from_status = OrderStatus.PARTIALLY_FILLED.value
    to_status = OrderStatus.PARTIALLY_FILLED.value

    assert is_valid_transition(from_status, to_status) is True
    validate_transition(from_status, to_status)


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        ("UNKNOWN", OrderStatus.FILLED.value),
        (OrderStatus.PENDING.value, "UNKNOWN"),
    ],
)
def test_unknown_status_values_are_rejected(from_status: str, to_status: str) -> None:
    assert is_valid_transition(from_status, to_status) is False
    with pytest.raises(ValueError, match="Invalid execution status transition"):
        validate_transition(from_status, to_status)
