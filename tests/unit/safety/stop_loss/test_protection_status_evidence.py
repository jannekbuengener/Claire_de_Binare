"""Protection status evidence gate tests (Issue #4186, extends #4152).

Protected rule: stop-loss protection may only be called available when every
required proof exists. Delivering trigger, consumer, and dedup code is not
sufficient — real-stack persistence and a productive exit path are still open,
so the canonical status must stay UNAVAILABLE.
"""

from __future__ import annotations

from dataclasses import fields, replace

import pytest

from core.safety.stop_loss_protection import (
    STOP_LOSS_PROTECTION_EVIDENCE,
    STOP_LOSS_PROTECTION_STATUS,
    StopLossProtectionEvidence,
    StopLossProtectionStatus,
    resolve_stop_loss_protection_status,
    stop_loss_protection_evidence_gaps,
    stop_loss_protection_is_available,
)

_ALL_PROOFS = tuple(field.name for field in fields(StopLossProtectionEvidence))


@pytest.mark.unit
def test_canonical_status_remains_unavailable_after_4186():
    assert STOP_LOSS_PROTECTION_STATUS is StopLossProtectionStatus.UNAVAILABLE
    assert stop_loss_protection_is_available() is False


@pytest.mark.unit
def test_status_is_derived_from_the_evidence_ledger():
    assert STOP_LOSS_PROTECTION_STATUS == resolve_stop_loss_protection_status(
        STOP_LOSS_PROTECTION_EVIDENCE
    )


@pytest.mark.unit
def test_declared_evidence_gaps_are_the_open_proofs():
    assert stop_loss_protection_evidence_gaps() == (
        "real_stack_persistence_proven",
        "productive_exit_path_proven",
    )


@pytest.mark.unit
def test_delivered_proofs_are_claimed_honestly():
    evidence = STOP_LOSS_PROTECTION_EVIDENCE

    assert evidence.trigger_contract_proven is True
    assert evidence.consumer_proven is True
    assert evidence.persistent_dedup_proven is True
    assert evidence.restart_replay_proven is True
    assert evidence.real_stack_persistence_proven is False
    assert evidence.productive_exit_path_proven is False


@pytest.mark.unit
def test_default_evidence_is_empty_and_unavailable():
    empty = StopLossProtectionEvidence()

    assert empty.complete is False
    assert set(empty.missing_evidence()) == set(_ALL_PROOFS)
    assert (
        resolve_stop_loss_protection_status(empty)
        is StopLossProtectionStatus.UNAVAILABLE
    )


@pytest.mark.unit
@pytest.mark.parametrize("missing_proof", _ALL_PROOFS)
def test_any_single_missing_proof_keeps_protection_unavailable(missing_proof):
    complete = StopLossProtectionEvidence(**{name: True for name in _ALL_PROOFS})
    degraded = replace(complete, **{missing_proof: False})

    assert resolve_stop_loss_protection_status(complete) is (
        StopLossProtectionStatus.END_TO_END_PROVEN
    )
    assert resolve_stop_loss_protection_status(degraded) is (
        StopLossProtectionStatus.UNAVAILABLE
    )
    assert degraded.missing_evidence() == (missing_proof,)
