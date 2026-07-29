"""Stop-loss protection status contract (Issue #4152 / CDB-036).

Stop-loss metadata on orders is ARTIFACT_ONLY until an end-to-end consumer
and exit/unwind path is proven. Callers must not treat presence of
``stop_loss_pct`` as protection evidence.
"""

from __future__ import annotations

from enum import Enum


class StopLossProtectionStatus(str, Enum):
    """Machine-readable stop-loss protection availability."""

    ARTIFACT_ONLY = "ARTIFACT_ONLY"
    UNAVAILABLE = "UNAVAILABLE"
    END_TO_END_PROVEN = "END_TO_END_PROVEN"


# Canonical status until a proven consumer + exit path exists.
STOP_LOSS_PROTECTION_STATUS = StopLossProtectionStatus.UNAVAILABLE

STOP_LOSS_PROTECTION_BLOCK_REASON = "STOP_LOSS_PROTECTION_UNAVAILABLE"


def stop_loss_protection_is_available() -> bool:
    """Return True only when end-to-end stop-loss protection is proven."""
    return STOP_LOSS_PROTECTION_STATUS == StopLossProtectionStatus.END_TO_END_PROVEN


def assert_stop_loss_protection_available(*, claim_source: str = "unknown") -> None:
    """Fail-closed: refuse any claim that stop-loss protection is available."""
    if not stop_loss_protection_is_available():
        raise RuntimeError(
            f"{STOP_LOSS_PROTECTION_BLOCK_REASON}: stop-loss protection cannot be "
            f"claimed as available from {claim_source}; status="
            f"{STOP_LOSS_PROTECTION_STATUS.value} (metadata is ARTIFACT_ONLY)"
        )


def stop_loss_metadata_note() -> str:
    """Operator-facing note for logs/docs: metadata must not imply protection."""
    return (
        "stop_loss_pct is order metadata only "
        f"(protection_status={STOP_LOSS_PROTECTION_STATUS.value}); "
        "no proven consumer/exit path"
    )
