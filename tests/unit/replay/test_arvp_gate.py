"""Unit tests for core/replay/arvp_gate.py."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from core.replay.arvp_gate import (
    ARVPEvidenceBundle,
    ARVPGateError,
    ARVPGateVerdict,
    build_arvp_gate_verdict,
    write_gate_verdict_artifact,
)
from core.replay.regime_analytics import RegimeScorecard, RegimeSegmentStats
from core.replay.run_registry import ReplayRunRecord
from core.replay.scenario_harness import ScenarioGroupManifest, ScenarioRunResult
from core.replay.shadow_compare import ShadowComparisonResult


# ---------------------------------------------------------------------------
# Test fixture helpers
# ---------------------------------------------------------------------------


def _make_record(**overrides) -> ReplayRunRecord:
    defaults = {
        "run_id": "replay-0123456789ab-0001",
        "status": "completed",
        "mode": "baseline",
        "strategy_id": "primary_breakout_v1",
        "symbol": "BTCUSDT",
        "dataset_fingerprint": "a" * 64,
        "scheduler_profile": "2x",
        "execution_provenance_id": "bt-0123456789abcdef",
        "artifact_root": "artifacts/replay_reports/replay-0123456789ab-0001",
        "deterministic_replay_ok": True,
        "failure_reason": None,
        "started_at_utc": "2026-04-22T14:00:00+00:00",
        "finished_at_utc": "2026-04-22T14:00:05+00:00",
    }
    defaults.update(overrides)
    return ReplayRunRecord(**defaults)


def _make_failed_record(**overrides) -> ReplayRunRecord:
    return _make_record(
        status="failed",
        failure_reason="deterministic_verify_mismatch",
        finished_at_utc="2026-04-22T14:00:05+00:00",
        **overrides,
    )


def _make_running_record(**overrides) -> ReplayRunRecord:
    return _make_record(
        status="running",
        finished_at_utc=None,
        **overrides,
    )


def _make_manifest(
    total: int = 3,
    succeeded: int = 2,
    failed: int = 1,
) -> ScenarioGroupManifest:
    results = []
    for i in range(succeeded):
        results.append(
            ScenarioRunResult(
                scenario_id=f"scenario_{i}",
                exit_code=0,
            )
        )
    for i in range(failed):
        results.append(
            ScenarioRunResult(
                scenario_id=f"scenario_fail_{i}",
                exit_code=1,
                failure_reason="signal_count_mismatch",
            )
        )
    return ScenarioGroupManifest(
        group_id="sg-test123456ab",
        scenario_results=tuple(results),
        artifact_root="artifacts/replay_reports/groups/sg-test123456ab",
        group_fingerprint="b" * 64,
        started_at_utc="2026-04-22T14:00:00+00:00",
        finished_at_utc="2026-04-22T14:00:10+00:00",
        total_scenarios=total,
        succeeded_count=succeeded,
        failed_count=failed,
    )


def _make_scorecard(
    unknown_regime_count: int = 0,
    total_records: int = 100,
) -> RegimeScorecard:
    seg = RegimeSegmentStats(
        regime_id="TREND",
        record_count=total_records,
        signal_count=50,
        fill_count=40,
        reject_count=10,
        pnl_sum=Decimal("1.23456789"),
        fill_rate=Decimal("0.80000000"),
    )
    return RegimeScorecard(
        run_id="replay-0123456789ab-0001",
        segments=(seg,),
        total_records=total_records,
        unknown_regime_count=unknown_regime_count,
        input_fingerprint="c" * 64,
    )


def _make_shadow(
    alignment_issue: str | None = None,
    fill_rate_delta: Decimal = Decimal("0.01000000"),
    signal_count_delta: int = -2,
    fill_count_delta: int = -1,
) -> ShadowComparisonResult:
    return ShadowComparisonResult(
        comparison_fingerprint="d" * 64,
        status="aligned" if alignment_issue is None else "misaligned",
        alignment_issue=alignment_issue,
        replay_run_id="replay-0123456789ab-0001",
        paper_provenance_id="paper-ref-001",
        symbol="BTCUSDT",
        strategy_id="primary_breakout_v1",
        signal_count_delta=signal_count_delta,
        fill_count_delta=fill_count_delta,
        reject_count_delta=0,
        fill_rate_replay=Decimal("0.85000000"),
        fill_rate_paper=Decimal("0.84000000"),
        fill_rate_delta=fill_rate_delta,
        window_start_utc_replay="2026-04-01T00:00:00+00:00",
        window_end_utc_replay="2026-04-22T00:00:00+00:00",
        window_start_utc_paper="2026-04-01T00:00:00+00:00",
        window_end_utc_paper="2026-04-22T00:00:00+00:00",
    )


# ---------------------------------------------------------------------------
# TestARVPEvidenceBundle
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestARVPEvidenceBundle:
    def test_minimal_bundle_ok(self) -> None:
        record = _make_record()
        bundle = ARVPEvidenceBundle(record=record)
        assert bundle.record is record
        assert bundle.manifest is None
        assert bundle.scorecard is None
        assert bundle.shadow is None

    def test_full_bundle_ok(self) -> None:
        record = _make_record()
        manifest = _make_manifest()
        scorecard = _make_scorecard()
        shadow = _make_shadow()
        bundle = ARVPEvidenceBundle(
            record=record, manifest=manifest, scorecard=scorecard, shadow=shadow
        )
        assert bundle.manifest is manifest
        assert bundle.scorecard is scorecard
        assert bundle.shadow is shadow

    def test_invalid_record_type_raises(self) -> None:
        with pytest.raises(ARVPGateError, match="record must be a ReplayRunRecord"):
            ARVPEvidenceBundle(record="not_a_record")  # type: ignore[arg-type]

    def test_invalid_manifest_type_raises(self) -> None:
        with pytest.raises(ARVPGateError, match="manifest must be ScenarioGroupManifest"):
            ARVPEvidenceBundle(record=_make_record(), manifest="wrong")  # type: ignore[arg-type]

    def test_invalid_scorecard_type_raises(self) -> None:
        with pytest.raises(ARVPGateError, match="scorecard must be RegimeScorecard"):
            ARVPEvidenceBundle(record=_make_record(), scorecard=42)  # type: ignore[arg-type]

    def test_invalid_shadow_type_raises(self) -> None:
        with pytest.raises(ARVPGateError, match="shadow must be ShadowComparisonResult"):
            ARVPEvidenceBundle(record=_make_record(), shadow=object())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestBuildARVPGateVerdictPassPath
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildARVPGateVerdictPassPath:
    def test_completed_deterministic_ok_is_pass(self) -> None:
        bundle = ARVPEvidenceBundle(record=_make_record())
        verdict = build_arvp_gate_verdict(bundle)
        assert verdict.verdict == "pass"
        assert verdict.run_id == "replay-0123456789ab-0001"
        assert verdict.required_artifacts_present is True
        assert verdict.blocking_findings == ()

    def test_pass_verdict_has_no_blocking_findings(self) -> None:
        bundle = ARVPEvidenceBundle(record=_make_record())
        verdict = build_arvp_gate_verdict(bundle)
        assert len(verdict.blocking_findings) == 0

    def test_pass_verdict_has_verdict_fingerprint(self) -> None:
        bundle = ARVPEvidenceBundle(record=_make_record())
        verdict = build_arvp_gate_verdict(bundle)
        assert len(verdict.verdict_fingerprint) == 64
        assert all(c in "0123456789abcdef" for c in verdict.verdict_fingerprint)

    def test_non_bundle_type_raises(self) -> None:
        with pytest.raises(ARVPGateError, match="bundle must be ARVPEvidenceBundle"):
            build_arvp_gate_verdict("not_a_bundle")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestBuildARVPGateVerdictFailPaths
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildARVPGateVerdictFailPaths:
    def test_failed_record_is_fail(self) -> None:
        bundle = ARVPEvidenceBundle(record=_make_failed_record())
        verdict = build_arvp_gate_verdict(bundle)
        assert verdict.verdict == "fail"

    def test_failed_record_has_blocking_finding(self) -> None:
        bundle = ARVPEvidenceBundle(record=_make_failed_record())
        verdict = build_arvp_gate_verdict(bundle)
        assert any("run_failed" in f for f in verdict.blocking_findings)

    def test_failed_record_blocking_finding_contains_reason(self) -> None:
        # _make_failed_record uses "deterministic_verify_mismatch" as default reason.
        bundle = ARVPEvidenceBundle(record=_make_failed_record())
        verdict = build_arvp_gate_verdict(bundle)
        assert any(
            "deterministic_verify_mismatch" in f for f in verdict.blocking_findings
        )

    def test_determinism_false_is_fail(self) -> None:
        bundle = ARVPEvidenceBundle(
            record=_make_record(deterministic_replay_ok=False)
        )
        verdict = build_arvp_gate_verdict(bundle)
        assert verdict.verdict == "fail"

    def test_determinism_false_has_blocking_finding(self) -> None:
        bundle = ARVPEvidenceBundle(
            record=_make_record(deterministic_replay_ok=False)
        )
        verdict = build_arvp_gate_verdict(bundle)
        assert any("determinism_check_failed" in f for f in verdict.blocking_findings)

    def test_shadow_alignment_issue_is_fail(self) -> None:
        shadow = _make_shadow(alignment_issue="symbol mismatch: BTCUSDT vs ETHUSDT")
        bundle = ARVPEvidenceBundle(record=_make_record(), shadow=shadow)
        verdict = build_arvp_gate_verdict(bundle)
        assert verdict.verdict == "fail"

    def test_shadow_alignment_issue_blocking_finding_contains_issue(self) -> None:
        shadow = _make_shadow(alignment_issue="misaligned: no temporal overlap")
        bundle = ARVPEvidenceBundle(record=_make_record(), shadow=shadow)
        verdict = build_arvp_gate_verdict(bundle)
        assert any(
            "misaligned: no temporal overlap" in f for f in verdict.blocking_findings
        )

    def test_multiple_blocking_findings_all_captured(self) -> None:
        bundle = ARVPEvidenceBundle(
            record=_make_failed_record(deterministic_replay_ok=False)
        )
        verdict = build_arvp_gate_verdict(bundle)
        assert verdict.verdict == "fail"
        # both run_failed and determinism_check_failed must be present
        blocking_str = " ".join(verdict.blocking_findings)
        assert "run_failed" in blocking_str
        assert "determinism_check_failed" in blocking_str

    def test_fail_verdict_has_no_informational_from_shadow_when_blocking(self) -> None:
        shadow = _make_shadow(alignment_issue="misaligned: no overlap")
        bundle = ARVPEvidenceBundle(record=_make_record(), shadow=shadow)
        verdict = build_arvp_gate_verdict(bundle)
        # shadow with alignment_issue → blocking, NOT informational
        assert not any("shadow_comparison:" in f for f in verdict.informational_findings)


# ---------------------------------------------------------------------------
# TestBuildARVPGateVerdictBlockedPath
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildARVPGateVerdictBlockedPath:
    def test_running_record_is_blocked(self) -> None:
        bundle = ARVPEvidenceBundle(record=_make_running_record())
        verdict = build_arvp_gate_verdict(bundle)
        assert verdict.verdict == "blocked"

    def test_blocked_verdict_has_no_findings(self) -> None:
        bundle = ARVPEvidenceBundle(record=_make_running_record())
        verdict = build_arvp_gate_verdict(bundle)
        assert verdict.blocking_findings == ()
        assert verdict.informational_findings == ()

    def test_blocked_verdict_required_artifacts_present(self) -> None:
        bundle = ARVPEvidenceBundle(record=_make_running_record())
        verdict = build_arvp_gate_verdict(bundle)
        assert verdict.required_artifacts_present is True

    def test_blocked_verdict_has_fingerprint(self) -> None:
        bundle = ARVPEvidenceBundle(record=_make_running_record())
        verdict = build_arvp_gate_verdict(bundle)
        assert len(verdict.verdict_fingerprint) == 64


# ---------------------------------------------------------------------------
# TestInformationalFindings
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInformationalFindings:
    def test_manifest_produces_informational_finding(self) -> None:
        manifest = _make_manifest(total=3, succeeded=2, failed=1)
        bundle = ARVPEvidenceBundle(record=_make_record(), manifest=manifest)
        verdict = build_arvp_gate_verdict(bundle)
        assert verdict.verdict == "pass"
        assert any("scenario_group" in f for f in verdict.informational_findings)

    def test_manifest_informational_contains_group_id(self) -> None:
        manifest = _make_manifest()
        bundle = ARVPEvidenceBundle(record=_make_record(), manifest=manifest)
        verdict = build_arvp_gate_verdict(bundle)
        assert any("sg-test123456ab" in f for f in verdict.informational_findings)

    def test_manifest_informational_contains_counts(self) -> None:
        manifest = _make_manifest(total=3, succeeded=2, failed=1)
        bundle = ARVPEvidenceBundle(record=_make_record(), manifest=manifest)
        verdict = build_arvp_gate_verdict(bundle)
        info_str = " ".join(verdict.informational_findings)
        assert "total=3" in info_str
        assert "succeeded=2" in info_str
        assert "failed=1" in info_str

    def test_scorecard_with_unknowns_produces_advisory(self) -> None:
        scorecard = _make_scorecard(unknown_regime_count=5)
        bundle = ARVPEvidenceBundle(record=_make_record(), scorecard=scorecard)
        verdict = build_arvp_gate_verdict(bundle)
        assert verdict.verdict == "pass"
        assert any(
            "unknown_regime_count=5" in f for f in verdict.informational_findings
        )

    def test_scorecard_without_unknowns_produces_stats_finding(self) -> None:
        scorecard = _make_scorecard(unknown_regime_count=0, total_records=100)
        bundle = ARVPEvidenceBundle(record=_make_record(), scorecard=scorecard)
        verdict = build_arvp_gate_verdict(bundle)
        assert any("total_records=100" in f for f in verdict.informational_findings)

    def test_aligned_shadow_produces_informational_finding(self) -> None:
        shadow = _make_shadow(alignment_issue=None)
        bundle = ARVPEvidenceBundle(record=_make_record(), shadow=shadow)
        verdict = build_arvp_gate_verdict(bundle)
        assert verdict.verdict == "pass"
        assert any("shadow_comparison:" in f for f in verdict.informational_findings)

    def test_aligned_shadow_informational_contains_fill_rate_delta(self) -> None:
        shadow = _make_shadow(
            alignment_issue=None, fill_rate_delta=Decimal("0.01000000")
        )
        bundle = ARVPEvidenceBundle(record=_make_record(), shadow=shadow)
        verdict = build_arvp_gate_verdict(bundle)
        assert any("fill_rate_delta" in f for f in verdict.informational_findings)

    def test_aligned_shadow_informational_contains_signal_count_delta(self) -> None:
        shadow = _make_shadow(
            alignment_issue=None, signal_count_delta=-3
        )
        bundle = ARVPEvidenceBundle(record=_make_record(), shadow=shadow)
        verdict = build_arvp_gate_verdict(bundle)
        assert any(
            "signal_count_delta=-3" in f for f in verdict.informational_findings
        )

    def test_no_optional_artifacts_yields_empty_informational(self) -> None:
        bundle = ARVPEvidenceBundle(record=_make_record())
        verdict = build_arvp_gate_verdict(bundle)
        assert verdict.informational_findings == ()

    def test_all_optional_artifacts_populate_informational(self) -> None:
        bundle = ARVPEvidenceBundle(
            record=_make_record(),
            manifest=_make_manifest(),
            scorecard=_make_scorecard(),
            shadow=_make_shadow(),
        )
        verdict = build_arvp_gate_verdict(bundle)
        assert verdict.verdict == "pass"
        assert len(verdict.informational_findings) == 3  # manifest, scorecard, shadow

    def test_informational_findings_not_blocking(self) -> None:
        bundle = ARVPEvidenceBundle(
            record=_make_record(),
            manifest=_make_manifest(),
            scorecard=_make_scorecard(unknown_regime_count=10),
            shadow=_make_shadow(),
        )
        verdict = build_arvp_gate_verdict(bundle)
        assert verdict.verdict == "pass"
        assert verdict.blocking_findings == ()


# ---------------------------------------------------------------------------
# TestDeterminism
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeterminism:
    def test_identical_inputs_produce_identical_fingerprint(self) -> None:
        bundle1 = ARVPEvidenceBundle(record=_make_record())
        bundle2 = ARVPEvidenceBundle(record=_make_record())
        v1 = build_arvp_gate_verdict(bundle1)
        v2 = build_arvp_gate_verdict(bundle2)
        assert v1.verdict_fingerprint == v2.verdict_fingerprint

    def test_different_verdict_produces_different_fingerprint(self) -> None:
        pass_bundle = ARVPEvidenceBundle(record=_make_record())
        fail_bundle = ARVPEvidenceBundle(
            record=_make_record(deterministic_replay_ok=False)
        )
        vp = build_arvp_gate_verdict(pass_bundle)
        vf = build_arvp_gate_verdict(fail_bundle)
        assert vp.verdict_fingerprint != vf.verdict_fingerprint

    def test_different_run_id_produces_different_fingerprint(self) -> None:
        bundle1 = ARVPEvidenceBundle(record=_make_record(run_id="replay-0123456789ab-0001"))
        bundle2 = ARVPEvidenceBundle(record=_make_record(run_id="replay-0123456789ab-0002"))
        v1 = build_arvp_gate_verdict(bundle1)
        v2 = build_arvp_gate_verdict(bundle2)
        assert v1.verdict_fingerprint != v2.verdict_fingerprint

    def test_blocked_fingerprint_is_stable(self) -> None:
        bundle1 = ARVPEvidenceBundle(record=_make_running_record())
        bundle2 = ARVPEvidenceBundle(record=_make_running_record())
        v1 = build_arvp_gate_verdict(bundle1)
        v2 = build_arvp_gate_verdict(bundle2)
        assert v1.verdict_fingerprint == v2.verdict_fingerprint

    def test_informational_findings_included_in_fingerprint(self) -> None:
        bundle_no_info = ARVPEvidenceBundle(record=_make_record())
        bundle_with_info = ARVPEvidenceBundle(
            record=_make_record(), manifest=_make_manifest()
        )
        v1 = build_arvp_gate_verdict(bundle_no_info)
        v2 = build_arvp_gate_verdict(bundle_with_info)
        assert v1.verdict_fingerprint != v2.verdict_fingerprint


# ---------------------------------------------------------------------------
# TestARVPGateVerdict
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestARVPGateVerdict:
    def test_to_dict_has_expected_keys(self) -> None:
        bundle = ARVPEvidenceBundle(record=_make_record())
        verdict = build_arvp_gate_verdict(bundle)
        d = verdict.to_dict()
        assert set(d.keys()) == {
            "verdict",
            "run_id",
            "required_artifacts_present",
            "blocking_findings",
            "informational_findings",
            "verdict_fingerprint",
        }

    def test_to_dict_blocking_findings_is_list(self) -> None:
        bundle = ARVPEvidenceBundle(record=_make_failed_record())
        verdict = build_arvp_gate_verdict(bundle)
        d = verdict.to_dict()
        assert isinstance(d["blocking_findings"], list)

    def test_to_dict_informational_findings_is_list(self) -> None:
        bundle = ARVPEvidenceBundle(record=_make_record(), manifest=_make_manifest())
        verdict = build_arvp_gate_verdict(bundle)
        d = verdict.to_dict()
        assert isinstance(d["informational_findings"], list)

    def test_invalid_verdict_string_raises(self) -> None:
        with pytest.raises(ARVPGateError, match="verdict must be one of"):
            ARVPGateVerdict(
                verdict="unknown",
                run_id="replay-0123456789ab-0001",
                required_artifacts_present=True,
                blocking_findings=(),
                informational_findings=(),
                verdict_fingerprint="e" * 64,
            )


# ---------------------------------------------------------------------------
# TestWriteGateVerdictArtifact
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWriteGateVerdictArtifact:
    def _build_pass_verdict(self) -> ARVPGateVerdict:
        return build_arvp_gate_verdict(
            ARVPEvidenceBundle(record=_make_record())
        )

    def test_writes_file_in_artifact_root(self, tmp_path: Path) -> None:
        verdict = self._build_pass_verdict()
        write_gate_verdict_artifact(verdict, tmp_path)
        assert (tmp_path / "arvp_gate_verdict.json").exists()

    def test_written_file_is_valid_json(self, tmp_path: Path) -> None:
        verdict = self._build_pass_verdict()
        write_gate_verdict_artifact(verdict, tmp_path)
        content = (tmp_path / "arvp_gate_verdict.json").read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    def test_written_json_verdict_matches(self, tmp_path: Path) -> None:
        verdict = self._build_pass_verdict()
        write_gate_verdict_artifact(verdict, tmp_path)
        content = (tmp_path / "arvp_gate_verdict.json").read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed["verdict"] == "pass"
        assert parsed["run_id"] == verdict.run_id
        assert parsed["required_artifacts_present"] is True

    def test_written_json_contains_fingerprint(self, tmp_path: Path) -> None:
        verdict = self._build_pass_verdict()
        write_gate_verdict_artifact(verdict, tmp_path)
        content = (tmp_path / "arvp_gate_verdict.json").read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed["verdict_fingerprint"] == verdict.verdict_fingerprint

    def test_creates_nested_artifact_root(self, tmp_path: Path) -> None:
        deep_root = tmp_path / "a" / "b" / "c"
        verdict = self._build_pass_verdict()
        write_gate_verdict_artifact(verdict, deep_root)
        assert (deep_root / "arvp_gate_verdict.json").exists()

    def test_fail_verdict_written_correctly(self, tmp_path: Path) -> None:
        bundle = ARVPEvidenceBundle(record=_make_failed_record())
        verdict = build_arvp_gate_verdict(bundle)
        write_gate_verdict_artifact(verdict, tmp_path)
        content = (tmp_path / "arvp_gate_verdict.json").read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed["verdict"] == "fail"
        assert len(parsed["blocking_findings"]) >= 1

    def test_fail_closed_on_io_error(self, tmp_path: Path) -> None:
        # Use a file path as artifact_root — mkdir on it raises OSError.
        blocking_file = tmp_path / "blocking_file.txt"
        blocking_file.write_text("not_a_dir", encoding="utf-8")
        verdict = self._build_pass_verdict()
        with pytest.raises(ARVPGateError, match="Failed to write gate verdict artifact"):
            write_gate_verdict_artifact(verdict, blocking_file)

    def test_wrong_verdict_type_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ARVPGateError, match="verdict must be ARVPGateVerdict"):
            write_gate_verdict_artifact("not_a_verdict", tmp_path)  # type: ignore[arg-type]

    def test_written_json_is_canonical_sorted_keys(self, tmp_path: Path) -> None:
        verdict = self._build_pass_verdict()
        write_gate_verdict_artifact(verdict, tmp_path)
        content = (tmp_path / "arvp_gate_verdict.json").read_text(encoding="utf-8")
        parsed = json.loads(content)
        keys = list(parsed.keys())
        assert keys == sorted(keys)
