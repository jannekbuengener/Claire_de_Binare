"""Unit tests for replay_contracts dataclasses.

Scope:
  - Dataclass instantiation and validation
  - to_dict() serialization (None-omission)
  - Canonical JSON compatibility
  - Type checking and field presence
"""

import pytest
from core.replay.canonical_json import canonical_hash
from core.replay.replay_contracts import (
    ReplayRunSpec,
    ReplayExecutionResult,
    ReplayIntegrity,
    EnvelopeSummary,
    ReplayReportArtifactManifest,
    ReplayReportInput,
)


class TestReplayRunSpec:
    """Tests for ReplayRunSpec."""

    def test_create_minimal(self) -> None:
        """Create ReplayRunSpec with required fields only."""
        spec = ReplayRunSpec(
            replay_run_id="replay-abc123",
            strategy_id="primary_breakout_v1",
            symbol="BTCUSDT",
            start_ts_ms=1000000,
            end_ts_ms=2000000,
            code_commit="abc123def456",
            run_mode="shadow",
        )
        assert spec.replay_run_id == "replay-abc123"
        assert spec.metadata is None

    def test_create_with_metadata(self) -> None:
        """Create ReplayRunSpec with optional metadata."""
        meta = {"source": "test"}
        spec = ReplayRunSpec(
            replay_run_id="replay-xyz",
            strategy_id="primary_breakout_v1",
            symbol="BTCUSDT",
            start_ts_ms=1000000,
            end_ts_ms=2000000,
            code_commit="abc123def456",
            run_mode="replay",
            metadata=meta,
        )
        assert spec.metadata == meta

    def test_to_dict_omits_none(self) -> None:
        """to_dict() omits None-valued optional fields."""
        spec = ReplayRunSpec(
            replay_run_id="replay-1",
            strategy_id="primary_breakout_v1",
            symbol="BTCUSDT",
            start_ts_ms=1000000,
            end_ts_ms=2000000,
            code_commit="abc123def456",
            run_mode="replay",
        )
        d = spec.to_dict()
        assert "replay_run_id" in d
        assert "metadata" not in d  # None is omitted

    def test_to_dict_includes_metadata(self) -> None:
        """to_dict() includes metadata when set."""
        spec = ReplayRunSpec(
            replay_run_id="replay-2",
            strategy_id="primary_breakout_v1",
            symbol="BTCUSDT",
            start_ts_ms=1000000,
            end_ts_ms=2000000,
            code_commit="abc123def456",
            run_mode="paper",
            metadata={"key": "value"},
        )
        d = spec.to_dict()
        assert d["metadata"] == {"key": "value"}

    def test_frozen_immutable(self) -> None:
        """ReplayRunSpec is frozen and immutable."""
        spec = ReplayRunSpec(
            replay_run_id="replay-3",
            strategy_id="primary_breakout_v1",
            symbol="BTCUSDT",
            start_ts_ms=1000000,
            end_ts_ms=2000000,
            code_commit="abc123def456",
            run_mode="live",
        )
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            spec.replay_run_id = "new-value"  # type: ignore


class TestReplayExecutionResult:
    """Tests for ReplayExecutionResult."""

    def test_create_minimal(self) -> None:
        """Create ReplayExecutionResult with required fields."""
        result = ReplayExecutionResult(
            run_id="replay-run-1",
            events_processed=100,
            decisions_made=10,
            orders_placed=5,
            fills_recorded=4,
            envelope_hashes=["a" * 64, "b" * 64],
        )
        assert result.run_id == "replay-run-1"
        assert result.events_processed == 100
        assert result.report_hash is None
        assert result.error_message is None

    def test_to_dict_omits_optional_none(self) -> None:
        """to_dict() omits None-valued optional fields."""
        result = ReplayExecutionResult(
            run_id="run-2",
            events_processed=50,
            decisions_made=5,
            orders_placed=2,
            fills_recorded=2,
            envelope_hashes=["c" * 64],
        )
        d = result.to_dict()
        assert "report_hash" not in d
        assert "error_message" not in d

    def test_to_dict_includes_optional_when_set(self) -> None:
        """to_dict() includes optional fields when set."""
        result = ReplayExecutionResult(
            run_id="run-3",
            events_processed=10,
            decisions_made=1,
            orders_placed=0,
            fills_recorded=0,
            envelope_hashes=["d" * 64],
            report_hash="e" * 64,
            error_message="Test error",
        )
        d = result.to_dict()
        assert d["report_hash"] == "e" * 64
        assert d["error_message"] == "Test error"

    def test_deterministic_hash_consistency(self) -> None:
        """Multiple identical results produce identical hashes."""
        result1 = ReplayExecutionResult(
            run_id="run-4",
            events_processed=100,
            decisions_made=10,
            orders_placed=5,
            fills_recorded=4,
            envelope_hashes=["f" * 64, "g" * 64],
        )
        result2 = ReplayExecutionResult(
            run_id="run-4",
            events_processed=100,
            decisions_made=10,
            orders_placed=5,
            fills_recorded=4,
            envelope_hashes=["f" * 64, "g" * 64],
        )
        hash1 = canonical_hash(result1.to_dict())
        hash2 = canonical_hash(result2.to_dict())
        assert hash1 == hash2


class TestReplayIntegrity:
    """Tests for ReplayIntegrity."""

    def test_create_ok(self) -> None:
        """Create ReplayIntegrity with integrity_ok=True."""
        integrity = ReplayIntegrity(
            run_id="run-5",
            envelope_count=10,
            envelope_chain_hash="a" * 64,
            event_loop_states_hash="b" * 64,
            integrity_ok=True,
            failed_checks=[],
        )
        assert integrity.integrity_ok is True
        assert len(integrity.failed_checks) == 0

    def test_create_with_failures(self) -> None:
        """Create ReplayIntegrity with integrity_ok=False and failures."""
        integrity = ReplayIntegrity(
            run_id="run-6",
            envelope_count=10,
            envelope_chain_hash="c" * 64,
            event_loop_states_hash="d" * 64,
            integrity_ok=False,
            failed_checks=["timestamp_violation", "duplicate_event_id"],
        )
        assert integrity.integrity_ok is False
        assert len(integrity.failed_checks) == 2

    def test_to_dict_omits_empty_failed_checks(self) -> None:
        """to_dict() omits failed_checks if empty."""
        integrity = ReplayIntegrity(
            run_id="run-7",
            envelope_count=5,
            envelope_chain_hash="e" * 64,
            event_loop_states_hash="f" * 64,
            integrity_ok=True,
            failed_checks=[],
        )
        d = integrity.to_dict()
        assert "failed_checks" not in d

    def test_to_dict_includes_failed_checks(self) -> None:
        """to_dict() includes failed_checks if non-empty."""
        integrity = ReplayIntegrity(
            run_id="run-8",
            envelope_count=5,
            envelope_chain_hash="g" * 64,
            event_loop_states_hash="h" * 64,
            integrity_ok=False,
            failed_checks=["check_1", "check_2"],
        )
        d = integrity.to_dict()
        assert d["failed_checks"] == ["check_1", "check_2"]


class TestEnvelopeSummary:
    """Tests for EnvelopeSummary."""

    def test_create_minimal(self) -> None:
        """Create EnvelopeSummary with counts only."""
        summary = EnvelopeSummary(
            decision_envelopes_total=10,
            order_envelopes_total=5,
            fill_envelopes_total=4,
        )
        assert summary.decision_envelopes_total == 10
        assert summary.first_envelope_ts_ms is None

    def test_to_dict_omits_optional_timestamps(self) -> None:
        """to_dict() omits optional timestamp fields when None."""
        summary = EnvelopeSummary(
            decision_envelopes_total=8,
            order_envelopes_total=3,
            fill_envelopes_total=2,
        )
        d = summary.to_dict()
        assert "first_envelope_ts_ms" not in d
        assert "last_envelope_ts_ms" not in d

    def test_to_dict_includes_timestamps(self) -> None:
        """to_dict() includes timestamps when set."""
        summary = EnvelopeSummary(
            decision_envelopes_total=6,
            order_envelopes_total=2,
            fill_envelopes_total=1,
            first_envelope_ts_ms=1000000,
            last_envelope_ts_ms=2000000,
        )
        d = summary.to_dict()
        assert d["first_envelope_ts_ms"] == 1000000
        assert d["last_envelope_ts_ms"] == 2000000


class TestReplayReportArtifactManifest:
    """Tests for ReplayReportArtifactManifest."""

    def test_create_required_fields(self) -> None:
        """Create manifest with required URIs."""
        manifest = ReplayReportArtifactManifest(
            envelope_log_uri="/path/to/envelopes.jsonl",
            event_loop_states_uri="/path/to/states.jsonl",
            report_artifact_uri="/path/to/report.json",
        )
        assert manifest.envelope_log_uri == "/path/to/envelopes.jsonl"
        assert len(manifest.supplementary_artifacts) == 0

    def test_to_dict_omits_empty_supplementary(self) -> None:
        """to_dict() omits supplementary_artifacts if empty."""
        manifest = ReplayReportArtifactManifest(
            envelope_log_uri="uri1",
            event_loop_states_uri="uri2",
            report_artifact_uri="uri3",
        )
        d = manifest.to_dict()
        assert "supplementary_artifacts" not in d

    def test_to_dict_includes_supplementary(self) -> None:
        """to_dict() includes supplementary_artifacts when non-empty."""
        supp = {"market_snapshots": "uri4", "regime_log": "uri5"}
        manifest = ReplayReportArtifactManifest(
            envelope_log_uri="uri1",
            event_loop_states_uri="uri2",
            report_artifact_uri="uri3",
            supplementary_artifacts=supp,
        )
        d = manifest.to_dict()
        assert d["supplementary_artifacts"] == supp


class TestReplayReportInput:
    """Tests for ReplayReportInput (top-level report input)."""

    def test_create_minimal_required_only(self) -> None:
        """Create ReplayReportInput with all required fields."""
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
            events_processed=100,
            decisions_made=10,
            orders_placed=5,
            fills_recorded=4,
            envelope_hashes=["a" * 64],
        )
        integrity = ReplayIntegrity(
            run_id="r1",
            envelope_count=1,
            envelope_chain_hash="b" * 64,
            event_loop_states_hash="c" * 64,
            integrity_ok=True,
            failed_checks=[],
        )
        summary = EnvelopeSummary(
            decision_envelopes_total=10,
            order_envelopes_total=5,
            fill_envelopes_total=4,
        )
        manifest = ReplayReportArtifactManifest(
            envelope_log_uri="uri1",
            event_loop_states_uri="uri2",
            report_artifact_uri="uri3",
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
        assert report.schema_version == "replay_report.v1"
        assert report.config_snapshot is None

    def test_to_dict_omits_optional_sections(self) -> None:
        """to_dict() omits optional report sections when None."""
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
            events_processed=50,
            decisions_made=5,
            orders_placed=2,
            fills_recorded=2,
            envelope_hashes=["d" * 64],
        )
        integrity = ReplayIntegrity(
            run_id="r2",
            envelope_count=1,
            envelope_chain_hash="e" * 64,
            event_loop_states_hash="f" * 64,
            integrity_ok=True,
            failed_checks=[],
        )
        summary = EnvelopeSummary(
            decision_envelopes_total=5,
            order_envelopes_total=2,
            fill_envelopes_total=2,
        )
        manifest = ReplayReportArtifactManifest(
            envelope_log_uri="u1",
            event_loop_states_uri="u2",
            report_artifact_uri="u3",
        )
        report = ReplayReportInput(
            schema_version="replay_report.v1",
            report_type="shadow_replay",
            strategy_id="primary_breakout_v1",
            run_spec=run_spec,
            execution_result=exec_result,
            replay_integrity=integrity,
            envelope_summary=summary,
            artifact_manifest=manifest,
        )
        d = report.to_dict()
        assert "config_snapshot" not in d
        assert "metrics" not in d
        assert "gate_result" not in d

    def test_to_dict_includes_optional_when_set(self) -> None:
        """to_dict() includes optional sections when set."""
        run_spec = ReplayRunSpec(
            replay_run_id="r3",
            strategy_id="primary_breakout_v1",
            symbol="BTCUSDT",
            start_ts_ms=1000,
            end_ts_ms=2000,
            code_commit="abc123def456",
            run_mode="replay",
        )
        exec_result = ReplayExecutionResult(
            run_id="r3",
            events_processed=100,
            decisions_made=10,
            orders_placed=5,
            fills_recorded=4,
            envelope_hashes=["g" * 64],
        )
        integrity = ReplayIntegrity(
            run_id="r3",
            envelope_count=1,
            envelope_chain_hash="h" * 64,
            event_loop_states_hash="i" * 64,
            integrity_ok=True,
            failed_checks=[],
        )
        summary = EnvelopeSummary(
            decision_envelopes_total=10,
            order_envelopes_total=5,
            fill_envelopes_total=4,
        )
        manifest = ReplayReportArtifactManifest(
            envelope_log_uri="u1",
            event_loop_states_uri="u2",
            report_artifact_uri="u3",
        )
        config = {"entry_lookback_minutes": 240}
        metrics = {"signals_total": 50}
        report = ReplayReportInput(
            schema_version="replay_report.v1",
            report_type="deterministic_replay",
            strategy_id="primary_breakout_v1",
            run_spec=run_spec,
            execution_result=exec_result,
            replay_integrity=integrity,
            envelope_summary=summary,
            artifact_manifest=manifest,
            config_snapshot=config,
            metrics=metrics,
        )
        d = report.to_dict()
        assert d["config_snapshot"] == config
        assert d["metrics"] == metrics


@pytest.mark.unit
def test_schema_version_constant() -> None:
    """schema_version must be 'replay_report.v1' for V1."""
    run_spec = ReplayRunSpec(
        replay_run_id="test",
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        start_ts_ms=1000,
        end_ts_ms=2000,
        code_commit="abc123def456",
        run_mode="replay",
    )
    exec_result = ReplayExecutionResult(
        run_id="test",
        events_processed=1,
        decisions_made=0,
        orders_placed=0,
        fills_recorded=0,
        envelope_hashes=[],
    )
    integrity = ReplayIntegrity(
        run_id="test",
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
    assert report.schema_version == "replay_report.v1"
