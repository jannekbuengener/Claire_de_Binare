"""Fixture-only Replay→Paper→Compare→Calibration→Gate regression contract (#3822)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from core.replay.arvp_gate import ARVPEvidenceBundle, build_arvp_gate_verdict
from core.replay.replay_vs_paper_compare import ComparePaths, compare_from_paths
from core.replay.run_registry import ReplayRunRecord
from core.replay.simulator_calibration_report import build_simulator_calibration_report

from tests.unit.arvp._arvp_calibration_gate_helpers import (
    comparison_for_calibration,
    paper_reference_window,
    replay_report,
    run_calibration_pipeline,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

_FIXTURE_ALIGNED = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "arvp"
    / "calibration"
    / "aligned_happy_path"
)


def test_aligned_happy_path_compare_calibration_gate_pass(tmp_path: Path) -> None:
    pipeline = run_calibration_pipeline(
        tmp_path,
        replay=replay_report(signals=3, orders=2, fills=2),
        paper=paper_reference_window(signal_count=1, order_count=1, fill_count=1),
    )
    assert pipeline.comparison.status == "aligned"
    assert pipeline.calibration.status == "aligned"
    assert pipeline.calibration.drift_classification in {
        "optimistic",
        "pessimistic",
        "ambiguous",
    }
    assert len(pipeline.calibration.calibration_fingerprint) == 64
    assert pipeline.gate.verdict == "pass"
    assert pipeline.gate.blocking_findings == ()


def test_aligned_fixture_bundle_roundtrip(tmp_path: Path) -> None:
    replay_path = _FIXTURE_ALIGNED / "replay_report.json"
    paper_path = _FIXTURE_ALIGNED / "paper_reference_window.json"
    assert replay_path.is_file()
    assert paper_path.is_file()

    comparison = compare_from_paths(
        ComparePaths(replay_report_json=replay_path, paper_reference_json=paper_path)
    )
    calibration = build_simulator_calibration_report(comparison)
    record = ReplayRunRecord(
        run_id="replay-aabbccddee11-0001",
        status="completed",
        mode="baseline",
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        dataset_fingerprint="a" * 64,
        scheduler_profile="2x",
        execution_provenance_id="bt-0123456789abcdef",
        artifact_root="artifacts/replay_reports/replay-aabbccddee11-0001",
        deterministic_replay_ok=True,
        failure_reason=None,
        started_at_utc="2026-04-22T14:00:00+00:00",
        finished_at_utc="2026-04-22T14:00:05+00:00",
    )
    gate = build_arvp_gate_verdict(ARVPEvidenceBundle(record=record, shadow=comparison))
    assert comparison.status == "aligned"
    assert calibration.drift_classification in {"optimistic", "pessimistic", "ambiguous"}
    assert gate.verdict == "pass"


def test_symbol_mismatch_is_unusable_fail_closed(tmp_path: Path) -> None:
    pipeline = run_calibration_pipeline(
        tmp_path,
        replay=replay_report(symbol="BTCUSDT"),
        paper=paper_reference_window(symbol="ETHUSDT"),
    )
    assert pipeline.comparison.status == "unusable"
    assert pipeline.calibration.status == "unusable"
    assert pipeline.calibration.drift_classification == "unusable"
    assert pipeline.gate.verdict == "fail"
    assert pipeline.gate.blocking_findings


def test_missing_replay_artifact_fail_closed(tmp_path: Path) -> None:
    paper_path = tmp_path / "paper.json"
    paper_path.write_text("{}", encoding="utf-8")
    missing_replay = tmp_path / "missing_report.json"
    with pytest.raises(Exception):
        compare_from_paths(
            ComparePaths(
                replay_report_json=missing_replay,
                paper_reference_json=paper_path,
            )
        )


def test_running_replay_record_blocks_gate_without_promotion(tmp_path: Path) -> None:
    pipeline = run_calibration_pipeline(
        tmp_path,
        replay=replay_report(),
        paper=paper_reference_window(),
        record_overrides={"status": "running", "finished_at_utc": None},
    )
    assert pipeline.comparison.status == "aligned"
    assert pipeline.gate.verdict == "blocked"
    assert pipeline.gate.blocking_findings == ()


def test_failed_replay_record_fail_closed_gate(tmp_path: Path) -> None:
    pipeline = run_calibration_pipeline(
        tmp_path,
        replay=replay_report(),
        paper=paper_reference_window(),
        record_overrides={
            "status": "failed",
            "failure_reason": "deterministic_verify_mismatch",
        },
    )
    assert pipeline.gate.verdict == "fail"
    assert any("run_failed" in f for f in pipeline.gate.blocking_findings)


@pytest.mark.parametrize(
    ("fill_rate_delta", "expected_drift"),
    [
        (Decimal("0.02"), "optimistic"),
        (Decimal("-0.02"), "pessimistic"),
    ],
)
def test_simulator_drift_classifications(
    fill_rate_delta: Decimal, expected_drift: str
) -> None:
    comparison = comparison_for_calibration(fill_rate_delta=fill_rate_delta)
    report = build_simulator_calibration_report(comparison)
    assert report.drift_classification == expected_drift
    assert len(report.calibration_fingerprint) == 64


def test_ambiguous_drift_when_proxy_signals_conflict() -> None:
    comparison = comparison_for_calibration(
        fill_rate_delta=None, fill_count_delta=5, inferred_unfilled_count_delta=3
    )
    report = build_simulator_calibration_report(comparison)
    assert report.drift_classification == "ambiguous"
    assert any("mixed_signals" in note for note in report.notes)


def test_calibration_fingerprint_is_deterministic() -> None:
    comparison = comparison_for_calibration(fill_rate_delta=Decimal("0.01"))
    first = build_simulator_calibration_report(comparison)
    second = build_simulator_calibration_report(comparison)
    assert first.calibration_fingerprint == second.calibration_fingerprint


def test_gate_fingerprint_changes_when_shadow_misaligned(tmp_path: Path) -> None:
    aligned = run_calibration_pipeline(
        tmp_path / "aligned",
        replay=replay_report(),
        paper=paper_reference_window(),
    )
    misaligned = run_calibration_pipeline(
        tmp_path / "misaligned",
        replay=replay_report(),
        paper=paper_reference_window(),
        shadow=comparison_for_calibration(
            status="misaligned",
            alignment_issue="misaligned: no temporal overlap",
            fill_rate_delta=None,
        ),
    )
    assert aligned.gate.verdict == "pass"
    assert misaligned.gate.verdict == "fail"
    assert (
        aligned.gate.verdict_fingerprint != misaligned.gate.verdict_fingerprint
    )
