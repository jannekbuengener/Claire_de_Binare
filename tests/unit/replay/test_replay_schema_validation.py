"""Schema validation tests for replay_report.v1.schema.json.

Scope:
  - Valid replay report passes schema validation
  - Malformed/incomplete reports fail schema validation
  - Type discriminator: backtest reports cannot be misread as replay reports
  - Required field enforcement
  - Optional field omission is schema-compatible
"""

import json
import pathlib

import jsonschema
import pytest

from core.replay.replay_contracts import (
    ReplayRunSpec,
    ReplayExecutionResult,
    ReplayIntegrity,
    EnvelopeSummary,
    ReplayReportArtifactManifest,
    ReplayReportInput,
)

_SCHEMA_PATH = (
    pathlib.Path(__file__).parent.parent.parent.parent
    / "docs"
    / "contracts"
    / "replay_report.v1.schema.json"
)
_BACKTEST_SCHEMA_PATH = (
    pathlib.Path(__file__).parent.parent.parent.parent
    / "docs"
    / "contracts"
    / "strategy_validation_report_v1.schema.json"
)


def _load_schema(path: pathlib.Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _make_valid_report_dict() -> dict:
    """Build a minimal but fully valid replay report dict."""
    run_spec = ReplayRunSpec(
        replay_run_id="replay-test-001",
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        start_ts_ms=1_000_000,
        end_ts_ms=2_000_000,
        code_commit="abc123def456",
        run_mode="shadow",
    )
    exec_result = ReplayExecutionResult(
        run_id="replay-test-001",
        events_processed=100,
        decisions_made=10,
        orders_placed=5,
        fills_recorded=4,
        envelope_hashes=["a" * 64, "b" * 64],
    )
    integrity = ReplayIntegrity(
        run_id="replay-test-001",
        envelope_count=2,
        envelope_chain_hash="c" * 64,
        event_loop_states_hash="d" * 64,
        integrity_ok=True,
        failed_checks=[],
    )
    summary = EnvelopeSummary(
        decision_envelopes_total=10,
        order_envelopes_total=5,
        fill_envelopes_total=4,
    )
    manifest = ReplayReportArtifactManifest(
        envelope_log_uri="/data/replay/envelopes.jsonl",
        event_loop_states_uri="/data/replay/states.jsonl",
        report_artifact_uri="/data/replay/report.json",
    )
    return ReplayReportInput(
        schema_version="replay_report.v1",
        report_type="shadow_replay",
        strategy_id="primary_breakout_v1",
        run_spec=run_spec,
        execution_result=exec_result,
        replay_integrity=integrity,
        envelope_summary=summary,
        artifact_manifest=manifest,
    ).to_dict()


@pytest.mark.unit
class TestReplaySchemaValidation:
    """Test JSON schema validation for replay_report.v1."""

    def test_schema_file_exists(self) -> None:
        """Schema file is present and parseable."""
        assert _SCHEMA_PATH.exists(), f"Schema not found at {_SCHEMA_PATH}"
        schema = _load_schema(_SCHEMA_PATH)
        assert schema["title"] == "Deterministic Replay Report Contract"

    def test_valid_minimal_report_passes(self) -> None:
        """A minimal valid report dict passes schema validation."""
        schema = _load_schema(_SCHEMA_PATH)
        report = _make_valid_report_dict()
        jsonschema.validate(instance=report, schema=schema)

    def test_valid_report_with_optional_fields_passes(self) -> None:
        """A report with optional sections set also passes schema validation."""
        schema = _load_schema(_SCHEMA_PATH)
        report = _make_valid_report_dict()
        report["config_snapshot"] = {"entry_lookback_minutes": 240}
        report["dataset_summary"] = {"symbol": "BTCUSDT", "candle_count": 1440}
        report["metrics"] = {"signals_total": 50, "win_rate": 0.6}
        report["thresholds_applied"] = {"min_win_rate": 0.5}
        report["gate_result"] = {"decision": "PASS"}
        report["metadata"] = {"source": "unit_test"}
        jsonschema.validate(instance=report, schema=schema)

    def test_optional_fields_absent_passes(self) -> None:
        """Schema accepts report with no optional fields (None-omission stable)."""
        schema = _load_schema(_SCHEMA_PATH)
        report = _make_valid_report_dict()
        for optional_key in ("config_snapshot", "dataset_summary", "metrics", "thresholds_applied", "gate_result", "metadata"):
            assert optional_key not in report, f"Expected {optional_key!r} absent"
        jsonschema.validate(instance=report, schema=schema)

    def test_missing_schema_version_fails(self) -> None:
        """Missing schema_version causes schema validation failure."""
        schema = _load_schema(_SCHEMA_PATH)
        report = _make_valid_report_dict()
        del report["schema_version"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=report, schema=schema)

    def test_wrong_schema_version_fails(self) -> None:
        """Wrong schema_version (e.g., backtest) causes schema validation failure."""
        schema = _load_schema(_SCHEMA_PATH)
        report = _make_valid_report_dict()
        report["schema_version"] = "strategy_validation_report.v1"  # backtest version
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=report, schema=schema)

    def test_missing_replay_integrity_fails(self) -> None:
        """Missing replay_integrity (required) causes schema validation failure."""
        schema = _load_schema(_SCHEMA_PATH)
        report = _make_valid_report_dict()
        del report["replay_integrity"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=report, schema=schema)

    def test_missing_envelope_summary_fails(self) -> None:
        """Missing envelope_summary (required) causes schema validation failure."""
        schema = _load_schema(_SCHEMA_PATH)
        report = _make_valid_report_dict()
        del report["envelope_summary"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=report, schema=schema)

    def test_missing_artifact_manifest_fails(self) -> None:
        """Missing artifact_manifest (required) causes schema validation failure."""
        schema = _load_schema(_SCHEMA_PATH)
        report = _make_valid_report_dict()
        del report["artifact_manifest"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=report, schema=schema)

    def test_invalid_code_commit_pattern_fails(self) -> None:
        """Invalid code_commit (non-hex) causes schema validation failure."""
        schema = _load_schema(_SCHEMA_PATH)
        report = _make_valid_report_dict()
        report["run_spec"]["code_commit"] = "not-a-hex-commit"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=report, schema=schema)

    def test_invalid_envelope_hash_pattern_fails(self) -> None:
        """Invalid envelope hash (wrong length) causes schema validation failure."""
        schema = _load_schema(_SCHEMA_PATH)
        report = _make_valid_report_dict()
        report["execution_result"]["envelope_hashes"] = ["short"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=report, schema=schema)

    def test_invalid_run_mode_fails(self) -> None:
        """Invalid run_mode value causes schema validation failure."""
        schema = _load_schema(_SCHEMA_PATH)
        report = _make_valid_report_dict()
        report["run_spec"]["run_mode"] = "invalid_mode"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=report, schema=schema)

    def test_invalid_report_type_fails(self) -> None:
        """Invalid report_type value causes schema validation failure."""
        schema = _load_schema(_SCHEMA_PATH)
        report = _make_valid_report_dict()
        report["report_type"] = "backtest"  # Not allowed in replay schema
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=report, schema=schema)


@pytest.mark.unit
class TestReplayVsBacktestSchemaDiscrimination:
    """Verify replay and backtest schemas are distinct and non-interchangeable."""

    def test_replay_report_rejected_by_backtest_schema(self) -> None:
        """A replay report is rejected by the backtest schema (different schema_version)."""
        backtest_schema = _load_schema(_BACKTEST_SCHEMA_PATH)
        replay_report = _make_valid_report_dict()
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=replay_report, schema=backtest_schema)

    def test_backtest_schema_version_differs(self) -> None:
        """The two schemas use distinct schema_version discriminators."""
        replay_schema = _load_schema(_SCHEMA_PATH)
        backtest_schema = _load_schema(_BACKTEST_SCHEMA_PATH)
        replay_version = replay_schema["properties"]["schema_version"]["const"]
        backtest_version = backtest_schema["properties"]["schema_version"]["const"]
        assert replay_version != backtest_version
        assert replay_version == "replay_report.v1"
        assert "strategy_validation_report" in backtest_version
