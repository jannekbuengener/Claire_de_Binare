"""Deterministic replay contracts and dataclasses.

This module defines the minimal contract surfaces for replay execution,
reporting, and integrity verification. All dataclasses are frozen and
slots-based for deterministic serialization and immutability.

Governance: Issue #1806 (LR-021 Replay Contracts & Determinism)

Design rules:
  - frozen=True, slots=True for all dataclasses
  - to_dict() omits None-valued optional fields (deterministic serialization)
  - Canonical JSON serialization via core.replay.canonical_json
  - No wall-clock time in determinism-critical surfaces
  - Fail-closed contract validation (strict typing, no loose dicts)

relations:
  role: replay_contracts_definition
  domain: replay
  upstream:
    - core.replay.canonical_json
    - core.contracts.decision_contract_v1
    - core.replay.envelopes
  downstream:
    - core.replay.determinism
    - services/validation/ (potential future use)
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Literal


@dataclass(frozen=True, slots=True)
class ReplayRunSpec:
    """Specification for a single replay run.

    Immutable input parameters that define a replay execution.
    """

    replay_run_id: str
    """Unique identifier for this replay run (e.g., 'replay-{hash}')"""

    strategy_id: str
    """Strategy being replayed (e.g., 'primary_breakout_v1')"""

    symbol: str
    """Trading symbol (e.g., 'BTCUSDT')"""

    start_ts_ms: int
    """Replay window start timestamp in milliseconds"""

    end_ts_ms: int
    """Replay window end timestamp in milliseconds"""

    code_commit: str
    """Git commit hash for reproducibility (7..40 hex chars)"""

    run_mode: Literal["shadow", "paper", "replay", "live"]
    """Execution mode context"""

    metadata: Optional[Dict[str, Any]] = None
    """Optional metadata dict for diagnostic/audit purposes"""

    def to_dict(self) -> dict:
        """Convert to dict, omitting None-valued optional fields."""
        result = {
            "replay_run_id": self.replay_run_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "start_ts_ms": self.start_ts_ms,
            "end_ts_ms": self.end_ts_ms,
            "code_commit": self.code_commit,
            "run_mode": self.run_mode,
        }
        if self.metadata is not None:
            result["metadata"] = self.metadata
        return result


@dataclass(frozen=True, slots=True)
class ReplayExecutionRequest:
    """Request to execute a replay segment.

    Combines run specification with event data and context.
    """

    run_spec: ReplayRunSpec
    """Base replay specification"""

    event_batch: List[Dict[str, Any]]
    """Sequence of market/decision events to replay"""

    config_snapshot: Dict[str, Any]
    """Immutable snapshot of strategy configuration at replay time"""

    def to_dict(self) -> dict:
        """Convert to dict."""
        return {
            "run_spec": self.run_spec.to_dict(),
            "event_batch": self.event_batch,
            "config_snapshot": self.config_snapshot,
        }


@dataclass(frozen=True, slots=True)
class ReplayExecutionResult:
    """Result of replaying a batch of events.

    Immutable execution outcome including all generated envelopes.
    """

    run_id: str
    """Replay run identifier from ReplayRunSpec"""

    events_processed: int
    """Number of events successfully processed"""

    decisions_made: int
    """Number of risk decisions emitted"""

    orders_placed: int
    """Number of orders placed during replay"""

    fills_recorded: int
    """Number of fills recorded"""

    envelope_hashes: List[str]
    """SHA256 hashes of each envelope in deterministic order"""

    report_hash: Optional[str] = None
    """Overall replay execution hash (computed after completion)"""

    error_message: Optional[str] = None
    """If execution failed, error description"""

    def to_dict(self) -> dict:
        """Convert to dict, omitting None-valued optional fields."""
        result = {
            "run_id": self.run_id,
            "events_processed": self.events_processed,
            "decisions_made": self.decisions_made,
            "orders_placed": self.orders_placed,
            "fills_recorded": self.fills_recorded,
            "envelope_hashes": self.envelope_hashes,
        }
        if self.report_hash is not None:
            result["report_hash"] = self.report_hash
        if self.error_message is not None:
            result["error_message"] = self.error_message
        return result


@dataclass(frozen=True, slots=True)
class ReplayEventLoopState:
    """State snapshot during replay event loop execution.

    Used for integrity verification and determinism validation.
    """

    event_index: int
    """Current event index in the replay stream"""

    ts_ms: int
    """Event timestamp in milliseconds"""

    event_hash: str
    """Deterministic hash of the event being processed"""

    state_hash: str
    """Cumulative state hash after processing this event"""

    decision_made: bool
    """Whether a risk decision was emitted for this event"""

    order_submitted: bool
    """Whether an order was submitted"""

    metadata: Optional[Dict[str, Any]] = None
    """Optional state metadata for debugging"""

    def to_dict(self) -> dict:
        """Convert to dict, omitting None-valued optional fields."""
        result = {
            "event_index": self.event_index,
            "ts_ms": self.ts_ms,
            "event_hash": self.event_hash,
            "state_hash": self.state_hash,
            "decision_made": self.decision_made,
            "order_submitted": self.order_submitted,
        }
        if self.metadata is not None:
            result["metadata"] = self.metadata
        return result


@dataclass(frozen=True, slots=True)
class ReplayIntegrity:
    """Deterministic integrity check result for a replay run.

    Validates chain consistency and envelope ordering.
    """

    run_id: str
    """Replay run identifier"""

    envelope_count: int
    """Total number of envelopes in the chain"""

    envelope_chain_hash: str
    """Hash of the ordered envelope sequence"""

    event_loop_states_hash: str
    """Hash of all ReplayEventLoopState snapshots"""

    integrity_ok: bool
    """True if all checks passed"""

    failed_checks: tuple[str, ...] = ()
    """Non-empty if integrity_ok is False; tuple of failed check descriptions"""

    def to_dict(self) -> dict:
        """Convert to dict, omitting None-valued optional fields."""
        result = {
            "run_id": self.run_id,
            "envelope_count": self.envelope_count,
            "envelope_chain_hash": self.envelope_chain_hash,
            "event_loop_states_hash": self.event_loop_states_hash,
            "integrity_ok": self.integrity_ok,
        }
        if self.failed_checks:
            result["failed_checks"] = list(self.failed_checks)
        return result


@dataclass(frozen=True, slots=True)
class EnvelopeSummary:
    """Summary of envelope emissions during a replay run.

    Counts and high-level statistics.
    """

    decision_envelopes_total: int
    """Count of DecisionEnvelopeV1 emitted"""

    order_envelopes_total: int
    """Count of OrderEnvelopeV1 emitted"""

    fill_envelopes_total: int
    """Count of FillEnvelopeV1 emitted"""

    first_envelope_ts_ms: Optional[int] = None
    """Timestamp of first envelope (or None if no envelopes)"""

    last_envelope_ts_ms: Optional[int] = None
    """Timestamp of last envelope (or None if no envelopes)"""

    metadata: Optional[Dict[str, Any]] = None
    """Optional metadata (e.g., envelope type distribution)"""

    def to_dict(self) -> dict:
        """Convert to dict, omitting None-valued optional fields."""
        result = {
            "decision_envelopes_total": self.decision_envelopes_total,
            "order_envelopes_total": self.order_envelopes_total,
            "fill_envelopes_total": self.fill_envelopes_total,
        }
        if self.first_envelope_ts_ms is not None:
            result["first_envelope_ts_ms"] = self.first_envelope_ts_ms
        if self.last_envelope_ts_ms is not None:
            result["last_envelope_ts_ms"] = self.last_envelope_ts_ms
        if self.metadata is not None:
            result["metadata"] = self.metadata
        return result


@dataclass(frozen=True, slots=True)
class ReplayReportArtifactManifest:
    """Manifest of artifacts produced by a replay run.

    Documents where replay data is stored and how to retrieve it.
    """

    envelope_log_uri: str
    """URI/path to replay envelope log (JSON Lines or similar)"""

    event_loop_states_uri: str
    """URI/path to event loop state snapshots"""

    report_artifact_uri: str
    """URI/path to the final replay report artifact"""

    supplementary_artifacts: dict[str, str] = field(default_factory=dict)
    """Optional additional artifact URIs (e.g., market snapshots, regime logs)"""

    def to_dict(self) -> dict:
        """Convert to dict, omitting None-valued optional fields."""
        result = {
            "envelope_log_uri": self.envelope_log_uri,
            "event_loop_states_uri": self.event_loop_states_uri,
            "report_artifact_uri": self.report_artifact_uri,
        }
        if self.supplementary_artifacts:
            result["supplementary_artifacts"] = dict(self.supplementary_artifacts)
        return result


@dataclass(frozen=True, slots=True)
class ReplayReportInput:
    """Top-level input for replay report generation.

    Aggregates run spec, execution result, integrity check, and artifact manifest.
    Used to construct the final replay report before schema validation.
    """

    schema_version: str
    """Must be 'replay_report.v1' for V1 replay reports"""

    report_type: Literal["shadow_replay", "deterministic_replay"]
    """Type of replay: shadow (reference) or deterministic (canon)"""

    strategy_id: str
    """Strategy identifier"""

    run_spec: ReplayRunSpec
    """Base run specification"""

    execution_result: ReplayExecutionResult
    """Execution outcome"""

    replay_integrity: ReplayIntegrity
    """Integrity validation result"""

    envelope_summary: EnvelopeSummary
    """Summary of envelope emissions"""

    artifact_manifest: ReplayReportArtifactManifest
    """Artifact locations and URIs"""

    config_snapshot: Optional[Dict[str, Any]] = None
    """Optional strategy config snapshot at replay time"""

    dataset_summary: Optional[Dict[str, Any]] = None
    """Optional market data summary (e.g., symbol, timeframe, candle count)"""

    metrics: Optional[Dict[str, Any]] = None
    """Optional performance metrics (e.g., signals, trades, P&L)"""

    thresholds_applied: Optional[Dict[str, Any]] = None
    """Optional gate thresholds if validation was performed"""

    gate_result: Optional[Dict[str, Any]] = None
    """Optional gate decision (PASS/REVIEW/FAIL) if validation was performed"""

    metadata: Optional[Dict[str, Any]] = None
    """Optional additional metadata for audit/diagnostic purposes"""

    def to_dict(self) -> dict:
        """Convert to dict, omitting None-valued optional fields.

        Uses canonical ordering and deterministic serialization rules.
        Must be compatible with core.replay.canonical_json for hashing.
        """
        result = {
            "schema_version": self.schema_version,
            "report_type": self.report_type,
            "strategy_id": self.strategy_id,
            "run_spec": self.run_spec.to_dict(),
            "execution_result": self.execution_result.to_dict(),
            "replay_integrity": self.replay_integrity.to_dict(),
            "envelope_summary": self.envelope_summary.to_dict(),
            "artifact_manifest": self.artifact_manifest.to_dict(),
        }
        if self.config_snapshot is not None:
            result["config_snapshot"] = self.config_snapshot
        if self.dataset_summary is not None:
            result["dataset_summary"] = self.dataset_summary
        if self.metrics is not None:
            result["metrics"] = self.metrics
        if self.thresholds_applied is not None:
            result["thresholds_applied"] = self.thresholds_applied
        if self.gate_result is not None:
            result["gate_result"] = self.gate_result
        if self.metadata is not None:
            result["metadata"] = self.metadata
        return result
