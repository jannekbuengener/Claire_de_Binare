"""Pure governed run lifecycle transitions (ACP §5).

Issue-only labels VALIDATED / EVIDENCE_COLLECTED / HANDED_OFF are events,
not additional canonical lifecycle states.
"""

from __future__ import annotations

from typing import Final

from tools.agent_control.errors import DispatchError

CANONICAL_STATES: Final[tuple[str, ...]] = (
    "PLANNED",
    "ROUTED",
    "CONTRACTED",
    "DISPATCHED",
    "RUNNING",
    "AWAITING_APPROVAL",
    "DELIVERED",
    "PASS",
    "HOLD",
    "BLOCKED",
    "FAILED",
    "CANCELLED",
)

TERMINAL_STATES: Final[frozenset[str]] = frozenset(
    {"PASS", "HOLD", "BLOCKED", "FAILED", "CANCELLED"}
)

ALLOWED_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    "PLANNED": frozenset({"ROUTED", "HOLD", "BLOCKED", "CANCELLED"}),
    "ROUTED": frozenset({"CONTRACTED", "HOLD", "BLOCKED", "CANCELLED"}),
    "CONTRACTED": frozenset({"DISPATCHED", "HOLD", "BLOCKED", "CANCELLED"}),
    "DISPATCHED": frozenset({"RUNNING", "FAILED", "CANCELLED"}),
    "RUNNING": frozenset(
        {"AWAITING_APPROVAL", "DELIVERED", "FAILED", "HOLD", "BLOCKED", "CANCELLED"}
    ),
    "AWAITING_APPROVAL": frozenset({"DELIVERED", "HOLD", "BLOCKED", "CANCELLED"}),
    "DELIVERED": frozenset({"PASS", "HOLD"}),
}

# Issue #4253 vocabulary mapped to canon (events, not states).
ISSUE_STATE_MAPPING: Final[dict[str, str]] = {
    "VALIDATED": "CONTRACTED via validation_success event",
    "EVIDENCE_COLLECTED": "lifecycle snapshot event only",
    "HANDED_OFF": "handoff event; then DELIVERED -> PASS|HOLD",
}


def assert_known_state(state: str) -> None:
    if state not in CANONICAL_STATES:
        raise DispatchError(
            "DISPATCH_UNKNOWN_STATE",
            f"unknown lifecycle state: {state!r}",
        )


def can_transition(current: str, nxt: str) -> bool:
    assert_known_state(current)
    assert_known_state(nxt)
    if current == nxt:
        return True
    if current in TERMINAL_STATES:
        return False
    return nxt in ALLOWED_TRANSITIONS.get(current, frozenset())


def transition(current: str, nxt: str) -> str:
    """Return nxt if legal; raise without implying any mutation on failure."""
    assert_known_state(current)
    assert_known_state(nxt)
    if current == nxt:
        return nxt
    if current in TERMINAL_STATES:
        raise DispatchError(
            "DISPATCH_TERMINAL_TRANSITION",
            f"cannot transition from terminal state {current!r} to {nxt!r}",
        )
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if nxt not in allowed:
        raise DispatchError(
            "DISPATCH_ILLEGAL_TRANSITION",
            f"illegal transition {current!r} -> {nxt!r}",
        )
    return nxt
