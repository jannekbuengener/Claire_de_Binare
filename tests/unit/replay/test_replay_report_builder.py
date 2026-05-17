"""Tests for core.replay.replay_report_builder (#1847).

Covers: per-run summaries, scenario comparison, regime scorecard summary,
combined management report, artifact writing, run index artifact, and
fail-closed error paths.
"""

from __future__ import annotations

import json
import pathlib
from decimal import Decimal

import pytest

from core.replay.regime_analytics import RegimeScorecard, RegimeSegmentStats
from core.replay.resampling import (
    ResamplingConfig,
    ResamplingKPISummary,
    ResamplingSourceProvenance,
    ResamplingStabilityArtifact,
)
from core.replay.replay_report_builder import (
    ReplayReportBuilderError,
    _MANAGEMENT_REPORT_FILENAME,
    _RUN_INDEX_FILENAME,
    build_management_report,
    build_regime_scorecard_summary,
    build_resampling_stability_summary,
    build_run_summary_text,
    build_scenario_comparison_summary,
    write_management_report,
    write_run_index_artifact,
)
from core.replay.run_registry import ReplayRunRecord
from core.replay.scenario_harness import ScenarioGroupManifest, ScenarioRunResult

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_DATASET_FP = "a" * 64
_STARTED = "2026-04-01T10:00:00+00:00"
_FINISHED = "2026-04-01T10:05:00+00:00"
_EXECUTION_PROV = "bt-" + "b" * 16
_GROUP_FP = "c" * 64
_INPUT_FP = "d" * 64
_CONFIG_FP = "e" * 64


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _completed_record(**overrides: object) -> ReplayRunRecord:
    fields: dict = {
        "run_id": "replay-aabbccddeeff-0001",
        "status": "completed",
        "mode": "baseline",
        "strategy_id": "primary_breakout_v1",
        "symbol": "BTCUSDT",
        "dataset_fingerprint": _DATASET_FP,
        "scheduler_profile": "instant",
        "execution_provenance_id": _EXECUTION_PROV,
        "artifact_root": "/artifacts/replay_reports/replay-aabbccddeeff-0001",
        "deterministic_replay_ok": True,
        "started_at_utc": _STARTED,
        "finished_at_utc": _FINISHED,
    }
    fields.update(overrides)
    return ReplayRunRecord(**fields)


def _failed_record(**overrides: object) -> ReplayRunRecord:
    fields: dict = {
        "run_id": "replay-aabbccddeeff-0002",
        "status": "failed",
        "mode": "baseline",
        "strategy_id": "primary_breakout_v1",
        "symbol": "BTCUSDT",
        "dataset_fingerprint": _DATASET_FP,
        "scheduler_profile": "instant",
        "execution_provenance_id": _EXECUTION_PROV,
        "artifact_root": "/artifacts/replay_reports/replay-aabbccddeeff-0002",
        "deterministic_replay_ok": False,
        "started_at_utc": _STARTED,
        "finished_at_utc": _FINISHED,
        "failure_reason": "determinism check failed: hash mismatch",
    }
    fields.update(overrides)
    return ReplayRunRecord(**fields)


def _manifest(results: tuple[ScenarioRunResult, ...], **overrides: object) -> ScenarioGroupManifest:
    succeeded = sum(1 for r in results if r.succeeded)
    failed = sum(1 for r in results if not r.succeeded)
    fields: dict = {
        "group_id": "sg-001122334455",
        "scenario_results": results,
        "artifact_root": "/artifacts/scenario_groups/sg-001122334455",
        "group_fingerprint": _GROUP_FP,
        "started_at_utc": _STARTED,
        "finished_at_utc": _FINISHED,
        "total_scenarios": len(results),
        "succeeded_count": succeeded,
        "failed_count": failed,
    }
    fields.update(overrides)
    return ScenarioGroupManifest(**fields)


def _scorecard(**overrides: object) -> RegimeScorecard:
    seg = RegimeSegmentStats(
        regime_id="TREND",
        record_count=10,
        signal_count=50,
        fill_count=45,
        reject_count=5,
        pnl_sum=Decimal("1.23456789"),
        fill_rate=Decimal("0.90000000"),
    )
    fields: dict = {
        "run_id": "replay-aabbccddeeff-0001",
        "segments": (seg,),
        "total_records": 10,
        "unknown_regime_count": 0,
        "input_fingerprint": _INPUT_FP,
    }
    fields.update(overrides)
    return RegimeScorecard(**fields)


def _stability(**overrides: object) -> ResamplingStabilityArtifact:
    config = ResamplingConfig(
        method="block_bootstrap",
        sample_count=32,
        sample_block_count=4,
        seed=7,
        selected_kpis=("pnl_sum", "fill_rate"),
    )
    provenance = ResamplingSourceProvenance(
        source_run_id="replay-aabbccddeeff-0001",
        run_count=1,
        block_count=4,
        dataset_fingerprint=_DATASET_FP,
        execution_provenance_id=_EXECUTION_PROV,
        input_fingerprint=_INPUT_FP,
    )
    summaries = (
        ResamplingKPISummary(
            kpi="pnl_sum",
            sample_count=32,
            baseline="1.23456789",
            minimum="0.50000000",
            p05="0.80000000",
            p50="1.20000000",
            p95="1.70000000",
            maximum="2.00000000",
            empirical_span="1.50000000",
        ),
        ResamplingKPISummary(
            kpi="fill_rate",
            sample_count=32,
            baseline="0.90000000",
            minimum="0.50000000",
            p05="0.66666667",
            p50="0.83333333",
            p95="1.00000000",
            maximum="1.00000000",
            empirical_span="0.50000000",
        ),
    )
    fields: dict = {
        "schema_version": "replay_resampling_stability.v1",
        "resampling_method": "block_bootstrap",
        "sample_count": 32,
        "sample_block_count": 4,
        "config": config,
        "config_fingerprint": _CONFIG_FP,
        "source_provenance": provenance,
        "baseline_metrics": {
            "pnl_sum": "1.23456789",
            "fill_rate": "0.90000000",
        },
        "kpi_summaries": summaries,
        "operator_summary": (
            "method=block_bootstrap; samples=32; blocks_per_sample=4; seed=7",
            "pnl_sum: baseline=1.23456789; empirical_band_p05_p95=0.80000000..1.70000000; span=1.50000000",
        ),
    }
    fields.update(overrides)
    return ResamplingStabilityArtifact(**fields)


def _ok_result(scenario_id: str, run_id: str = "replay-aabbccddeeff-0001") -> ScenarioRunResult:
    return ScenarioRunResult(scenario_id=scenario_id, exit_code=0, run_id=run_id)


def _fail_result(scenario_id: str, reason: str = "execution error") -> ScenarioRunResult:
    return ScenarioRunResult(scenario_id=scenario_id, exit_code=2, failure_reason=reason)


# ---------------------------------------------------------------------------
# build_run_summary_text — successful run
# ---------------------------------------------------------------------------


class TestBuildRunSummaryTextSuccess:
    def test_contains_run_id(self) -> None:
        rec = _completed_record()
        text = build_run_summary_text(rec)
        assert rec.run_id in text

    def test_contains_status(self) -> None:
        rec = _completed_record()
        text = build_run_summary_text(rec)
        assert "completed" in text

    def test_success_icon_present(self) -> None:
        rec = _completed_record()
        text = build_run_summary_text(rec)
        assert "✓" in text

    def test_contains_strategy_id(self) -> None:
        rec = _completed_record()
        text = build_run_summary_text(rec)
        assert rec.strategy_id in text

    def test_contains_symbol(self) -> None:
        rec = _completed_record()
        text = build_run_summary_text(rec)
        assert rec.symbol in text

    def test_contains_scheduler_profile(self) -> None:
        rec = _completed_record()
        text = build_run_summary_text(rec)
        assert rec.scheduler_profile in text

    def test_deterministic(self) -> None:
        rec = _completed_record()
        assert build_run_summary_text(rec) == build_run_summary_text(rec)

    def test_no_failure_section_on_success(self) -> None:
        rec = _completed_record()
        text = build_run_summary_text(rec)
        assert "## Failure" not in text

    def test_gate_status_absent_shown_as_dash(self) -> None:
        rec = _completed_record()
        text = build_run_summary_text(rec)
        assert "Gate status" in text
        assert "—" in text


# ---------------------------------------------------------------------------
# build_run_summary_text — failed run
# ---------------------------------------------------------------------------


class TestBuildRunSummaryTextFailure:
    def test_contains_failure_reason(self) -> None:
        rec = _failed_record()
        text = build_run_summary_text(rec)
        assert rec.failure_reason in text

    def test_failure_section_present(self) -> None:
        rec = _failed_record()
        text = build_run_summary_text(rec)
        assert "## Failure" in text

    def test_failure_icon_present(self) -> None:
        rec = _failed_record()
        text = build_run_summary_text(rec)
        assert "✗" in text

    def test_failed_status_present(self) -> None:
        rec = _failed_record()
        text = build_run_summary_text(rec)
        assert "failed" in text

    def test_deterministic_failed(self) -> None:
        rec = _failed_record()
        assert build_run_summary_text(rec) == build_run_summary_text(rec)


# ---------------------------------------------------------------------------
# build_run_summary_text — type validation
# ---------------------------------------------------------------------------


class TestBuildRunSummaryTextValidation:
    def test_rejects_non_record(self) -> None:
        with pytest.raises(ReplayReportBuilderError, match="Expected ReplayRunRecord"):
            build_run_summary_text("not a record")  # type: ignore[arg-type]

    def test_rejects_none(self) -> None:
        with pytest.raises(ReplayReportBuilderError):
            build_run_summary_text(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# build_scenario_comparison_summary
# ---------------------------------------------------------------------------


class TestBuildScenarioComparisonSummary:
    def test_contains_group_id(self) -> None:
        m = _manifest((_ok_result("baseline"),))
        text = build_scenario_comparison_summary(m)
        assert m.group_id in text

    def test_contains_scenario_id(self) -> None:
        m = _manifest((_ok_result("baseline"), _fail_result("pessimistic_execution")))
        text = build_scenario_comparison_summary(m)
        assert "baseline" in text
        assert "pessimistic_execution" in text

    def test_success_icon_for_ok_result(self) -> None:
        m = _manifest((_ok_result("baseline"),))
        text = build_scenario_comparison_summary(m)
        assert "✓ ok" in text

    def test_failure_icon_for_failed_result(self) -> None:
        m = _manifest((_fail_result("pessimistic_execution", "fill rate too low"),))
        text = build_scenario_comparison_summary(m)
        assert "✗ failed" in text

    def test_failure_reason_present(self) -> None:
        m = _manifest((_fail_result("feed_gap", "feed gap caused bridge failure"),))
        text = build_scenario_comparison_summary(m)
        assert "feed gap caused bridge failure" in text

    def test_counts_in_summary(self) -> None:
        results = (_ok_result("baseline"), _fail_result("delayed_execution"))
        m = _manifest(results)
        text = build_scenario_comparison_summary(m)
        assert str(m.total_scenarios) in text
        assert str(m.succeeded_count) in text
        assert str(m.failed_count) in text

    def test_no_run_id_shows_dash(self) -> None:
        m = _manifest((_fail_result("pessimistic_execution"),))
        text = build_scenario_comparison_summary(m)
        assert "—" in text

    def test_deterministic(self) -> None:
        results = (_ok_result("baseline"), _fail_result("feed_gap"))
        m = _manifest(results)
        assert build_scenario_comparison_summary(m) == build_scenario_comparison_summary(m)

    def test_rejects_non_manifest(self) -> None:
        with pytest.raises(ReplayReportBuilderError, match="Expected ScenarioGroupManifest"):
            build_scenario_comparison_summary("not a manifest")  # type: ignore[arg-type]

    def test_single_scenario(self) -> None:
        m = _manifest((_ok_result("baseline"),))
        text = build_scenario_comparison_summary(m)
        assert "baseline" in text
        assert "✓ ok" in text


# ---------------------------------------------------------------------------
# build_regime_scorecard_summary
# ---------------------------------------------------------------------------


class TestBuildRegimeScorecardSummary:
    def test_contains_run_id(self) -> None:
        sc = _scorecard()
        text = build_regime_scorecard_summary(sc)
        assert sc.run_id in text

    def test_contains_regime_id(self) -> None:
        sc = _scorecard()
        text = build_regime_scorecard_summary(sc)
        assert "TREND" in text

    def test_contains_record_count(self) -> None:
        sc = _scorecard()
        text = build_regime_scorecard_summary(sc)
        assert "10" in text

    def test_contains_fill_rate(self) -> None:
        sc = _scorecard()
        text = build_regime_scorecard_summary(sc)
        assert "0.90000000" in text

    def test_contains_pnl_sum(self) -> None:
        sc = _scorecard()
        text = build_regime_scorecard_summary(sc)
        assert "1.23456789" in text

    def test_unknown_regime_count_present(self) -> None:
        sc = _scorecard(unknown_regime_count=3, total_records=10)
        text = build_regime_scorecard_summary(sc)
        assert "3" in text

    def test_zero_total_records_shows_na(self) -> None:
        sc = _scorecard(segments=(), total_records=0, unknown_regime_count=0)
        text = build_regime_scorecard_summary(sc)
        assert "n/a" in text

    def test_empty_segments_shows_placeholder(self) -> None:
        sc = _scorecard(segments=(), total_records=0, unknown_regime_count=0)
        text = build_regime_scorecard_summary(sc)
        assert "—" in text

    def test_deterministic(self) -> None:
        sc = _scorecard()
        assert build_regime_scorecard_summary(sc) == build_regime_scorecard_summary(sc)

    def test_rejects_non_scorecard(self) -> None:
        with pytest.raises(ReplayReportBuilderError, match="Expected RegimeScorecard"):
            build_regime_scorecard_summary("not a scorecard")  # type: ignore[arg-type]

    def test_multiple_segments(self) -> None:
        seg_trend = RegimeSegmentStats(
            regime_id="TREND", record_count=5, signal_count=20,
            fill_count=18, reject_count=2,
            pnl_sum=Decimal("0.5"), fill_rate=Decimal("0.9"),
        )
        seg_range = RegimeSegmentStats(
            regime_id="RANGE", record_count=8, signal_count=30,
            fill_count=25, reject_count=5,
            pnl_sum=Decimal("-0.2"), fill_rate=Decimal("0.83333333"),
        )
        sc = RegimeScorecard(
            run_id="replay-aabbccddeeff-0001",
            segments=(seg_trend, seg_range),
            total_records=13,
            unknown_regime_count=0,
            input_fingerprint=_INPUT_FP,
        )
        text = build_regime_scorecard_summary(sc)
        assert "TREND" in text
        assert "RANGE" in text


# ---------------------------------------------------------------------------
# build_resampling_stability_summary
# ---------------------------------------------------------------------------


class TestBuildResamplingStabilitySummary:
    def test_contains_run_id(self) -> None:
        stability = _stability()
        text = build_resampling_stability_summary(stability)
        assert stability.source_provenance.source_run_id in text

    def test_contains_method(self) -> None:
        stability = _stability()
        text = build_resampling_stability_summary(stability)
        assert "block_bootstrap" in text

    def test_contains_kpi_values(self) -> None:
        stability = _stability()
        text = build_resampling_stability_summary(stability)
        assert "pnl_sum" in text
        assert "0.80000000" in text
        assert "0.90000000" in text

    def test_contains_operator_summary(self) -> None:
        stability = _stability()
        text = build_resampling_stability_summary(stability)
        assert "Operator Summary" in text
        assert "samples=32" in text

    def test_rejects_invalid_type(self) -> None:
        with pytest.raises(ReplayReportBuilderError, match="Expected ResamplingStabilityArtifact"):
            build_resampling_stability_summary("bad")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# build_management_report
# ---------------------------------------------------------------------------


class TestBuildManagementReport:
    def test_baseline_only_contains_run_id(self) -> None:
        rec = _completed_record()
        text = build_management_report(record=rec)
        assert rec.run_id in text

    def test_with_manifest_contains_group_id(self) -> None:
        rec = _completed_record()
        m = _manifest((_ok_result("baseline"),))
        text = build_management_report(record=rec, manifest=m)
        assert m.group_id in text

    def test_with_scorecard_contains_regime(self) -> None:
        rec = _completed_record()
        sc = _scorecard()
        text = build_management_report(record=rec, scorecard=sc)
        assert "TREND" in text

    def test_with_stability_contains_section(self) -> None:
        rec = _completed_record()
        stability = _stability()
        text = build_management_report(record=rec, stability=stability)
        assert "Resampling Stability" in text
        assert "block_bootstrap" in text

    def test_all_three_sections(self) -> None:
        rec = _completed_record()
        m = _manifest((_ok_result("baseline"), _fail_result("feed_gap")))
        sc = _scorecard()
        text = build_management_report(record=rec, manifest=m, scorecard=sc)
        assert rec.run_id in text
        assert m.group_id in text
        assert "TREND" in text

    def test_all_optional_sections(self) -> None:
        rec = _completed_record()
        m = _manifest((_ok_result("baseline"), _fail_result("feed_gap")))
        sc = _scorecard()
        stability = _stability()
        text = build_management_report(
            record=rec,
            manifest=m,
            scorecard=sc,
            stability=stability,
        )
        assert rec.run_id in text
        assert m.group_id in text
        assert "TREND" in text
        assert "Resampling Stability" in text

    def test_failed_run_report_includes_failure_reason(self) -> None:
        rec = _failed_record()
        text = build_management_report(record=rec)
        assert rec.failure_reason in text
        assert "## Failure" in text

    def test_separator_present_with_manifest(self) -> None:
        rec = _completed_record()
        m = _manifest((_ok_result("baseline"),))
        text = build_management_report(record=rec, manifest=m)
        assert "---" in text

    def test_separator_present_with_scorecard(self) -> None:
        rec = _completed_record()
        sc = _scorecard()
        text = build_management_report(record=rec, scorecard=sc)
        assert "---" in text

    def test_separator_present_with_stability(self) -> None:
        rec = _completed_record()
        stability = _stability()
        text = build_management_report(record=rec, stability=stability)
        assert "---" in text

    def test_no_section_divider_without_optional_args(self) -> None:
        rec = _completed_record()
        text = build_management_report(record=rec)
        # Section divider is "\n---\n"; table separators like "|-------|" are fine.
        assert "\n---\n" not in text

    def test_deterministic(self) -> None:
        rec = _completed_record()
        m = _manifest((_ok_result("baseline"),))
        sc = _scorecard()
        t1 = build_management_report(record=rec, manifest=m, scorecard=sc)
        t2 = build_management_report(record=rec, manifest=m, scorecard=sc)
        assert t1 == t2

    def test_rejects_invalid_record(self) -> None:
        with pytest.raises(ReplayReportBuilderError, match="Expected ReplayRunRecord"):
            build_management_report(record="bad")  # type: ignore[arg-type]

    def test_rejects_invalid_manifest(self) -> None:
        rec = _completed_record()
        with pytest.raises(ReplayReportBuilderError, match="manifest must be"):
            build_management_report(record=rec, manifest="bad")  # type: ignore[arg-type]

    def test_rejects_invalid_scorecard(self) -> None:
        rec = _completed_record()
        with pytest.raises(ReplayReportBuilderError, match="scorecard must be"):
            build_management_report(record=rec, scorecard=42)  # type: ignore[arg-type]

    def test_rejects_invalid_stability(self) -> None:
        rec = _completed_record()
        with pytest.raises(ReplayReportBuilderError, match="stability must be"):
            build_management_report(record=rec, stability=42)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# write_management_report
# ---------------------------------------------------------------------------


class TestWriteManagementReport:
    def test_creates_file(self, tmp_path: pathlib.Path) -> None:
        rec = _completed_record()
        report = build_management_report(record=rec)
        write_management_report(report, tmp_path)
        out = tmp_path / _MANAGEMENT_REPORT_FILENAME
        assert out.exists()

    def test_file_content_matches(self, tmp_path: pathlib.Path) -> None:
        rec = _completed_record()
        report = build_management_report(record=rec)
        write_management_report(report, tmp_path)
        out = tmp_path / _MANAGEMENT_REPORT_FILENAME
        assert out.read_text(encoding="utf-8") == report

    def test_creates_parent_dirs(self, tmp_path: pathlib.Path) -> None:
        rec = _completed_record()
        report = build_management_report(record=rec)
        nested = tmp_path / "a" / "b" / "c"
        write_management_report(report, nested)
        assert (nested / _MANAGEMENT_REPORT_FILENAME).exists()

    def test_rejects_empty_report(self, tmp_path: pathlib.Path) -> None:
        with pytest.raises(ReplayReportBuilderError, match="non-empty string"):
            write_management_report("", tmp_path)

    def test_rejects_whitespace_only_report(self, tmp_path: pathlib.Path) -> None:
        with pytest.raises(ReplayReportBuilderError, match="non-empty string"):
            write_management_report("   ", tmp_path)

    def test_fail_closed_on_io_error(self, tmp_path: pathlib.Path) -> None:
        rec = _completed_record()
        report = build_management_report(record=rec)
        # Use a path that is a file (not a dir) so mkdir fails.
        blocker = tmp_path / "blocker"
        blocker.write_text("block")
        with pytest.raises(ReplayReportBuilderError, match="Failed to write management report"):
            write_management_report(report, blocker)

    def test_accepts_path_object(self, tmp_path: pathlib.Path) -> None:
        rec = _completed_record()
        report = build_management_report(record=rec)
        write_management_report(report, tmp_path)
        assert (tmp_path / _MANAGEMENT_REPORT_FILENAME).exists()

    def test_accepts_string_path(self, tmp_path: pathlib.Path) -> None:
        rec = _completed_record()
        report = build_management_report(record=rec)
        write_management_report(report, str(tmp_path))
        assert (tmp_path / _MANAGEMENT_REPORT_FILENAME).exists()


# ---------------------------------------------------------------------------
# write_run_index_artifact
# ---------------------------------------------------------------------------


class TestWriteRunIndexArtifact:
    def test_creates_file(self, tmp_path: pathlib.Path) -> None:
        records = [_completed_record(), _failed_record()]
        write_run_index_artifact(records, tmp_path)
        out = tmp_path / _RUN_INDEX_FILENAME
        assert out.exists()

    def test_file_is_valid_json(self, tmp_path: pathlib.Path) -> None:
        records = [_completed_record()]
        write_run_index_artifact(records, tmp_path)
        out = tmp_path / _RUN_INDEX_FILENAME
        data = json.loads(out.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_run_count_correct(self, tmp_path: pathlib.Path) -> None:
        records = [_completed_record(), _failed_record()]
        write_run_index_artifact(records, tmp_path)
        data = json.loads((tmp_path / _RUN_INDEX_FILENAME).read_text(encoding="utf-8"))
        assert data["run_count"] == 2

    def test_runs_array_length(self, tmp_path: pathlib.Path) -> None:
        records = [_completed_record(), _failed_record()]
        write_run_index_artifact(records, tmp_path)
        data = json.loads((tmp_path / _RUN_INDEX_FILENAME).read_text(encoding="utf-8"))
        assert len(data["runs"]) == 2

    def test_empty_records_valid(self, tmp_path: pathlib.Path) -> None:
        write_run_index_artifact([], tmp_path)
        data = json.loads((tmp_path / _RUN_INDEX_FILENAME).read_text(encoding="utf-8"))
        assert data["run_count"] == 0
        assert data["runs"] == []

    def test_deterministic_output(self, tmp_path: pathlib.Path) -> None:
        records = [_completed_record(), _failed_record()]
        out = tmp_path / _RUN_INDEX_FILENAME
        write_run_index_artifact(records, tmp_path)
        content1 = out.read_text(encoding="utf-8")
        out.unlink()
        write_run_index_artifact(records, tmp_path)
        content2 = out.read_text(encoding="utf-8")
        assert content1 == content2

    def test_run_id_present_in_output(self, tmp_path: pathlib.Path) -> None:
        rec = _completed_record()
        write_run_index_artifact([rec], tmp_path)
        data = json.loads((tmp_path / _RUN_INDEX_FILENAME).read_text(encoding="utf-8"))
        assert data["runs"][0]["run_id"] == rec.run_id

    def test_creates_parent_dirs(self, tmp_path: pathlib.Path) -> None:
        nested = tmp_path / "x" / "y"
        write_run_index_artifact([], nested)
        assert (nested / _RUN_INDEX_FILENAME).exists()

    def test_rejects_invalid_record_in_list(self, tmp_path: pathlib.Path) -> None:
        with pytest.raises(ReplayReportBuilderError, match="records\\[0\\] must be ReplayRunRecord"):
            write_run_index_artifact(["not a record"], tmp_path)  # type: ignore[list-item]

    def test_fail_closed_on_io_error(self, tmp_path: pathlib.Path) -> None:
        blocker = tmp_path / "blocker"
        blocker.write_text("block")
        with pytest.raises(ReplayReportBuilderError, match="Failed to write run index"):
            write_run_index_artifact([], blocker)

    def test_accepts_string_path(self, tmp_path: pathlib.Path) -> None:
        write_run_index_artifact([_completed_record()], str(tmp_path))
        assert (tmp_path / _RUN_INDEX_FILENAME).exists()
