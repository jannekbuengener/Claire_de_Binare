"""Stop-loss protection contract tests for Issue #4152 (S3 honest fail-closed)."""

from __future__ import annotations

import pytest

from core.safety.stop_loss_protection import (
    STOP_LOSS_PROTECTION_BLOCK_REASON,
    STOP_LOSS_PROTECTION_STATUS,
    StopLossProtectionStatus,
    assert_stop_loss_protection_available,
    stop_loss_metadata_note,
    stop_loss_protection_is_available,
)


@pytest.mark.unit
def test_stop_loss_protection_is_unavailable():
    assert STOP_LOSS_PROTECTION_STATUS == StopLossProtectionStatus.UNAVAILABLE
    assert stop_loss_protection_is_available() is False


@pytest.mark.unit
def test_unconsumed_stop_loss_cannot_report_protection_pass():
    with pytest.raises(RuntimeError, match=STOP_LOSS_PROTECTION_BLOCK_REASON):
        assert_stop_loss_protection_available(claim_source="candidate_evidence")


@pytest.mark.unit
def test_metadata_note_does_not_claim_protection():
    note = stop_loss_metadata_note()
    assert "ARTIFACT" in note or "UNAVAILABLE" in note
    assert "proven" in note.lower() or "metadata" in note.lower()
    assert "PASS" not in note
