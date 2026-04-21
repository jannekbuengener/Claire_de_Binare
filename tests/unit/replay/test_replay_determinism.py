"""Unit tests for replay determinism validation and hashing.

Scope:
  - Envelope validation
  - Chain integrity verification
  - Hash computation consistency
  - Error handling (fail-closed)
"""

import pytest
from core.replay.determinism import (
    ReplayDeterminismError,
    validate_envelope_determinism,
    compute_envelope_hash,
    verify_envelope_chain_integrity,
    verify_replay_execution_result,
    verify_replay_integrity_result,
    compute_replay_report_hash,
)
from core.replay.envelopes import DecisionEnvelopeV1, OrderEnvelopeV1, FillEnvelopeV1
from core.replay.replay_contracts import (
    ReplayRunSpec,
    ReplayExecutionResult,
    ReplayIntegrity,
    EnvelopeSummary,
    ReplayReportArtifactManifest,
    ReplayReportInput,
)


class TestValidateEnvelopeDeterminism:
    """Tests for validate_envelope_determinism."""

    def test_valid_decision_envelope(self) -> None:
        """Valid DecisionEnvelopeV1 passes validation."""
        envelope = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="dec-001",
            ts_ms=1000000,
            payload={"decision": "ALLOW"},
        )
        # Should not raise
        validate_envelope_determinism(envelope)

    def test_valid_order_envelope(self) -> None:
        """Valid OrderEnvelopeV1 passes validation."""
        envelope = OrderEnvelopeV1(
            schema_version="envelope.v1",
            event_type="ORDER",
            event_id="ord-001",
            ts_ms=1000001,
            payload={"side": "BUY", "qty": 1.0},
        )
        validate_envelope_determinism(envelope)

    def test_valid_fill_envelope(self) -> None:
        """Valid FillEnvelopeV1 passes validation."""
        envelope = FillEnvelopeV1(
            schema_version="envelope.v1",
            event_type="FILL",
            event_id="fill-001",
            ts_ms=1000002,
            payload={"filled": 1.0, "price": 50000.0},
        )
        validate_envelope_determinism(envelope)

    def test_rejects_invalid_schema_version(self) -> None:
        """Rejects envelope with wrong schema_version."""
        envelope = DecisionEnvelopeV1(
            schema_version="envelope.v2",  # Wrong version
            event_type="DECISION",
            event_id="dec-002",
            ts_ms=1000000,
            payload={"decision": "BLOCK"},
        )
        with pytest.raises(ReplayDeterminismError, match="schema_version"):
            validate_envelope_determinism(envelope)

    def test_rejects_invalid_event_type(self) -> None:
        """Rejects envelope with invalid event_type."""
        envelope = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="INVALID",  # Wrong type
            event_id="dec-003",
            ts_ms=1000000,
            payload={"decision": "ALLOW"},
        )
        with pytest.raises(ReplayDeterminismError, match="event_type"):
            validate_envelope_determinism(envelope)

    def test_rejects_empty_event_id(self) -> None:
        """Rejects envelope with empty event_id."""
        envelope = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="",  # Empty
            ts_ms=1000000,
            payload={"decision": "ALLOW"},
        )
        with pytest.raises(ReplayDeterminismError, match="event_id"):
            validate_envelope_determinism(envelope)

    def test_rejects_negative_ts_ms(self) -> None:
        """Rejects envelope with negative ts_ms."""
        envelope = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="dec-004",
            ts_ms=-1,  # Negative
            payload={"decision": "ALLOW"},
        )
        with pytest.raises(ReplayDeterminismError, match="ts_ms"):
            validate_envelope_determinism(envelope)

    def test_rejects_non_dict_payload(self) -> None:
        """Rejects envelope with non-dict payload."""
        envelope = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="dec-005",
            ts_ms=1000000,
            payload=[1, 2, 3],  # type: ignore  # Wrong type
        )
        with pytest.raises(ReplayDeterminismError, match="payload"):
            validate_envelope_determinism(envelope)

    def test_rejects_missing_to_dict_method(self) -> None:
        """Rejects object without to_dict() method."""
        obj = {"schema_version": "envelope.v1"}  # type: ignore
        with pytest.raises(ReplayDeterminismError, match="to_dict"):
            validate_envelope_determinism(obj)


class TestComputeEnvelopeHash:
    """Tests for compute_envelope_hash."""

    def test_hash_is_64char_hex(self) -> None:
        """Hash is 64-character lowercase hex string."""
        envelope = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="dec-hash-001",
            ts_ms=1000000,
            payload={"decision": "ALLOW"},
        )
        h = compute_envelope_hash(envelope)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_identical_envelopes_same_hash(self) -> None:
        """Identical envelopes produce identical hashes."""
        env1 = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="dec-hash-002",
            ts_ms=2000000,
            payload={"decision": "BLOCK"},
        )
        env2 = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="dec-hash-002",
            ts_ms=2000000,
            payload={"decision": "BLOCK"},
        )
        assert compute_envelope_hash(env1) == compute_envelope_hash(env2)

    def test_different_payload_different_hash(self) -> None:
        """Different payloads produce different hashes."""
        env1 = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="dec-hash-003",
            ts_ms=3000000,
            payload={"decision": "ALLOW"},
        )
        env2 = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="dec-hash-003",
            ts_ms=3000000,
            payload={"decision": "BLOCK"},
        )
        assert compute_envelope_hash(env1) != compute_envelope_hash(env2)

    def test_rejects_invalid_envelope(self) -> None:
        """Raises ReplayDeterminismError for invalid envelope."""
        envelope = DecisionEnvelopeV1(
            schema_version="envelope.v2",  # Invalid
            event_type="DECISION",
            event_id="dec-hash-004",
            ts_ms=4000000,
            payload={"decision": "ALLOW"},
        )
        with pytest.raises(ReplayDeterminismError):
            compute_envelope_hash(envelope)


class TestVerifyEnvelopeChainIntegrity:
    """Tests for verify_envelope_chain_integrity."""

    def test_empty_chain(self) -> None:
        """Empty envelope list produces empty chain hash."""
        h = verify_envelope_chain_integrity([])
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_single_envelope_chain(self) -> None:
        """Chain with single envelope computes correctly."""
        envelope = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="chain-001",
            ts_ms=1000000,
            payload={"decision": "ALLOW"},
        )
        h = verify_envelope_chain_integrity([envelope])
        assert len(h) == 64

    def test_multiple_envelope_chain(self) -> None:
        """Chain with multiple envelopes verifies ordering."""
        env1 = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="chain-002a",
            ts_ms=1000000,
            payload={"decision": "ALLOW"},
        )
        env2 = OrderEnvelopeV1(
            schema_version="envelope.v1",
            event_type="ORDER",
            event_id="chain-002b",
            ts_ms=1000001,
            payload={"side": "BUY"},
        )
        env3 = FillEnvelopeV1(
            schema_version="envelope.v1",
            event_type="FILL",
            event_id="chain-002c",
            ts_ms=1000002,
            payload={"filled": 1.0},
        )
        h = verify_envelope_chain_integrity([env1, env2, env3])
        assert len(h) == 64

    def test_rejects_non_monotonic_timestamps(self) -> None:
        """Rejects chain with decreasing timestamps."""
        env1 = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="chain-003a",
            ts_ms=2000000,  # Later
            payload={"decision": "ALLOW"},
        )
        env2 = OrderEnvelopeV1(
            schema_version="envelope.v1",
            event_type="ORDER",
            event_id="chain-003b",
            ts_ms=1000000,  # Earlier (violation!)
            payload={"side": "BUY"},
        )
        with pytest.raises(ReplayDeterminismError, match="timestamp"):
            verify_envelope_chain_integrity([env1, env2])

    def test_rejects_duplicate_event_ids(self) -> None:
        """Rejects chain with duplicate event_ids."""
        env1 = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="chain-004",  # Same ID
            ts_ms=1000000,
            payload={"decision": "ALLOW"},
        )
        env2 = OrderEnvelopeV1(
            schema_version="envelope.v1",
            event_type="ORDER",
            event_id="chain-004",  # Duplicate!
            ts_ms=1000001,
            payload={"side": "BUY"},
        )
        with pytest.raises(ReplayDeterminismError, match="duplicate.*event_id"):
            verify_envelope_chain_integrity([env1, env2])

    def test_verify_expected_hash(self) -> None:
        """Verifies chain hash matches expected value."""
        envelope = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="chain-005",
            ts_ms=1000000,
            payload={"decision": "BLOCK"},
        )
        h = verify_envelope_chain_integrity([envelope])
        # Verify again with expected hash
        verify_envelope_chain_integrity([envelope], expected_chain_hash=h)

    def test_rejects_wrong_expected_hash(self) -> None:
        """Rejects chain with wrong expected hash."""
        envelope = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="chain-006",
            ts_ms=1000000,
            payload={"decision": "ALLOW"},
        )
        wrong_hash = "z" * 64
        with pytest.raises(ReplayDeterminismError, match="hash mismatch"):
            verify_envelope_chain_integrity([envelope], expected_chain_hash=wrong_hash)


class TestVerifyReplayExecutionResult:
    """Tests for verify_replay_execution_result."""

    def test_valid_result(self) -> None:
        """Valid ReplayExecutionResult passes verification."""
        result = ReplayExecutionResult(
            run_id="exec-001",
            events_processed=100,
            decisions_made=10,
            orders_placed=5,
            fills_recorded=4,
            envelope_hashes=["a" * 64, "b" * 64],
        )
        verify_replay_execution_result(result)  # Should not raise

    def test_rejects_invalid_run_id(self) -> None:
        """Rejects result with empty run_id."""
        result = ReplayExecutionResult(
            run_id="",  # Empty
            events_processed=100,
            decisions_made=10,
            orders_placed=5,
            fills_recorded=4,
            envelope_hashes=["c" * 64],
        )
        with pytest.raises(ReplayDeterminismError, match="run_id"):
            verify_replay_execution_result(result)

    def test_rejects_negative_counts(self) -> None:
        """Rejects result with negative event counts."""
        result = ReplayExecutionResult(
            run_id="exec-002",
            events_processed=-1,  # Negative
            decisions_made=10,
            orders_placed=5,
            fills_recorded=4,
            envelope_hashes=["d" * 64],
        )
        with pytest.raises(ReplayDeterminismError, match="events_processed"):
            verify_replay_execution_result(result)

    def test_rejects_invalid_envelope_hashes(self) -> None:
        """Rejects result with invalid envelope hashes."""
        result = ReplayExecutionResult(
            run_id="exec-003",
            events_processed=100,
            decisions_made=10,
            orders_placed=5,
            fills_recorded=4,
            envelope_hashes=["invalid-hash"],  # Too short
        )
        with pytest.raises(ReplayDeterminismError, match="envelope_hashes"):
            verify_replay_execution_result(result)

    def test_rejects_error_with_events(self) -> None:
        """Rejects result with error_message but events_processed > 0."""
        result = ReplayExecutionResult(
            run_id="exec-004",
            events_processed=10,  # Non-zero
            decisions_made=0,
            orders_placed=0,
            fills_recorded=0,
            envelope_hashes=[],
            error_message="Error occurred",  # Inconsistent
        )
        with pytest.raises(ReplayDeterminismError, match="Inconsistent"):
            verify_replay_execution_result(result)


class TestVerifyReplayIntegrityResult:
    """Tests for verify_replay_integrity_result."""

    def test_valid_integrity_ok(self) -> None:
        """Valid integrity result with ok=True passes."""
        integrity = ReplayIntegrity(
            run_id="int-001",
            envelope_count=10,
            envelope_chain_hash="a" * 64,
            event_loop_states_hash="b" * 64,
            integrity_ok=True,
            failed_checks=[],
        )
        verify_replay_integrity_result(integrity)  # Should not raise

    def test_valid_integrity_failed(self) -> None:
        """Valid integrity result with ok=False and failures passes."""
        integrity = ReplayIntegrity(
            run_id="int-002",
            envelope_count=10,
            envelope_chain_hash="c" * 64,
            event_loop_states_hash="d" * 64,
            integrity_ok=False,
            failed_checks=["check_1", "check_2"],
        )
        verify_replay_integrity_result(integrity)  # Should not raise

    def test_rejects_integrity_ok_with_failures(self) -> None:
        """Rejects integrity=True but failed_checks non-empty."""
        integrity = ReplayIntegrity(
            run_id="int-003",
            envelope_count=10,
            envelope_chain_hash="e" * 64,
            event_loop_states_hash="f" * 64,
            integrity_ok=True,
            failed_checks=["check_failed"],  # Inconsistent
        )
        with pytest.raises(ReplayDeterminismError, match="Inconsistent"):
            verify_replay_integrity_result(integrity)

    def test_rejects_integrity_failed_without_failures(self) -> None:
        """Rejects integrity=False but failed_checks empty."""
        integrity = ReplayIntegrity(
            run_id="int-004",
            envelope_count=10,
            envelope_chain_hash="g" * 64,
            event_loop_states_hash="h" * 64,
            integrity_ok=False,
            failed_checks=[],  # Inconsistent
        )
        with pytest.raises(ReplayDeterminismError, match="Inconsistent"):
            verify_replay_integrity_result(integrity)

    def test_rejects_invalid_hash_format(self) -> None:
        """Rejects result with invalid hash format."""
        integrity = ReplayIntegrity(
            run_id="int-005",
            envelope_count=10,
            envelope_chain_hash="not-a-hash",  # Wrong format
            event_loop_states_hash="i" * 64,
            integrity_ok=True,
            failed_checks=[],
        )
        with pytest.raises(ReplayDeterminismError, match="envelope_chain_hash"):
            verify_replay_integrity_result(integrity)


class TestComputeReplayReportHash:
    """Tests for compute_replay_report_hash."""

    def test_computes_64char_hex_hash(self) -> None:
        """Report hash is 64-character lowercase hex."""
        run_spec = ReplayRunSpec(
            replay_run_id="r1",
            strategy_id="primary_breakout_v1",
            symbol="BTCUSDT",
            start_ts_ms=1000,
            end_ts_ms=2000,
            code_commit="abc123def456",
            run_mode="replay",
        )
        exec_result = ReplayExecutionResult(
            run_id="r1",
            events_processed=1,
            decisions_made=0,
            orders_placed=0,
            fills_recorded=0,
            envelope_hashes=[],
        )
        integrity = ReplayIntegrity(
            run_id="r1",
            envelope_count=0,
            envelope_chain_hash="a" * 64,
            event_loop_states_hash="b" * 64,
            integrity_ok=True,
            failed_checks=[],
        )
        summary = EnvelopeSummary(
            decision_envelopes_total=0,
            order_envelopes_total=0,
            fill_envelopes_total=0,
        )
        manifest = ReplayReportArtifactManifest(
            envelope_log_uri="u1",
            event_loop_states_uri="u2",
            report_artifact_uri="u3",
        )
        report = ReplayReportInput(
            schema_version="replay_report.v1",
            report_type="deterministic_replay",
            strategy_id="primary_breakout_v1",
            run_spec=run_spec,
            execution_result=exec_result,
            replay_integrity=integrity,
            envelope_summary=summary,
            artifact_manifest=manifest,
        )
        h = compute_replay_report_hash(report)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_identical_reports_same_hash(self) -> None:
        """Identical reports produce identical hashes."""
        run_spec = ReplayRunSpec(
            replay_run_id="r2",
            strategy_id="primary_breakout_v1",
            symbol="BTCUSDT",
            start_ts_ms=1000,
            end_ts_ms=2000,
            code_commit="abc123def456",
            run_mode="shadow",
        )
        exec_result = ReplayExecutionResult(
            run_id="r2",
            events_processed=10,
            decisions_made=1,
            orders_placed=0,
            fills_recorded=0,
            envelope_hashes=["c" * 64],
        )
        integrity = ReplayIntegrity(
            run_id="r2",
            envelope_count=1,
            envelope_chain_hash="d" * 64,
            event_loop_states_hash="e" * 64,
            integrity_ok=True,
            failed_checks=[],
        )
        summary = EnvelopeSummary(
            decision_envelopes_total=1,
            order_envelopes_total=0,
            fill_envelopes_total=0,
        )
        manifest = ReplayReportArtifactManifest(
            envelope_log_uri="u1",
            event_loop_states_uri="u2",
            report_artifact_uri="u3",
        )
        report1 = ReplayReportInput(
            schema_version="replay_report.v1",
            report_type="deterministic_replay",
            strategy_id="primary_breakout_v1",
            run_spec=run_spec,
            execution_result=exec_result,
            replay_integrity=integrity,
            envelope_summary=summary,
            artifact_manifest=manifest,
        )
        report2 = ReplayReportInput(
            schema_version="replay_report.v1",
            report_type="deterministic_replay",
            strategy_id="primary_breakout_v1",
            run_spec=run_spec,
            execution_result=exec_result,
            replay_integrity=integrity,
            envelope_summary=summary,
            artifact_manifest=manifest,
        )
        assert compute_replay_report_hash(report1) == compute_replay_report_hash(report2)


@pytest.mark.unit
def test_determinism_error_is_value_error() -> None:
    """ReplayDeterminismError is a ValueError."""
    assert issubclass(ReplayDeterminismError, ValueError)
