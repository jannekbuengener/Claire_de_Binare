"""Stop-loss protection status contract (Issue #4152 / CDB-036, extended #4186).

Stop-loss metadata on orders is ARTIFACT_ONLY until an end-to-end consumer
and exit/unwind path is proven. Callers must not treat presence of
``stop_loss_pct`` as protection evidence.

Issue #4186 adds the trigger contract, the restart-safe consumer, and the
persistent dedup state (``core.safety.stop_loss``). The status is derived from
an explicit evidence ledger: as long as one required proof is missing, the
status stays ``UNAVAILABLE``. Protection availability is never asserted from
code presence alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StopLossProtectionStatus(str, Enum):
    """Machine-readable stop-loss protection availability."""

    ARTIFACT_ONLY = "ARTIFACT_ONLY"
    UNAVAILABLE = "UNAVAILABLE"
    END_TO_END_PROVEN = "END_TO_END_PROVEN"


@dataclass(frozen=True)
class StopLossProtectionEvidence:
    """Required proofs before stop-loss protection may be called available.

    Every field must be backed by a concrete artifact (test, evidence file, or
    runtime drill). A ``True`` value without such an artifact is a governance
    violation, not a shortcut.
    """

    trigger_contract_proven: bool = False
    consumer_proven: bool = False
    persistent_dedup_proven: bool = False
    restart_replay_proven: bool = False
    real_stack_persistence_proven: bool = False
    productive_exit_path_proven: bool = False

    def missing_evidence(self) -> tuple[str, ...]:
        """Return the names of all required proofs that are still missing."""
        return tuple(
            field
            for field, proven in (
                ("trigger_contract_proven", self.trigger_contract_proven),
                ("consumer_proven", self.consumer_proven),
                ("persistent_dedup_proven", self.persistent_dedup_proven),
                ("restart_replay_proven", self.restart_replay_proven),
                (
                    "real_stack_persistence_proven",
                    self.real_stack_persistence_proven,
                ),
                ("productive_exit_path_proven", self.productive_exit_path_proven),
            )
            if not proven
        )

    @property
    def complete(self) -> bool:
        return not self.missing_evidence()


def resolve_stop_loss_protection_status(
    evidence: StopLossProtectionEvidence,
) -> StopLossProtectionStatus:
    """Derive the protection status from an evidence ledger, fail-closed."""
    if evidence.complete:
        return StopLossProtectionStatus.END_TO_END_PROVEN
    return StopLossProtectionStatus.UNAVAILABLE


# Honest evidence ledger after Issue #4186 (mock/shadow slice).
# Trigger, consumer, dedup persistence, and restart/replay behaviour are proven
# by unit/contract/shadow tests. Real-stack persistence and a productive exit
# path are NOT proven and are explicitly out of scope for this slice.
STOP_LOSS_PROTECTION_EVIDENCE = StopLossProtectionEvidence(
    trigger_contract_proven=True,
    consumer_proven=True,
    persistent_dedup_proven=True,
    restart_replay_proven=True,
    real_stack_persistence_proven=False,
    productive_exit_path_proven=False,
)

# Canonical status until a proven consumer + exit path exists.
STOP_LOSS_PROTECTION_STATUS = resolve_stop_loss_protection_status(
    STOP_LOSS_PROTECTION_EVIDENCE
)

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


def stop_loss_protection_evidence_gaps() -> tuple[str, ...]:
    """Return the missing proofs that keep protection unavailable."""
    return STOP_LOSS_PROTECTION_EVIDENCE.missing_evidence()
