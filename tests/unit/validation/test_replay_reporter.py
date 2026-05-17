"""Unit tests for services/validation/replay_reporter.py.

Scope (Issue #1805):
  - Deterministic hashing: identical inputs → identical canonical report.json SHA-256
  - Optional field omission is hash-stable
  - Required fields fail-closed (ReplayReporterError raised before I/O)
  - Schema validation: valid report passes; malformed report fails
  - Artifact bundle: report.json, manifest.json, audit.log written
  - manifest.json contains correct SHA-256 digests
  - audit.log always written (even empty-ish)
  - Gate result delegation via GateEvaluator (not duplicated)
  - Gate result already present → evaluator not called again
  - No wall-clock time in canonical report fields
  - Partial bundle cleanup on write failure
  - No silent recalculation of strategy/execution results
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import jsonschema
import pytest

from core.replay.canonical_json import canonical_json_dumps
from core.replay.replay_contracts import (
    EnvelopeSummary,
    ReplayExecutionResult,
    ReplayIntegrity,
    ReplayReportArtifactManifest,
    ReplayReportInput,
    ReplayRunSpec,
)
from services.validation.gate_evaluator import GateEvaluator, GateThresholds
from services.validation.replay_reporter import (
    ReplayReporter,
    ReplayReporterError,
    _strip_wall_clock,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_VALID_RUN_ID = "replay-test-abc123def456"
_VALID_COMMIT = "abc123def456"


def _make_run_spec(**overrides: Any) -> ReplayRunSpec:
    defaults: Dict[str, Any] = dict(
        replay_run_id=_VALID_RUN_ID,
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        start_ts_ms=1_000_000,
        end_ts_ms=2_000_000,
        code_commit=_VALID_COMMIT,
        run_mode="shadow",
    )
    defaults.update(overrides)
    return ReplayRunSpec(**defaults)


def _make_exec_result(**overrides: Any) -> ReplayExecutionResult:
    defaults: Dict[str, Any] = dict(
        run_id=_VALID_RUN_ID,
        events_processed=50,
        decisions_made=10,
        orders_placed=5,
        fills_recorded=4,
        envelope_hashes=["a" * 64, "b" * 64],
    )
    defaults.update(overrides)
    return ReplayExecutionResult(**defaults)


def _make_integrity(**overrides: Any) -> ReplayIntegrity:
    defaults: Dict[str, Any] = dict(
        run_id=_VALID_RUN_ID,
        envelope_count=2,
        envelope_chain_hash="c" * 64,
        event_loop_states_hash="d" * 64,
        integrity_ok=True,
        failed_checks=[],
    )
    defaults.update(overrides)
    return ReplayIntegrity(**defaults)


def _make_summary(**overrides: Any) -> EnvelopeSummary:
    defaults: Dict[str, Any] = dict(
        decision_envelopes_total=10,
        order_envelopes_total=5,
        fill_envelopes_total=4,
    )
    defaults.update(overrides)
    return EnvelopeSummary(**defaults)


def _make_manifest(**overrides: Any) -> ReplayReportArtifactManifest:
    defaults: Dict[str, Any] = dict(
        envelope_log_uri="/data/replay/envelopes.jsonl",
        event_loop_states_uri="/data/replay/states.jsonl",
        report_artifact_uri="/data/replay/report.json",
    )
    defaults.update(overrides)
    return ReplayReportArtifactManifest(**defaults)


def _make_valid_report_input(**overrides: Any) -> ReplayReportInput:
    defaults: Dict[str, Any] = dict(
        schema_version="replay_report.v1",
        report_type="shadow_replay",
        strategy_id="primary_breakout_v1",
        run_spec=_make_run_spec(),
        execution_result=_make_exec_result(),
        replay_integrity=_make_integrity(),
        envelope_summary=_make_summary(),
        artifact_manifest=_make_manifest(),
    )
    defaults.update(overrides)
    return ReplayReportInput(**defaults)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# _strip_wall_clock helper
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStripWallClock:
    def test_removes_timestamp_key(self) -> None:
        d = {"overall_pass": True, "timestamp": "2026-01-01T00:00:00", "x": 1}
        result = _strip_wall_clock(d)
        assert "timestamp" not in result
        assert result["overall_pass"] is True
        assert result["x"] == 1

    def test_no_timestamp_unchanged(self) -> None:
        d = {"overall_pass": False, "reason": "failed"}
        assert _strip_wall_clock(d) == d


# ---------------------------------------------------------------------------
# ReplayReporter.build_report_dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildReportDict:
    def test_valid_input_returns_dict(self) -> None:
        reporter = ReplayReporter()
        report_input = _make_valid_report_input()
        audit: list = []
        result = reporter.build_report_dict(report_input, audit)
        assert result["schema_version"] == "replay_report.v1"
        assert result["strategy_id"] == "primary_breakout_v1"

    def test_wrong_type_raises(self) -> None:
        reporter = ReplayReporter()
        with pytest.raises(ReplayReporterError, match="Expected ReplayReportInput"):
            reporter.build_report_dict({"schema_version": "replay_report.v1"}, [])  # type: ignore

    def test_wrong_schema_version_raises(self) -> None:
        reporter = ReplayReporter()
        report_input = _make_valid_report_input(schema_version="replay_report.v2")
        with pytest.raises(ReplayReporterError, match="schema_version"):
            reporter.build_report_dict(report_input, [])

    def test_invalid_execution_result_raises(self) -> None:
        reporter = ReplayReporter()
        bad_exec = _make_exec_result(run_id="")  # empty run_id
        report_input = _make_valid_report_input(execution_result=bad_exec)
        audit: list = []
        with pytest.raises(ReplayReporterError, match="execution_result"):
            reporter.build_report_dict(report_input, audit)
        assert any("ERROR" in e for e in audit)

    def test_invalid_integrity_raises(self) -> None:
        reporter = ReplayReporter()
        # integrity_ok=False but failed_checks=[] → inconsistent
        bad_integrity = _make_integrity(integrity_ok=False, failed_checks=[])
        report_input = _make_valid_report_input(replay_integrity=bad_integrity)
        audit: list = []
        with pytest.raises(ReplayReporterError, match="replay_integrity"):
            reporter.build_report_dict(report_input, audit)
        assert any("ERROR" in e for e in audit)

    def test_schema_validation_fails_for_malformed_report(self) -> None:
        """Malformed report (extra unknown field) fails schema validation."""
        reporter = ReplayReporter()
        report_input = _make_valid_report_input()
        audit: list = []
        report_dict = reporter.build_report_dict(report_input, audit)
        # Inject a field not in schema to make it fail additionalProperties=false
        report_dict["unknown_field_xyz"] = "bad"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=report_dict, schema=reporter._schema)

    def test_audit_log_contains_schema_pass_entry(self) -> None:
        reporter = ReplayReporter()
        audit: list = []
        reporter.build_report_dict(_make_valid_report_input(), audit)
        assert any("Schema validation passed" in e for e in audit)

    def test_audit_log_has_gate_skip_entry_when_no_evaluator(self) -> None:
        reporter = ReplayReporter(gate_evaluator=None)
        audit: list = []
        reporter.build_report_dict(_make_valid_report_input(), audit)
        assert any("Gate evaluation skipped" in e for e in audit)

    def test_optional_fields_absent_in_output(self) -> None:
        """Optional fields absent in input are also absent in output dict."""
        reporter = ReplayReporter()
        report_input = _make_valid_report_input()
        audit: list = []
        result = reporter.build_report_dict(report_input, audit)
        for optional_key in ("config_snapshot", "dataset_summary", "metrics", "thresholds_applied", "gate_result", "metadata"):
            assert optional_key not in result, f"Expected {optional_key!r} absent"


# ---------------------------------------------------------------------------
# Determinism: identical inputs → identical hash
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeterminism:
    def test_identical_inputs_produce_identical_canonical_json(self) -> None:
        reporter = ReplayReporter()
        ri1 = _make_valid_report_input()
        ri2 = _make_valid_report_input()
        audit1: list = []
        audit2: list = []
        d1 = reporter.build_report_dict(ri1, audit1)
        d2 = reporter.build_report_dict(ri2, audit2)
        json1 = canonical_json_dumps(d1)
        json2 = canonical_json_dumps(d2)
        assert json1 == json2

    def test_identical_inputs_produce_identical_sha256(self) -> None:
        reporter = ReplayReporter()
        ri1 = _make_valid_report_input()
        ri2 = _make_valid_report_input()
        d1 = reporter.build_report_dict(ri1, [])
        d2 = reporter.build_report_dict(ri2, [])
        h1 = _sha256(canonical_json_dumps(d1).encode("utf-8"))
        h2 = _sha256(canonical_json_dumps(d2).encode("utf-8"))
        assert h1 == h2
        assert len(h1) == 64

    def test_optional_fields_omitted_both_runs_hash_stable(self) -> None:
        """Two runs omitting the same optional fields produce the same hash."""
        reporter = ReplayReporter()
        ri = _make_valid_report_input()  # no optional fields
        d1 = reporter.build_report_dict(ri, [])
        d2 = reporter.build_report_dict(ri, [])
        h1 = _sha256(canonical_json_dumps(d1).encode("utf-8"))
        h2 = _sha256(canonical_json_dumps(d2).encode("utf-8"))
        assert h1 == h2

    def test_different_run_ids_produce_different_hashes(self) -> None:
        reporter = ReplayReporter()
        ri1 = _make_valid_report_input(run_spec=_make_run_spec(replay_run_id="replay-aaa"))
        ri2 = _make_valid_report_input(
            run_spec=_make_run_spec(replay_run_id="replay-bbb"),
            execution_result=_make_exec_result(run_id="replay-bbb"),
            replay_integrity=_make_integrity(run_id="replay-bbb"),
        )
        d1 = reporter.build_report_dict(ri1, [])
        d2 = reporter.build_report_dict(ri2, [])
        h1 = _sha256(canonical_json_dumps(d1).encode("utf-8"))
        h2 = _sha256(canonical_json_dumps(d2).encode("utf-8"))
        assert h1 != h2

    def test_no_wall_clock_in_report_dict_fields(self) -> None:
        """Canonical report dict contains no timestamp fields derived from wall-clock."""
        reporter = ReplayReporter()
        d = reporter.build_report_dict(_make_valid_report_input(), [])
        # gate_result should not be present when no gate_evaluator and no gate_result in input
        assert "gate_result" not in d
        # The report should not contain "timestamp" anywhere at top level
        assert "timestamp" not in d


# ---------------------------------------------------------------------------
# Gate evaluation delegation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGateDelegation:
    def _make_evaluator(self) -> GateEvaluator:
        return GateEvaluator(
            GateThresholds(min_orders=1, min_fill_rate=0.0, min_qty_sum=0.0)
        )

    def test_gate_evaluated_when_metrics_present(self) -> None:
        evaluator = self._make_evaluator()
        reporter = ReplayReporter(gate_evaluator=evaluator)
        metrics = {"orders_total": 5, "filled_total": 4, "qty_sum": 2.0}
        report_input = _make_valid_report_input(metrics=metrics)
        audit: list = []
        result = reporter.build_report_dict(report_input, audit)
        assert "gate_result" in result
        assert "overall_pass" in result["gate_result"]
        assert any("Gate evaluation completed" in e for e in audit)

    def test_gate_result_has_no_timestamp(self) -> None:
        """Wall-clock timestamp stripped from gate result before inclusion."""
        evaluator = self._make_evaluator()
        reporter = ReplayReporter(gate_evaluator=evaluator)
        metrics = {"orders_total": 3, "filled_total": 2, "qty_sum": 1.0}
        report_input = _make_valid_report_input(metrics=metrics)
        result = reporter.build_report_dict(report_input, [])
        assert "timestamp" not in result.get("gate_result", {})

    def test_gate_skipped_when_no_metrics(self) -> None:
        evaluator = self._make_evaluator()
        reporter = ReplayReporter(gate_evaluator=evaluator)
        report_input = _make_valid_report_input()  # no metrics
        audit: list = []
        result = reporter.build_report_dict(report_input, audit)
        assert "gate_result" not in result
        assert any("no metrics" in e for e in audit)

    def test_gate_not_re_evaluated_when_already_set(self) -> None:
        """If gate_result is already in report_input, evaluator is NOT called."""
        evaluator = MagicMock(spec=GateEvaluator)
        reporter = ReplayReporter(gate_evaluator=evaluator)
        preset_gate = {"overall_pass": True, "reason": "preset"}
        metrics = {"orders_total": 5, "filled_total": 5, "qty_sum": 1.0}
        report_input = _make_valid_report_input(
            metrics=metrics,
            gate_result=preset_gate,
        )
        audit: list = []
        result = reporter.build_report_dict(report_input, audit)
        evaluator.evaluate.assert_not_called()
        assert result["gate_result"] == preset_gate
        assert any("already present" in e for e in audit)

    def test_gate_pass_and_fail_results_map_correctly(self) -> None:
        evaluator = GateEvaluator(
            GateThresholds(min_orders=100, min_fill_rate=0.9, min_qty_sum=999.0)
        )
        reporter = ReplayReporter(gate_evaluator=evaluator)
        metrics = {"orders_total": 1, "filled_total": 0, "qty_sum": 0.0}
        report_input = _make_valid_report_input(metrics=metrics)
        result = reporter.build_report_dict(report_input, [])
        gate = result["gate_result"]
        assert gate["overall_pass"] is False
        assert gate["risk_assessment"] == "high"


# ---------------------------------------------------------------------------
# write_bundle: artifact files
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWriteBundle:
    def test_bundle_writes_three_files(self, tmp_path: pathlib.Path) -> None:
        reporter = ReplayReporter()
        bundle_dir = reporter.write_bundle(_make_valid_report_input(), tmp_path)
        assert (bundle_dir / "report.json").exists()
        assert (bundle_dir / "manifest.json").exists()
        assert (bundle_dir / "audit.log").exists()

    def test_bundle_dir_named_by_run_id(self, tmp_path: pathlib.Path) -> None:
        reporter = ReplayReporter()
        bundle_dir = reporter.write_bundle(_make_valid_report_input(), tmp_path)
        assert bundle_dir.name == _VALID_RUN_ID

    def test_report_json_is_valid_json(self, tmp_path: pathlib.Path) -> None:
        reporter = ReplayReporter()
        bundle_dir = reporter.write_bundle(_make_valid_report_input(), tmp_path)
        content = json.loads((bundle_dir / "report.json").read_bytes())
        assert content["schema_version"] == "replay_report.v1"

    def test_report_json_passes_schema(self, tmp_path: pathlib.Path) -> None:
        reporter = ReplayReporter()
        bundle_dir = reporter.write_bundle(_make_valid_report_input(), tmp_path)
        content = json.loads((bundle_dir / "report.json").read_bytes())
        jsonschema.validate(instance=content, schema=reporter._schema)

    def test_report_json_is_canonical_sorted_keys(self, tmp_path: pathlib.Path) -> None:
        """report.json must use sorted keys (canonical JSON)."""
        reporter = ReplayReporter()
        bundle_dir = reporter.write_bundle(_make_valid_report_input(), tmp_path)
        raw = (bundle_dir / "report.json").read_text(encoding="utf-8")
        # Re-parse and re-canonicalize; they must be identical
        parsed = json.loads(raw)
        expected = canonical_json_dumps(parsed)
        assert raw == expected

    def test_manifest_contains_correct_report_sha256(
        self, tmp_path: pathlib.Path
    ) -> None:
        reporter = ReplayReporter()
        bundle_dir = reporter.write_bundle(_make_valid_report_input(), tmp_path)
        report_bytes = (bundle_dir / "report.json").read_bytes()
        expected_sha256 = _sha256(report_bytes)
        manifest = json.loads((bundle_dir / "manifest.json").read_bytes())
        assert manifest["report_json_sha256"] == expected_sha256

    def test_manifest_contains_correct_audit_log_sha256(
        self, tmp_path: pathlib.Path
    ) -> None:
        reporter = ReplayReporter()
        bundle_dir = reporter.write_bundle(_make_valid_report_input(), tmp_path)
        audit_bytes = (bundle_dir / "audit.log").read_bytes()
        expected_sha256 = _sha256(audit_bytes)
        manifest = json.loads((bundle_dir / "manifest.json").read_bytes())
        assert manifest["audit_log_sha256"] == expected_sha256

    def test_manifest_contains_run_id_and_strategy_id(
        self, tmp_path: pathlib.Path
    ) -> None:
        reporter = ReplayReporter()
        bundle_dir = reporter.write_bundle(_make_valid_report_input(), tmp_path)
        manifest = json.loads((bundle_dir / "manifest.json").read_bytes())
        assert manifest["replay_run_id"] == _VALID_RUN_ID
        assert manifest["strategy_id"] == "primary_breakout_v1"
        assert manifest["bundle_schema_version"] == "replay_bundle.v1"

    def test_audit_log_always_written(self, tmp_path: pathlib.Path) -> None:
        reporter = ReplayReporter()
        bundle_dir = reporter.write_bundle(_make_valid_report_input(), tmp_path)
        audit_path = bundle_dir / "audit.log"
        assert audit_path.exists()
        # Should have content (at least the "started" entry)
        assert audit_path.stat().st_size > 0

    def test_audit_log_contains_started_entry(self, tmp_path: pathlib.Path) -> None:
        reporter = ReplayReporter()
        bundle_dir = reporter.write_bundle(_make_valid_report_input(), tmp_path)
        content = (bundle_dir / "audit.log").read_text(encoding="utf-8")
        assert "Replay reporter started" in content
        assert _VALID_RUN_ID in content

    def test_identical_inputs_produce_identical_report_json(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Two writes with identical inputs produce identical report.json content."""
        reporter = ReplayReporter()
        dir1 = tmp_path / "run1"
        dir2 = tmp_path / "run2"
        # Need matching run_ids across sub-contracts too
        ri1 = _make_valid_report_input(
            run_spec=_make_run_spec(replay_run_id="replay-same"),
            execution_result=_make_exec_result(run_id="replay-same"),
            replay_integrity=_make_integrity(run_id="replay-same"),
        )
        ri2 = _make_valid_report_input(
            run_spec=_make_run_spec(replay_run_id="replay-same"),
            execution_result=_make_exec_result(run_id="replay-same"),
            replay_integrity=_make_integrity(run_id="replay-same"),
        )
        b1 = reporter.write_bundle(ri1, dir1)
        b2 = reporter.write_bundle(ri2, dir2)
        bytes1 = (b1 / "report.json").read_bytes()
        bytes2 = (b2 / "report.json").read_bytes()
        assert bytes1 == bytes2
        assert _sha256(bytes1) == _sha256(bytes2)

    def test_manifest_is_canonical_json(self, tmp_path: pathlib.Path) -> None:
        reporter = ReplayReporter()
        bundle_dir = reporter.write_bundle(_make_valid_report_input(), tmp_path)
        raw = (bundle_dir / "manifest.json").read_text(encoding="utf-8")
        parsed = json.loads(raw)
        assert raw == canonical_json_dumps(parsed)


# ---------------------------------------------------------------------------
# Fail-closed: required fields and partial bundle cleanup
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFailClosed:
    def test_missing_required_field_raises_before_write(
        self, tmp_path: pathlib.Path
    ) -> None:
        """ReplayReporterError raised on bad input; no bundle directory created."""
        reporter = ReplayReporter()
        bad_exec = _make_exec_result(run_id="")  # invalid
        report_input = _make_valid_report_input(execution_result=bad_exec)
        with pytest.raises(ReplayReporterError):
            reporter.write_bundle(report_input, tmp_path)
        # Bundle directory should NOT exist or should be empty (no partial files)
        bundle_dir = tmp_path / _VALID_RUN_ID
        if bundle_dir.exists():
            files = list(bundle_dir.iterdir())
            assert not files, f"Partial bundle files found: {files}"

    def test_partial_bundle_cleaned_up_on_write_failure(
        self, tmp_path: pathlib.Path
    ) -> None:
        """If write fails mid-bundle, already-written files are cleaned up."""
        reporter = ReplayReporter()
        report_input = _make_valid_report_input()
        call_count = [0]
        original_write_bytes = pathlib.Path.write_bytes

        def patched_write_bytes(self: pathlib.Path, data: bytes) -> int:
            call_count[0] += 1
            if call_count[0] == 2:  # fail on manifest.json (second write)
                raise OSError("simulated write failure")
            return original_write_bytes(self, data)

        with patch.object(pathlib.Path, "write_bytes", patched_write_bytes):
            with pytest.raises(ReplayReporterError, match="Failed to write"):
                reporter.write_bundle(report_input, tmp_path)

        # report.json was written (first write), then cleaned up
        bundle_dir = tmp_path / _VALID_RUN_ID
        if bundle_dir.exists():
            remaining = list(bundle_dir.iterdir())
            assert not remaining, f"Partial files remain after cleanup: {remaining}"

    def test_schema_invalid_input_raises_reporter_error(self) -> None:
        """Report with wrong schema_version raises before any I/O."""
        reporter = ReplayReporter()
        bad = _make_valid_report_input(schema_version="nope.v99")
        with pytest.raises(ReplayReporterError, match="schema_version"):
            reporter.build_report_dict(bad, [])

    def test_no_strategy_logic_recalculation(self) -> None:
        """Reporter consumes metrics; it does not recalculate them."""
        # Supply pre-computed metrics — reporter passes them through unchanged.
        metrics = {
            "signals_total": 42,
            "win_rate": 0.71,
            "profit_factor": 1.5,
        }
        reporter = ReplayReporter()
        report_input = _make_valid_report_input(metrics=metrics)
        result = reporter.build_report_dict(report_input, [])
        # Metrics are passed through exactly as provided
        assert result["metrics"] == metrics
