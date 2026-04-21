"""Deterministic replay reporter: consume replay report inputs, write artifact bundle.

This module is the reporting surface for #1805. It consumes structured
upstream data (ReplayReportInput from #1806 contracts), validates, serializes
deterministically, optionally integrates gate evaluation via delegation, and
writes a minimal artifact bundle.

Governance: Issue #1805 (LR-021 Replay Reporting Slice)

Design rules:
  - Reporter consumes; it does NOT recalculate strategy or execution behavior
  - Deterministic serialization via core.replay.canonical_json
  - No wall-clock time in canonical report fields
  - Optional fields omitted consistently (hash-stable)
  - Fail-closed: validation before I/O; partial bundle cleaned up on write failure
  - Gate evaluation via delegation to GateEvaluator; no gate-logic duplication

Artifact bundle per run (under output_dir/<replay_run_id>/):
  report.json    — canonical replay report (schema: replay_report.v1)
  manifest.json  — bundle digest manifest (bundle_schema_version: replay_bundle.v1)
  audit.log      — reporter warnings/errors (may be empty; always written)

relations:
  role: replay_reporting_surface
  domain: validation
  upstream:
    - core.replay.replay_contracts (ReplayReportInput and related dataclasses)
    - core.replay.canonical_json   (deterministic serialization)
    - core.replay.determinism      (execution/integrity validation helpers)
    - services.validation.gate_evaluator (GateEvaluator, optional delegation)
    - docs/contracts/replay_report.v1.schema.json
  downstream:
    - CLI (#1804, future)
    - replay orchestration layers (future)
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Dict, List, Optional

import jsonschema

from core.replay.canonical_json import canonical_json_dumps
from core.replay.determinism import (
    compute_replay_report_hash,
    verify_replay_execution_result,
    verify_replay_integrity_result,
    ReplayDeterminismError,
)
from core.replay.replay_contracts import ReplayReportInput
from services.validation.gate_evaluator import GateEvaluator

_BUNDLE_SCHEMA_VERSION = "replay_bundle.v1"
_SCHEMA_PATH = (
    pathlib.Path(__file__).parent.parent.parent
    / "docs"
    / "contracts"
    / "replay_report.v1.schema.json"
)

# Wall-clock keys injected by GateEvaluator that must be stripped before
# writing to canonical report fields.
_GATE_RESULT_WALL_CLOCK_KEYS = frozenset({"timestamp"})


class ReplayReporterError(ValueError):
    """Raised when the replay reporter cannot produce a valid artifact bundle.

    Covers: invalid inputs, schema validation failures, write failures.
    """


def _load_replay_report_schema() -> dict:
    """Load replay_report.v1 JSON schema from docs/contracts/."""
    try:
        with _SCHEMA_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise ReplayReporterError(
            f"Cannot load replay report schema from {_SCHEMA_PATH}: {exc}"
        ) from exc


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strip_wall_clock(gate_result: Dict[str, Any]) -> Dict[str, Any]:
    """Remove wall-clock fields from a gate evaluator result dict.

    GateEvaluator.evaluate() injects a 'timestamp' field that must be
    excluded from canonical report fields to preserve deterministic hashing.
    """
    return {k: v for k, v in gate_result.items() if k not in _GATE_RESULT_WALL_CLOCK_KEYS}


class ReplayReporter:
    """Builds and writes a deterministic replay artifact bundle.

    Accepts a ReplayReportInput (from core.replay.replay_contracts), validates
    required sub-contracts, optionally evaluates gate criteria via a delegated
    GateEvaluator, schema-validates the final report, and writes a minimal
    artifact bundle.

    Usage::

        reporter = ReplayReporter()
        bundle_path = reporter.write_bundle(
            report_input,
            output_dir=pathlib.Path("artifacts/replay_reports"),
        )

    Gate evaluation is opt-in::

        from services.validation.gate_evaluator import GateEvaluator, GateThresholds
        evaluator = GateEvaluator(GateThresholds(min_orders=5, min_fill_rate=0.45, min_qty_sum=0.0))
        reporter = ReplayReporter(gate_evaluator=evaluator)

    Design invariants:
      - ``report_input`` is never mutated
      - ``build_report_dict`` performs all validation; I/O only in ``write_bundle``
      - Writes are fail-closed: partial files cleaned up on error
    """

    def __init__(
        self,
        gate_evaluator: Optional[GateEvaluator] = None,
        schema: Optional[dict] = None,
    ) -> None:
        self._gate_evaluator = gate_evaluator
        self._schema = schema if schema is not None else _load_replay_report_schema()

    def build_report_dict(
        self,
        report_input: ReplayReportInput,
        audit_log: List[str],
    ) -> dict:
        """Build and validate the canonical report dict from report_input.

        Optionally evaluates gate result if metrics are present and a
        gate_evaluator is configured. Does NOT mutate report_input; returns
        a new dict that may include an injected gate_result.

        Args:
            report_input: Validated ReplayReportInput instance.
            audit_log: Mutable list; WARNING/ERROR/INFO entries appended here.

        Returns:
            Fully validated report dict ready for canonical serialization.

        Raises:
            ReplayReporterError on missing required fields, invalid sub-contracts,
            or schema validation failure.
        """
        if not isinstance(report_input, ReplayReportInput):
            raise ReplayReporterError(
                f"Expected ReplayReportInput, got {type(report_input).__name__}"
            )

        if report_input.schema_version != "replay_report.v1":
            raise ReplayReporterError(
                f"Expected schema_version='replay_report.v1', "
                f"got {report_input.schema_version!r}"
            )

        # Validate required sub-contracts (fail-closed).
        try:
            verify_replay_execution_result(report_input.execution_result)
        except ReplayDeterminismError as exc:
            audit_log.append(f"ERROR: execution_result validation failed: {exc}")
            raise ReplayReporterError(
                f"execution_result invalid: {exc}"
            ) from exc

        try:
            verify_replay_integrity_result(report_input.replay_integrity)
        except ReplayDeterminismError as exc:
            audit_log.append(f"ERROR: replay_integrity validation failed: {exc}")
            raise ReplayReporterError(
                f"replay_integrity invalid: {exc}"
            ) from exc

        # Build report dict from input (omits None-valued optional fields).
        report_dict = report_input.to_dict()

        # Gate evaluation via delegation — never duplicate threshold logic.
        if report_input.gate_result is None and self._gate_evaluator is not None:
            if report_input.metrics is not None:
                try:
                    raw_gate = self._gate_evaluator.evaluate(report_input.metrics)
                    # Strip wall-clock timestamp to preserve deterministic hashing.
                    report_dict["gate_result"] = _strip_wall_clock(raw_gate)
                    overall = report_dict["gate_result"].get("overall_pass")
                    audit_log.append(
                        f"INFO: Gate evaluation completed: overall_pass={overall}"
                    )
                except Exception as exc:  # pragma: no cover — defensive path
                    audit_log.append(
                        f"WARNING: Gate evaluation failed (non-blocking): {exc}"
                    )
            else:
                audit_log.append(
                    "INFO: Gate evaluation skipped (no metrics in report_input)"
                )
        elif report_input.gate_result is not None:
            audit_log.append(
                "INFO: Gate result already present in report_input; evaluation skipped"
            )
            # Normalize gate_result regardless of source to preserve canonical
            # determinism and exclude wall-clock fields from report content.
            if "gate_result" in report_dict:
                report_dict["gate_result"] = _strip_wall_clock(report_dict["gate_result"])
        else:
            audit_log.append(
                "INFO: Gate evaluation skipped (no gate_evaluator configured)"
            )

        # Schema validation (fail-closed before any I/O).
        try:
            jsonschema.validate(instance=report_dict, schema=self._schema)
        except jsonschema.ValidationError as exc:
            audit_log.append(f"ERROR: Schema validation failed: {exc.message}")
            raise ReplayReporterError(
                f"Report failed schema validation: {exc.message}"
            ) from exc

        run_id = report_input.run_spec.replay_run_id
        audit_log.append(f"INFO: Schema validation passed for run_id={run_id}")
        return report_dict

    def write_bundle(
        self,
        report_input: ReplayReportInput,
        output_dir: pathlib.Path,
    ) -> pathlib.Path:
        """Build and write the artifact bundle under output_dir/<replay_run_id>/.

        Bundle contents:
          report.json   — canonical replay report (deterministic)
          manifest.json — bundle digests (report_json_sha256, audit_log_sha256)
          audit.log     — reporter log entries (may be empty; always written)

        All validation and content generation happens before any I/O. If a
        write fails mid-bundle, already-written files are cleaned up and
        ReplayReporterError is raised — the caller will not see a partial bundle
        reported as success.

        Args:
            report_input: Validated ReplayReportInput instance.
            output_dir: Root directory for replay report bundles.

        Returns:
            Path to the written bundle directory.

        Raises:
            ReplayReporterError on validation failure or write failure.
        """
        audit_log: List[str] = []
        run_id = report_input.run_spec.replay_run_id
        audit_log.append(f"INFO: Replay reporter started for run_id={run_id}")

        # Phase 1: build and validate all content in memory (no I/O yet).
        report_dict = self.build_report_dict(report_input, audit_log)

        report_json_bytes = canonical_json_dumps(report_dict).encode("utf-8")
        report_sha256 = _sha256_bytes(report_json_bytes)
        audit_log.append(f"INFO: report.json sha256={report_sha256}")

        # Build audit log content now (after all log entries are appended).
        audit_log_content = "\n".join(audit_log) + "\n"
        audit_log_bytes = audit_log_content.encode("utf-8")
        audit_sha256 = _sha256_bytes(audit_log_bytes)

        # Manifest: deterministic, no wall-clock time.
        manifest: Dict[str, Any] = {
            "bundle_schema_version": _BUNDLE_SCHEMA_VERSION,
            "replay_run_id": run_id,
            "strategy_id": report_input.strategy_id,
            "report_json_sha256": report_sha256,
            "audit_log_sha256": audit_sha256,
        }
        manifest_json_bytes = canonical_json_dumps(manifest).encode("utf-8")

        # Phase 2: write bundle (fail-closed, cleanup on partial failure).
        bundle_dir = pathlib.Path(output_dir) / run_id
        written: List[pathlib.Path] = []
        try:
            bundle_dir.mkdir(parents=True, exist_ok=True)

            report_path = bundle_dir / "report.json"
            report_path.write_bytes(report_json_bytes)
            written.append(report_path)

            manifest_path = bundle_dir / "manifest.json"
            manifest_path.write_bytes(manifest_json_bytes)
            written.append(manifest_path)

            audit_path = bundle_dir / "audit.log"
            audit_path.write_bytes(audit_log_bytes)
            written.append(audit_path)

        except OSError as exc:
            for f in written:
                try:
                    f.unlink(missing_ok=True)
                except OSError:
                    pass
            raise ReplayReporterError(
                f"Failed to write artifact bundle to {bundle_dir}: {exc}"
            ) from exc

        return bundle_dir
