"""Unit tests for core/replay/shadow_compare.py (#1848).

Coverage:
  - PaperReferenceWindow validation
  - ReplayOutputWindow validation
  - compare_windows: aligned, missing reference, symbol/strategy mismatch,
    non-overlapping windows, partial overlap, adjacent windows, zero counts
  - Deterministic fingerprint: identical inputs → same fingerprint;
    different inputs → different fingerprint
  - fill_rate_delta type and correctness
  - build_calibration_summary: content grounding
  - write_shadow_comparison_artifact: artifact written, fail-closed on I/O error
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from core.replay.shadow_compare import (
    PaperReferenceWindow,
    ReplayOutputWindow,
    ShadowCompareError,
    ShadowComparisonResult,
    build_calibration_summary,
    compare_windows,
    write_shadow_comparison_artifact,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_FP = "a" * 64  # valid 64-char hex dataset_fingerprint
_RUN_ID = "replay-aabbccddee11-0001"

_START = "2024-01-01T00:00:00+00:00"
_END = "2024-01-02T00:00:00+00:00"
_SYMBOL = "BTCUSDT"
_STRATEGY = "momentum-v1"


def _make_replay(**kw) -> ReplayOutputWindow:
    defaults = dict(
        run_id=_RUN_ID,
        symbol=_SYMBOL,
        strategy_id=_STRATEGY,
        window_start_utc=_START,
        window_end_utc=_END,
        signal_count=10,
        order_count=10,
        fill_count=8,
        actual_reject_count=2,
        inferred_unfilled_count=2,
        dataset_fingerprint=_FP,
    )
    defaults.update(kw)
    return ReplayOutputWindow(**defaults)


def _make_paper(**kw) -> PaperReferenceWindow:
    defaults = dict(
        symbol=_SYMBOL,
        strategy_id=_STRATEGY,
        window_start_utc=_START,
        window_end_utc=_END,
        signal_count=12,
        order_count=12,
        fill_count=9,
        actual_reject_count=3,
        inferred_unfilled_count=3,
        provenance_id="paper-run-001",
    )
    defaults.update(kw)
    return PaperReferenceWindow(**defaults)


# ---------------------------------------------------------------------------
# PaperReferenceWindow validation
# ---------------------------------------------------------------------------


class TestPaperReferenceWindow:
    def test_valid_construction(self):
        w = _make_paper()
        assert w.symbol == _SYMBOL
        assert w.strategy_id == _STRATEGY
        assert w.signal_count == 12

    def test_empty_symbol_raises(self):
        with pytest.raises(ShadowCompareError, match="symbol"):
            _make_paper(symbol="")

    def test_empty_strategy_id_raises(self):
        with pytest.raises(ShadowCompareError, match="strategy_id"):
            _make_paper(strategy_id="  ")

    def test_empty_provenance_id_raises(self):
        with pytest.raises(ShadowCompareError, match="provenance_id"):
            _make_paper(provenance_id="")

    def test_end_before_start_raises(self):
        with pytest.raises(ShadowCompareError, match="strictly after"):
            _make_paper(window_start_utc=_END, window_end_utc=_START)

    def test_equal_start_end_raises(self):
        with pytest.raises(ShadowCompareError, match="strictly after"):
            _make_paper(window_start_utc=_START, window_end_utc=_START)

    def test_missing_timezone_raises(self):
        with pytest.raises(ShadowCompareError, match="timezone"):
            _make_paper(window_start_utc="2024-01-01T00:00:00")

    def test_negative_signal_count_raises(self):
        with pytest.raises(ShadowCompareError, match="signal_count"):
            _make_paper(signal_count=-1)

    def test_negative_fill_count_raises(self):
        with pytest.raises(ShadowCompareError, match="fill_count"):
            _make_paper(fill_count=-1)

    def test_negative_order_count_raises(self):
        with pytest.raises(ShadowCompareError, match="order_count"):
            _make_paper(order_count=-1)

    def test_negative_unfilled_count_raises(self):
        with pytest.raises(ShadowCompareError, match="inferred_unfilled_count"):
            _make_paper(inferred_unfilled_count=-1)

    def test_bool_count_raises(self):
        with pytest.raises(ShadowCompareError, match="signal_count"):
            _make_paper(signal_count=True)

    # --- causal_signal_count (#3058) ---

    def test_causal_signal_count_valid_positive(self):
        w = _make_paper(causal_signal_count=3)
        assert w.causal_signal_count == 3

    def test_causal_signal_count_valid_zero(self):
        w = _make_paper(causal_signal_count=0)
        assert w.causal_signal_count == 0

    def test_causal_signal_count_negative_raises(self):
        with pytest.raises(ShadowCompareError, match="causal_signal_count"):
            _make_paper(causal_signal_count=-1)

    def test_causal_signal_count_bool_raises(self):
        with pytest.raises(ShadowCompareError, match="causal_signal_count"):
            _make_paper(causal_signal_count=True)

    def test_causal_signal_count_in_to_dict(self):
        w = _make_paper(causal_signal_count=2)
        d = w.to_dict()
        assert d["causal_signal_count"] == 2


# ---------------------------------------------------------------------------
# ReplayOutputWindow validation
# ---------------------------------------------------------------------------


class TestReplayOutputWindow:
    def test_valid_construction(self):
        w = _make_replay()
        assert w.run_id == _RUN_ID
        assert w.dataset_fingerprint == _FP

    def test_invalid_run_id_raises(self):
        with pytest.raises(ShadowCompareError, match="run_id"):
            _make_replay(run_id="not-valid")

    def test_invalid_dataset_fingerprint_raises(self):
        with pytest.raises(ShadowCompareError, match="dataset_fingerprint"):
            _make_replay(dataset_fingerprint="short")

    def test_uppercase_fingerprint_raises(self):
        with pytest.raises(ShadowCompareError, match="dataset_fingerprint"):
            _make_replay(dataset_fingerprint="A" * 64)

    def test_end_before_start_raises(self):
        with pytest.raises(ShadowCompareError, match="strictly after"):
            _make_replay(window_start_utc=_END, window_end_utc=_START)

    def test_negative_count_raises(self):
        with pytest.raises(ShadowCompareError, match="fill_count"):
            _make_replay(fill_count=-1)

    def test_negative_order_count_raises(self):
        with pytest.raises(ShadowCompareError, match="order_count"):
            _make_replay(order_count=-1)

    def test_bool_count_raises(self):
        with pytest.raises(ShadowCompareError, match="inferred_unfilled_count"):
            _make_replay(inferred_unfilled_count=False)


# ---------------------------------------------------------------------------
# compare_windows: success path
# ---------------------------------------------------------------------------


class TestCompareWindowsAligned:
    def test_status_is_aligned(self):
        result = compare_windows(_make_replay(), _make_paper())
        assert result.status == "aligned"

    def test_alignment_issue_is_none(self):
        result = compare_windows(_make_replay(), _make_paper())
        assert result.alignment_issue is None

    def test_signal_count_delta(self):
        result = compare_windows(_make_replay(), _make_paper())
        # replay=10, paper=12  →  10 - 12 = -2
        assert result.signal_count_delta == -2

    def test_fill_count_delta(self):
        result = compare_windows(_make_replay(), _make_paper())
        # replay=8, paper=9  →  8 - 9 = -1
        assert result.fill_count_delta == -1

    def test_actual_reject_count_delta(self):
        result = compare_windows(_make_replay(), _make_paper())
        # replay=2, paper=3  →  2 - 3 = -1
        assert result.actual_reject_count_delta == -1

    def test_inferred_unfilled_count_delta(self):
        result = compare_windows(_make_replay(), _make_paper())
        # replay=2, paper=3  →  2 - 3 = -1
        assert result.inferred_unfilled_count_delta == -1

    def test_fill_rate_replay(self):
        result = compare_windows(_make_replay(), _make_paper())
        # replay: 8 / (8+2) = 0.8
        assert result.fill_rate_replay == Decimal("0.80000000")

    def test_fill_rate_paper(self):
        result = compare_windows(_make_replay(), _make_paper())
        # paper: 9 / (9+3) = 0.75
        assert result.fill_rate_paper == Decimal("0.75000000")

    def test_fill_rate_delta_value(self):
        result = compare_windows(_make_replay(), _make_paper())
        # 0.80000000 - 0.75000000 = 0.05000000
        assert result.fill_rate_delta == Decimal("0.05000000")

    def test_fill_rate_delta_is_decimal(self):
        result = compare_windows(_make_replay(), _make_paper())
        assert isinstance(result.fill_rate_delta, Decimal)
        assert isinstance(result.fill_rate_replay, Decimal)
        assert isinstance(result.fill_rate_paper, Decimal)

    def test_provenance_fields(self):
        result = compare_windows(_make_replay(), _make_paper())
        assert result.replay_run_id == _RUN_ID
        assert result.paper_provenance_id == "paper-run-001"
        assert result.symbol == _SYMBOL
        assert result.strategy_id == _STRATEGY

    def test_window_timestamps_preserved(self):
        result = compare_windows(_make_replay(), _make_paper())
        assert result.window_start_utc_replay == _START
        assert result.window_end_utc_replay == _END
        assert result.window_start_utc_paper == _START
        assert result.window_end_utc_paper == _END

    def test_comparison_fingerprint_is_hex_string(self):
        result = compare_windows(_make_replay(), _make_paper())
        assert isinstance(result.comparison_fingerprint, str)
        assert len(result.comparison_fingerprint) == 64
        assert all(c in "0123456789abcdef" for c in result.comparison_fingerprint)

    def test_zero_counts_no_error(self):
        # fill_rate must not divide by zero when counts are both 0
        r = _make_replay(
            signal_count=0,
            order_count=0,
            fill_count=0,
            actual_reject_count=0,
            inferred_unfilled_count=0,
        )
        p = _make_paper(
            signal_count=0,
            order_count=0,
            fill_count=0,
            actual_reject_count=0,
            inferred_unfilled_count=0,
        )
        result = compare_windows(r, p)
        assert result.fill_rate_replay == Decimal("0.00000000")
        assert result.fill_rate_paper == Decimal("0.00000000")
        assert result.fill_rate_delta == Decimal("0.00000000")

    def test_partial_overlap_is_aligned(self):
        # Replay: 2024-01-01 → 2024-01-03; Paper: 2024-01-02 → 2024-01-04
        # They overlap on 2024-01-02 → 2024-01-03
        r = _make_replay(
            window_start_utc="2024-01-01T00:00:00+00:00",
            window_end_utc="2024-01-03T00:00:00+00:00",
        )
        p = _make_paper(
            window_start_utc="2024-01-02T00:00:00+00:00",
            window_end_utc="2024-01-04T00:00:00+00:00",
        )
        result = compare_windows(r, p)
        assert result.status == "aligned"


# ---------------------------------------------------------------------------
# compare_windows: fail-closed paths
# ---------------------------------------------------------------------------


class TestCompareWindowsFailClosed:
    def test_missing_paper_raises(self):
        with pytest.raises(ShadowCompareError, match="missing_reference"):
            compare_windows(_make_replay(), None)

    def test_symbol_mismatch_raises(self):
        with pytest.raises(ShadowCompareError, match="misaligned.*symbol"):
            compare_windows(_make_replay(), _make_paper(symbol="ETHUSDT"))

    def test_strategy_mismatch_raises(self):
        with pytest.raises(ShadowCompareError, match="misaligned.*strategy_id"):
            compare_windows(_make_replay(), _make_paper(strategy_id="other-v2"))

    def test_non_overlapping_windows_raises(self):
        # Paper window is entirely before replay window
        p = _make_paper(
            window_start_utc="2023-12-01T00:00:00+00:00",
            window_end_utc="2023-12-31T00:00:00+00:00",
        )
        with pytest.raises(ShadowCompareError, match="misaligned.*temporal overlap"):
            compare_windows(_make_replay(), p)

    def test_adjacent_windows_raises(self):
        # Paper ends exactly where replay starts — no actual shared period
        p = _make_paper(
            window_start_utc="2023-12-31T00:00:00+00:00",
            window_end_utc="2024-01-01T00:00:00+00:00",  # == replay start
        )
        with pytest.raises(ShadowCompareError, match="misaligned.*temporal overlap"):
            compare_windows(_make_replay(), p)

    def test_future_paper_window_raises(self):
        p = _make_paper(
            window_start_utc="2024-01-03T00:00:00+00:00",
            window_end_utc="2024-01-04T00:00:00+00:00",
        )
        with pytest.raises(ShadowCompareError, match="misaligned.*temporal overlap"):
            compare_windows(_make_replay(), p)

    # --- Causal signal context tests (#3058) ---

    def test_signal_context_delta_no_causal(self):
        """Without causal context, signal_context_delta == signal_count_delta."""
        r = _make_replay(signal_count=5)
        p = _make_paper(signal_count=3, causal_signal_count=0)
        result = compare_windows(r, p)
        assert result.signal_count_delta == 2  # 5 - 3
        assert result.signal_context_delta == 2  # 5 - (3 + 0)
        assert result.signal_count_false_neutral_detected is False

    def test_signal_context_delta_with_causal(self):
        """With causal context, signal_context_delta includes causal signals."""
        r = _make_replay(signal_count=5)
        p = _make_paper(signal_count=3, causal_signal_count=2)
        result = compare_windows(r, p)
        assert result.signal_count_delta == 2  # 5 - 3 (in-window only)
        assert result.signal_context_delta == 0  # 5 - (3 + 2)
        assert result.signal_count_false_neutral_detected is False

    def test_signal_count_false_neutral_detected(self):
        """False neutral: in-window paper signal_count=0 but causal_signal_count>0."""
        r = _make_replay(signal_count=3)
        p = _make_paper(signal_count=0, causal_signal_count=1)
        result = compare_windows(r, p)
        assert result.signal_count_delta == 3  # 3 - 0 (in-window only, looks bad)
        assert result.signal_context_delta == 2  # 3 - (0 + 1)
        assert result.signal_count_false_neutral_detected is True

    def test_signal_context_delta_in_json_artifact(self, tmp_path):
        """signal_context_delta and false-neutral flag appear in artifact JSON."""
        r = _make_replay(signal_count=3)
        p = _make_paper(signal_count=0, causal_signal_count=1)
        result = compare_windows(r, p)
        write_shadow_comparison_artifact(result, tmp_path)
        data = json.loads((tmp_path / "shadow_comparison.json").read_text())
        assert data["signal_context_delta"] == 2
        assert data["signal_count_false_neutral_detected"] is True


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_identical_inputs_produce_same_fingerprint(self):
        r1 = compare_windows(_make_replay(), _make_paper())
        r2 = compare_windows(_make_replay(), _make_paper())
        assert r1.comparison_fingerprint == r2.comparison_fingerprint

    def test_different_signal_counts_produce_different_fingerprint(self):
        r1 = compare_windows(_make_replay(signal_count=10), _make_paper())
        r2 = compare_windows(_make_replay(signal_count=99), _make_paper())
        assert r1.comparison_fingerprint != r2.comparison_fingerprint

    def test_different_paper_provenance_produces_different_fingerprint(self):
        r1 = compare_windows(_make_replay(), _make_paper(provenance_id="paper-A"))
        r2 = compare_windows(_make_replay(), _make_paper(provenance_id="paper-B"))
        assert r1.comparison_fingerprint != r2.comparison_fingerprint

    def test_all_result_fields_are_deterministic(self):
        r1 = compare_windows(_make_replay(), _make_paper())
        r2 = compare_windows(_make_replay(), _make_paper())
        assert r1 == r2  # frozen dataclass equality


# ---------------------------------------------------------------------------
# build_calibration_summary
# ---------------------------------------------------------------------------


class TestBuildCalibrationSummary:
    @pytest.fixture
    def result(self) -> ShadowComparisonResult:
        return compare_windows(_make_replay(), _make_paper())

    def test_contains_status(self, result):
        summary = build_calibration_summary(result)
        assert "aligned" in summary

    def test_contains_replay_run_id(self, result):
        summary = build_calibration_summary(result)
        assert result.replay_run_id in summary

    def test_contains_paper_provenance_id(self, result):
        summary = build_calibration_summary(result)
        assert result.paper_provenance_id in summary

    def test_contains_symbol(self, result):
        summary = build_calibration_summary(result)
        assert result.symbol in summary

    def test_contains_signal_count_delta(self, result):
        summary = build_calibration_summary(result)
        # delta is -2, formatted as -2
        assert "-2" in summary

    def test_contains_fill_count_delta(self, result):
        summary = build_calibration_summary(result)
        assert "-1" in summary

    def test_contains_fill_rate_values(self, result):
        summary = build_calibration_summary(result)
        assert "0.80000000" in summary
        assert "0.75000000" in summary

    def test_contains_fill_rate_delta(self, result):
        summary = build_calibration_summary(result)
        assert "0.05000000" in summary

    def test_contains_fingerprint(self, result):
        summary = build_calibration_summary(result)
        assert result.comparison_fingerprint in summary

    def test_contains_window_timestamps(self, result):
        summary = build_calibration_summary(result)
        assert result.window_start_utc_replay in summary
        assert result.window_start_utc_paper in summary

    def test_returns_string(self, result):
        assert isinstance(build_calibration_summary(result), str)

    def test_contains_signal_context_delta(self):
        """Summary includes signal_context_delta in its output."""
        r = _make_replay(signal_count=3)
        p = _make_paper(signal_count=0, causal_signal_count=1)
        result = compare_windows(r, p)
        summary = build_calibration_summary(result)
        assert "+2" in summary  # 3 - (0 + 1) = 2
        assert "Signal False Neutral" in summary


# ---------------------------------------------------------------------------
# write_shadow_comparison_artifact
# ---------------------------------------------------------------------------


class TestWriteShadowComparisonArtifact:
    @pytest.fixture
    def result(self) -> ShadowComparisonResult:
        return compare_windows(_make_replay(), _make_paper())

    def test_writes_file(self, tmp_path, result):
        write_shadow_comparison_artifact(result, tmp_path)
        artifact = tmp_path / "shadow_comparison.json"
        assert artifact.exists()

    def test_writes_valid_json(self, tmp_path, result):
        write_shadow_comparison_artifact(result, tmp_path)
        raw = (tmp_path / "shadow_comparison.json").read_text(encoding="utf-8")
        data = json.loads(raw)
        assert isinstance(data, dict)

    def test_json_contains_required_keys(self, tmp_path, result):
        write_shadow_comparison_artifact(result, tmp_path)
        data = json.loads((tmp_path / "shadow_comparison.json").read_text())
        for key in (
            "comparison_fingerprint",
            "status",
            "replay_run_id",
            "paper_provenance_id",
            "symbol",
            "strategy_id",
            "signal_count_delta",
            "signal_context_delta",
            "signal_count_false_neutral_detected",
            "order_count_delta",
            "fill_count_delta",
            "inferred_unfilled_count_delta",
            "actual_reject_count_delta",
            "fill_rate_replay",
            "fill_rate_paper",
            "fill_rate_delta",
        ):
            assert key in data, f"Missing key: {key}"

    def test_json_fill_rate_delta_is_string(self, tmp_path, result):
        write_shadow_comparison_artifact(result, tmp_path)
        data = json.loads((tmp_path / "shadow_comparison.json").read_text())
        assert isinstance(data["fill_rate_delta"], str)
        assert isinstance(data["fill_rate_replay"], str)
        assert isinstance(data["fill_rate_paper"], str)

    def test_json_is_deterministic(self, tmp_path, result):
        write_shadow_comparison_artifact(result, tmp_path / "a")
        write_shadow_comparison_artifact(result, tmp_path / "b")
        text_a = (tmp_path / "a" / "shadow_comparison.json").read_text()
        text_b = (tmp_path / "b" / "shadow_comparison.json").read_text()
        assert text_a == text_b

    def test_aligned_result_omits_explicit_reject_keys_when_missing(self, tmp_path):
        replay = _make_replay(actual_reject_count=None, inferred_unfilled_count=2)
        paper = _make_paper(actual_reject_count=None, inferred_unfilled_count=3)
        result = compare_windows(replay, paper)
        write_shadow_comparison_artifact(result, tmp_path)
        data = json.loads((tmp_path / "shadow_comparison.json").read_text())
        assert data["status"] == "aligned"
        assert "actual_reject_count_delta" not in data
        assert "fill_rate_replay" not in data
        assert "fill_rate_paper" not in data
        assert "fill_rate_delta" not in data

    def test_creates_artifact_root_if_missing(self, tmp_path, result):
        nested = tmp_path / "deep" / "nested"
        write_shadow_comparison_artifact(result, nested)
        assert (nested / "shadow_comparison.json").exists()

    def test_fail_closed_on_io_error(self, tmp_path, result):
        # Create a file where a directory is expected → mkdir raises OSError
        blocker = tmp_path / "blocker"
        blocker.write_text("not a directory")
        with pytest.raises(ShadowCompareError, match="Failed to write"):
            write_shadow_comparison_artifact(result, blocker)
