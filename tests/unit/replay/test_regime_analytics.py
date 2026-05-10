"""Unit tests for core.replay.regime_analytics (#1846).

Covers:
  - KNOWN_REGIME_IDS and UNKNOWN_REGIME sentinel
  - RegimeKPIRecord validation
  - compute_regime_scorecard: empty input, single/multi-regime, fill_rate,
    unknown/non-canonical regime counting, segment ordering, fingerprint
    determinism
  - write_regime_scorecard_artifact: artifact creation, content validity
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from core.replay.regime_analytics import (
    KNOWN_REGIME_IDS,
    UNKNOWN_REGIME,
    RegimeAnalyticsError,
    RegimeKPIRecord,
    RegimeScorecard,
    compute_regime_scorecard,
    write_regime_scorecard_artifact,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _record(
    regime_id: str,
    *,
    signal_count: int = 1,
    fill_count: int = 1,
    reject_count: int = 0,
    pnl_sum: str = "0",
) -> RegimeKPIRecord:
    return RegimeKPIRecord(
        regime_id=regime_id,
        signal_count=signal_count,
        fill_count=fill_count,
        reject_count=reject_count,
        pnl_sum=Decimal(pnl_sum),
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_known_regime_ids_contains_all_four(self):
        assert KNOWN_REGIME_IDS == frozenset(
            {"TREND", "RANGE", "HIGH_VOL_CHAOTIC", "UNKNOWN"}
        )

    def test_unknown_regime_sentinel_not_in_known_ids(self):
        """UNKNOWN_REGIME is the analytics sentinel, not the regime service label."""
        assert UNKNOWN_REGIME not in KNOWN_REGIME_IDS

    def test_unknown_regime_sentinel_value(self):
        assert UNKNOWN_REGIME == "__unknown__"


# ---------------------------------------------------------------------------
# RegimeKPIRecord validation
# ---------------------------------------------------------------------------


class TestRegimeKPIRecord:
    def test_valid_record(self):
        r = _record("TREND", signal_count=3, fill_count=2, reject_count=1, pnl_sum="1.5")
        assert r.regime_id == "TREND"
        assert r.signal_count == 3
        assert r.fill_count == 2
        assert r.reject_count == 1
        assert r.pnl_sum == Decimal("1.5")

    def test_empty_regime_id_raises(self):
        with pytest.raises(RegimeAnalyticsError, match="regime_id"):
            RegimeKPIRecord(
                regime_id="",
                signal_count=0,
                fill_count=0,
                reject_count=0,
                pnl_sum=Decimal("0"),
            )

    def test_negative_signal_count_raises(self):
        with pytest.raises(RegimeAnalyticsError, match="signal_count"):
            _record("TREND", signal_count=-1)

    def test_negative_fill_count_raises(self):
        with pytest.raises(RegimeAnalyticsError, match="fill_count"):
            _record("TREND", fill_count=-1)

    def test_negative_reject_count_raises(self):
        with pytest.raises(RegimeAnalyticsError, match="reject_count"):
            _record("TREND", reject_count=-1)

    def test_bool_signal_count_raises(self):
        with pytest.raises(RegimeAnalyticsError, match="signal_count"):
            RegimeKPIRecord(
                regime_id="TREND",
                signal_count=True,  # bool subclasses int but must be rejected
                fill_count=0,
                reject_count=0,
                pnl_sum=Decimal("0"),
            )

    def test_float_pnl_raises(self):
        with pytest.raises(RegimeAnalyticsError, match="pnl_sum"):
            RegimeKPIRecord(
                regime_id="TREND",
                signal_count=0,
                fill_count=0,
                reject_count=0,
                pnl_sum=1.5,  # type: ignore[arg-type]
            )

    def test_unknown_regime_sentinel_is_valid_record(self):
        """Callers may use UNKNOWN_REGIME as regime_id — it must be accepted."""
        r = _record(UNKNOWN_REGIME)
        assert r.regime_id == UNKNOWN_REGIME


# ---------------------------------------------------------------------------
# compute_regime_scorecard — empty input
# ---------------------------------------------------------------------------


class TestComputeRegimeScorecardEmpty:
    def test_empty_records_gives_valid_scorecard(self):
        sc = compute_regime_scorecard([], run_id="run-001")
        assert sc.run_id == "run-001"
        assert sc.total_records == 0
        assert sc.segments == ()
        assert sc.unknown_regime_count == 0
        assert isinstance(sc.input_fingerprint, str)
        assert len(sc.input_fingerprint) == 64  # SHA-256 hex

    def test_empty_records_fingerprint_is_deterministic(self):
        sc1 = compute_regime_scorecard([], run_id="r1")
        sc2 = compute_regime_scorecard([], run_id="r1")
        assert sc1.input_fingerprint == sc2.input_fingerprint

    def test_invalid_run_id_raises(self):
        with pytest.raises(RegimeAnalyticsError, match="run_id"):
            compute_regime_scorecard([], run_id="")

    def test_whitespace_run_id_raises(self):
        with pytest.raises(RegimeAnalyticsError, match="run_id"):
            compute_regime_scorecard([], run_id="   ")


# ---------------------------------------------------------------------------
# compute_regime_scorecard — single regime
# ---------------------------------------------------------------------------


class TestComputeRegimeScorecardSingle:
    def test_single_known_regime_segment(self):
        records = [_record("TREND", signal_count=5, fill_count=3, reject_count=2, pnl_sum="10")]
        sc = compute_regime_scorecard(records, run_id="run-a")
        assert sc.total_records == 1
        assert sc.unknown_regime_count == 0
        assert len(sc.segments) == 1
        seg = sc.segments[0]
        assert seg.regime_id == "TREND"
        assert seg.record_count == 1
        assert seg.signal_count == 5
        assert seg.fill_count == 3
        assert seg.reject_count == 2
        assert seg.pnl_sum == Decimal("10").quantize(Decimal("0.00000001"))

    def test_fill_rate_calculation(self):
        records = [_record("RANGE", fill_count=3, reject_count=1)]
        sc = compute_regime_scorecard(records, run_id="r")
        seg = sc.segments[0]
        # 3 / (3 + 1) = 0.75
        assert seg.fill_rate == Decimal("0.75000000")

    def test_fill_rate_zero_when_no_fills_or_rejects(self):
        records = [_record("RANGE", fill_count=0, reject_count=0)]
        sc = compute_regime_scorecard(records, run_id="r")
        assert sc.segments[0].fill_rate == Decimal("0.00000000")

    def test_fill_rate_one_when_no_rejects(self):
        records = [_record("TREND", fill_count=5, reject_count=0)]
        sc = compute_regime_scorecard(records, run_id="r")
        assert sc.segments[0].fill_rate == Decimal("1.00000000")

    def test_fill_rate_zero_when_no_fills(self):
        records = [_record("TREND", fill_count=0, reject_count=3)]
        sc = compute_regime_scorecard(records, run_id="r")
        assert sc.segments[0].fill_rate == Decimal("0.00000000")


# ---------------------------------------------------------------------------
# compute_regime_scorecard — all four known regimes
# ---------------------------------------------------------------------------


class TestComputeRegimeScorecardAllKnown:
    def test_all_four_known_regimes_in_scorecard(self):
        records = [_record(rid) for rid in sorted(KNOWN_REGIME_IDS)]
        sc = compute_regime_scorecard(records, run_id="run-all")
        segment_ids = {seg.regime_id for seg in sc.segments}
        assert segment_ids == KNOWN_REGIME_IDS
        assert sc.unknown_regime_count == 0
        assert sc.total_records == 4

    def test_segments_are_sorted_by_regime_id(self):
        records = [_record("TREND"), _record("RANGE"), _record("HIGH_VOL_CHAOTIC")]
        sc = compute_regime_scorecard(records, run_id="r")
        ids = [seg.regime_id for seg in sc.segments]
        assert ids == sorted(ids)

    def test_multi_record_aggregation(self):
        records = [
            _record("TREND", signal_count=2, fill_count=1, reject_count=0, pnl_sum="5"),
            _record("TREND", signal_count=3, fill_count=2, reject_count=1, pnl_sum="7"),
        ]
        sc = compute_regime_scorecard(records, run_id="r")
        assert len(sc.segments) == 1
        seg = sc.segments[0]
        assert seg.record_count == 2
        assert seg.signal_count == 5
        assert seg.fill_count == 3
        assert seg.reject_count == 1
        # pnl: 5 + 7 = 12
        assert seg.pnl_sum == Decimal("12.00000000")
        # fill_rate: 3 / (3 + 1) = 0.75
        assert seg.fill_rate == Decimal("0.75000000")


# ---------------------------------------------------------------------------
# compute_regime_scorecard — unknown/non-canonical regime IDs
# ---------------------------------------------------------------------------


class TestComputeRegimeScorecardUnknown:
    def test_unknown_regime_sentinel_counted_as_unknown(self):
        records = [_record(UNKNOWN_REGIME)]
        sc = compute_regime_scorecard(records, run_id="r")
        assert sc.unknown_regime_count == 1
        # still appears in segments (not silently dropped)
        assert any(seg.regime_id == UNKNOWN_REGIME for seg in sc.segments)

    def test_non_canonical_regime_id_counted_as_unknown(self):
        records = [_record("CUSTOM_REGIME"), _record("TREND")]
        sc = compute_regime_scorecard(records, run_id="r")
        assert sc.unknown_regime_count == 1
        assert sc.total_records == 2

    def test_multiple_unknown_regimes_all_counted(self):
        records = [_record(UNKNOWN_REGIME), _record("NOT_A_REGIME"), _record("TREND")]
        sc = compute_regime_scorecard(records, run_id="r")
        assert sc.unknown_regime_count == 2

    def test_known_unknown_regime_label_not_counted_as_analytics_unknown(self):
        """The regime service label 'UNKNOWN' is a known regime ID — not analytics unknown."""
        records = [_record("UNKNOWN")]
        sc = compute_regime_scorecard(records, run_id="r")
        assert sc.unknown_regime_count == 0
        assert sc.segments[0].regime_id == "UNKNOWN"

    def test_unknown_regimes_visible_in_segments(self):
        """Non-canonical regime IDs must appear in segments, not be silently dropped."""
        records = [_record(UNKNOWN_REGIME), _record("WEIRD")]
        sc = compute_regime_scorecard(records, run_id="r")
        segment_ids = {seg.regime_id for seg in sc.segments}
        assert UNKNOWN_REGIME in segment_ids
        assert "WEIRD" in segment_ids


# ---------------------------------------------------------------------------
# compute_regime_scorecard — fingerprint determinism
# ---------------------------------------------------------------------------


class TestFingerprintDeterminism:
    def test_same_inputs_same_fingerprint(self):
        records_a = [_record("TREND", fill_count=2), _record("RANGE", fill_count=1)]
        records_b = [_record("TREND", fill_count=2), _record("RANGE", fill_count=1)]
        sc_a = compute_regime_scorecard(records_a, run_id="run-fp")
        sc_b = compute_regime_scorecard(records_b, run_id="run-fp")
        assert sc_a.input_fingerprint == sc_b.input_fingerprint

    def test_different_records_different_fingerprint(self):
        records_a = [_record("TREND", fill_count=2)]
        records_b = [_record("TREND", fill_count=3)]
        sc_a = compute_regime_scorecard(records_a, run_id="r")
        sc_b = compute_regime_scorecard(records_b, run_id="r")
        assert sc_a.input_fingerprint != sc_b.input_fingerprint

    def test_different_run_id_same_records_same_fingerprint(self):
        """Fingerprint covers only records, not run_id."""
        records = [_record("TREND")]
        sc_a = compute_regime_scorecard(records, run_id="run-1")
        sc_b = compute_regime_scorecard(records, run_id="run-2")
        assert sc_a.input_fingerprint == sc_b.input_fingerprint

    def test_order_sensitive_fingerprint(self):
        """Order of records is reflected in the fingerprint."""
        r1 = _record("TREND", pnl_sum="1")
        r2 = _record("RANGE", pnl_sum="2")
        sc_fwd = compute_regime_scorecard([r1, r2], run_id="r")
        sc_rev = compute_regime_scorecard([r2, r1], run_id="r")
        assert sc_fwd.input_fingerprint != sc_rev.input_fingerprint

    def test_fingerprint_is_64_char_hex(self):
        sc = compute_regime_scorecard([_record("TREND")], run_id="r")
        assert len(sc.input_fingerprint) == 64
        assert all(c in "0123456789abcdef" for c in sc.input_fingerprint)


# ---------------------------------------------------------------------------
# write_regime_scorecard_artifact
# ---------------------------------------------------------------------------


class TestWriteRegimeScorecardArtifact:
    def _simple_scorecard(self, run_id: str = "run-write") -> RegimeScorecard:
        return compute_regime_scorecard(
            [_record("TREND", fill_count=2, reject_count=1, pnl_sum="5.5")],
            run_id=run_id,
        )

    def test_writes_regime_scorecard_json(self, tmp_path: Path):
        sc = self._simple_scorecard()
        write_regime_scorecard_artifact(sc, tmp_path)
        artifact = tmp_path / "regime_scorecard.json"
        assert artifact.exists()

    def test_artifact_is_valid_json(self, tmp_path: Path):
        sc = self._simple_scorecard()
        write_regime_scorecard_artifact(sc, tmp_path)
        content = json.loads((tmp_path / "regime_scorecard.json").read_text())
        assert isinstance(content, dict)

    def test_artifact_contains_expected_top_level_keys(self, tmp_path: Path):
        sc = self._simple_scorecard()
        write_regime_scorecard_artifact(sc, tmp_path)
        content = json.loads((tmp_path / "regime_scorecard.json").read_text())
        assert "run_id" in content
        assert "total_records" in content
        assert "unknown_regime_count" in content
        assert "input_fingerprint" in content
        assert "segments" in content

    def test_artifact_run_id_matches(self, tmp_path: Path):
        sc = self._simple_scorecard(run_id="my-run-42")
        write_regime_scorecard_artifact(sc, tmp_path)
        content = json.loads((tmp_path / "regime_scorecard.json").read_text())
        assert content["run_id"] == "my-run-42"

    def test_artifact_segments_contain_regime_id(self, tmp_path: Path):
        sc = self._simple_scorecard()
        write_regime_scorecard_artifact(sc, tmp_path)
        content = json.loads((tmp_path / "regime_scorecard.json").read_text())
        assert len(content["segments"]) == 1
        assert content["segments"][0]["regime_id"] == "TREND"

    def test_artifact_pnl_sum_is_string(self, tmp_path: Path):
        """pnl_sum must be serialized as a string (no-float rule)."""
        sc = self._simple_scorecard()
        write_regime_scorecard_artifact(sc, tmp_path)
        content = json.loads((tmp_path / "regime_scorecard.json").read_text())
        assert isinstance(content["segments"][0]["pnl_sum"], str)

    def test_artifact_fill_rate_is_string(self, tmp_path: Path):
        """fill_rate must be serialized as a string (no-float rule)."""
        sc = self._simple_scorecard()
        write_regime_scorecard_artifact(sc, tmp_path)
        content = json.loads((tmp_path / "regime_scorecard.json").read_text())
        assert isinstance(content["segments"][0]["fill_rate"], str)

    def test_creates_artifact_root_if_not_exists(self, tmp_path: Path):
        nested = tmp_path / "a" / "b" / "c"
        sc = self._simple_scorecard()
        write_regime_scorecard_artifact(sc, nested)
        assert (nested / "regime_scorecard.json").exists()

    def test_accepts_string_path(self, tmp_path: Path):
        sc = self._simple_scorecard()
        write_regime_scorecard_artifact(sc, str(tmp_path))
        assert (tmp_path / "regime_scorecard.json").exists()

    def test_artifact_is_deterministic(self, tmp_path: Path):
        """Same scorecard written twice produces identical bytes."""
        sc = self._simple_scorecard()
        path_a = tmp_path / "a"
        path_b = tmp_path / "b"
        write_regime_scorecard_artifact(sc, path_a)
        write_regime_scorecard_artifact(sc, path_b)
        assert (path_a / "regime_scorecard.json").read_bytes() == (
            path_b / "regime_scorecard.json"
        ).read_bytes()

    def test_empty_scorecard_artifact_is_valid(self, tmp_path: Path):
        sc = compute_regime_scorecard([], run_id="empty-run")
        write_regime_scorecard_artifact(sc, tmp_path)
        content = json.loads((tmp_path / "regime_scorecard.json").read_text())
        assert content["total_records"] == 0
        assert content["segments"] == []
        assert content["unknown_regime_count"] == 0
