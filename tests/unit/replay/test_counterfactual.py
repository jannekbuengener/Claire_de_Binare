"""Unit tests for core.replay.counterfactual (#1850).

Covers: perturbation validation, all 4 perturbation types with exact deltas,
sequential composition, fingerprint determinism, Decimal correctness,
artifact writing (valid JSON + fail-closed), and summary content.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from core.replay.counterfactual import (
    CounterfactualBaseWindow,
    CounterfactualError,
    CounterfactualResult,
    PerturbationSpec,
    apply_perturbations,
    build_perturbation_summary,
    write_counterfactual_artifact,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_base(
    symbol: str = "BTCUSDT",
    strategy_id: str = "strat_test",
    signal_count: int = 100,
    fill_count: int = 80,
    reject_count: int = 20,
    fill_rate: str = "0.8",
    window_start: str = "2024-01-01T00:00:00Z",
    window_end: str = "2024-01-02T00:00:00Z",
) -> CounterfactualBaseWindow:
    return CounterfactualBaseWindow(
        symbol=symbol,
        strategy_id=strategy_id,
        window_start=window_start,
        window_end=window_end,
        signal_count=signal_count,
        fill_count=fill_count,
        reject_count=reject_count,
        fill_rate=Decimal(fill_rate),
    )


def _spec(perturbation_type: str, magnitude: str) -> PerturbationSpec:
    return PerturbationSpec(
        perturbation_type=perturbation_type, magnitude=Decimal(magnitude)
    )


# ===========================================================================
# TestPerturbationSpecValidation
# ===========================================================================


class TestPerturbationSpecValidation:
    def test_unknown_type_raises(self) -> None:
        with pytest.raises(CounterfactualError, match="unknown perturbation type"):
            _spec("random_perturbation", "1")

    def test_slippage_bps_below_zero_raises(self) -> None:
        with pytest.raises(CounterfactualError, match="out of range"):
            _spec("slippage_bps", "-1")

    def test_slippage_bps_above_max_raises(self) -> None:
        with pytest.raises(CounterfactualError, match="out of range"):
            _spec("slippage_bps", "10001")

    def test_entry_delay_bars_below_one_raises(self) -> None:
        with pytest.raises(CounterfactualError, match="out of range"):
            _spec("entry_delay_bars", "0")

    def test_entry_delay_bars_above_max_raises(self) -> None:
        with pytest.raises(CounterfactualError, match="out of range"):
            _spec("entry_delay_bars", "1001")

    def test_fill_rate_reduction_below_zero_raises(self) -> None:
        with pytest.raises(CounterfactualError, match="out of range"):
            _spec("fill_rate_reduction", "-0.01")

    def test_fill_rate_reduction_above_one_raises(self) -> None:
        with pytest.raises(CounterfactualError, match="out of range"):
            _spec("fill_rate_reduction", "1.001")

    def test_feed_gap_bars_below_one_raises(self) -> None:
        with pytest.raises(CounterfactualError, match="out of range"):
            _spec("feed_gap_bars", "0")

    def test_feed_gap_bars_above_max_raises(self) -> None:
        with pytest.raises(CounterfactualError, match="out of range"):
            _spec("feed_gap_bars", "10001")

    def test_valid_spec_construction(self) -> None:
        spec = _spec("slippage_bps", "500")
        assert spec.perturbation_type == "slippage_bps"
        assert spec.magnitude == Decimal("500")

    def test_boundary_values_are_valid(self) -> None:
        _spec("slippage_bps", "0")
        _spec("slippage_bps", "10000")
        _spec("fill_rate_reduction", "0")
        _spec("fill_rate_reduction", "1")
        _spec("entry_delay_bars", "1")
        _spec("entry_delay_bars", "1000")
        _spec("feed_gap_bars", "1")
        _spec("feed_gap_bars", "10000")

    def test_to_dict_has_string_magnitude(self) -> None:
        spec = _spec("slippage_bps", "500")
        d = spec.to_dict()
        assert isinstance(d["magnitude"], str)
        assert d["perturbation_type"] == "slippage_bps"


# ===========================================================================
# TestCounterfactualBaseWindowValidation
# ===========================================================================


class TestCounterfactualBaseWindowValidation:
    def test_empty_symbol_raises(self) -> None:
        with pytest.raises(CounterfactualError, match="symbol must not be empty"):
            CounterfactualBaseWindow(
                symbol="",
                strategy_id="strat",
                window_start="2024-01-01T00:00:00Z",
                window_end="2024-01-02T00:00:00Z",
                signal_count=100,
                fill_count=80,
                reject_count=20,
                fill_rate=Decimal("0.8"),
            )

    def test_empty_strategy_id_raises(self) -> None:
        with pytest.raises(CounterfactualError, match="strategy_id must not be empty"):
            CounterfactualBaseWindow(
                symbol="BTCUSDT",
                strategy_id="",
                window_start="2024-01-01T00:00:00Z",
                window_end="2024-01-02T00:00:00Z",
                signal_count=100,
                fill_count=80,
                reject_count=20,
                fill_rate=Decimal("0.8"),
            )

    def test_negative_signal_count_raises(self) -> None:
        with pytest.raises(CounterfactualError, match="signal_count must be >= 0"):
            CounterfactualBaseWindow(
                symbol="BTCUSDT",
                strategy_id="strat",
                window_start="2024-01-01T00:00:00Z",
                window_end="2024-01-02T00:00:00Z",
                signal_count=-1,
                fill_count=0,
                reject_count=0,
                fill_rate=Decimal("0"),
            )

    def test_negative_fill_count_raises(self) -> None:
        with pytest.raises(CounterfactualError, match="fill_count must be >= 0"):
            CounterfactualBaseWindow(
                symbol="BTCUSDT",
                strategy_id="strat",
                window_start="2024-01-01T00:00:00Z",
                window_end="2024-01-02T00:00:00Z",
                signal_count=100,
                fill_count=-1,
                reject_count=20,
                fill_rate=Decimal("0.8"),
            )

    def test_fill_rate_above_one_raises(self) -> None:
        with pytest.raises(CounterfactualError, match="fill_rate must be in"):
            CounterfactualBaseWindow(
                symbol="BTCUSDT",
                strategy_id="strat",
                window_start="2024-01-01T00:00:00Z",
                window_end="2024-01-02T00:00:00Z",
                signal_count=100,
                fill_count=80,
                reject_count=20,
                fill_rate=Decimal("1.1"),
            )

    def test_valid_base_construction(self) -> None:
        base = _make_base()
        assert base.signal_count == 100
        assert base.fill_count == 80
        assert base.fill_rate == Decimal("0.8")

    def test_to_dict_has_string_fill_rate(self) -> None:
        base = _make_base()
        d = base.to_dict()
        assert isinstance(d["fill_rate"], str)
        assert d["symbol"] == "BTCUSDT"


# ===========================================================================
# TestApplyPerturbationsFailClosed
# ===========================================================================


class TestApplyPerturbationsFailClosed:
    def test_base_none_raises(self) -> None:
        with pytest.raises(CounterfactualError, match="base must not be None"):
            apply_perturbations(None, [_spec("slippage_bps", "100")])  # type: ignore[arg-type]

    def test_empty_specs_raises(self) -> None:
        base = _make_base()
        with pytest.raises(CounterfactualError, match="no perturbations specified"):
            apply_perturbations(base, [])


# ===========================================================================
# TestSlippageBps
# ===========================================================================


class TestSlippageBps:
    def test_basic_delta_500_bps(self) -> None:
        # fills_lost = floor(80 * 500 / 10000) = floor(4.0) = 4
        base = _make_base(signal_count=100, fill_count=80, reject_count=20)
        result = apply_perturbations(base, [_spec("slippage_bps", "500")])
        assert result.perturbed_signal_count == 100
        assert result.perturbed_fill_count == 76
        assert result.perturbed_reject_count == 24
        assert result.signal_count_delta == 0
        assert result.fill_count_delta == -4
        assert result.reject_count_delta == 4

    def test_zero_slippage_no_change(self) -> None:
        base = _make_base()
        result = apply_perturbations(base, [_spec("slippage_bps", "0")])
        assert result.perturbed_fill_count == 80
        assert result.perturbed_reject_count == 20
        assert result.fill_count_delta == 0
        assert result.signal_count_delta == 0

    def test_max_slippage_empties_fills(self) -> None:
        # fills_lost = floor(80 * 10000 / 10000) = 80
        base = _make_base(signal_count=100, fill_count=80, reject_count=20)
        result = apply_perturbations(base, [_spec("slippage_bps", "10000")])
        assert result.perturbed_fill_count == 0
        assert result.perturbed_reject_count == 100
        assert result.fill_count_delta == -80
        assert result.reject_count_delta == 80

    def test_applied_type_recorded(self) -> None:
        base = _make_base()
        result = apply_perturbations(base, [_spec("slippage_bps", "500")])
        assert "slippage_bps" in result.applied_perturbation_types

    def test_signal_unchanged(self) -> None:
        base = _make_base(signal_count=200, fill_count=150, reject_count=50)
        result = apply_perturbations(base, [_spec("slippage_bps", "1000")])
        assert result.perturbed_signal_count == 200
        assert result.signal_count_delta == 0


# ===========================================================================
# TestEntryDelayBars
# ===========================================================================


class TestEntryDelayBars:
    def test_basic_delta_50_bars(self) -> None:
        # fraction_retained = 1 - 50*0.01 = 0.5
        # new_signal = floor(100 * 0.5) = 50
        # fill_fraction = 80/100 = 0.8
        # new_fill = floor(50 * 0.8) = 40
        # new_reject = 50 - 40 = 10
        base = _make_base(signal_count=100, fill_count=80, reject_count=20)
        result = apply_perturbations(base, [_spec("entry_delay_bars", "50")])
        assert result.perturbed_signal_count == 50
        assert result.perturbed_fill_count == 40
        assert result.perturbed_reject_count == 10
        assert result.signal_count_delta == -50
        assert result.fill_count_delta == -40
        assert result.reject_count_delta == -10

    def test_100_bars_complete_signal_loss(self) -> None:
        # fraction_retained = max(0, 1 - 100*0.01) = 0.0
        base = _make_base(signal_count=100, fill_count=80, reject_count=20)
        result = apply_perturbations(base, [_spec("entry_delay_bars", "100")])
        assert result.perturbed_signal_count == 0
        assert result.perturbed_fill_count == 0
        assert result.perturbed_reject_count == 0

    def test_zero_signal_edge_case(self) -> None:
        base = _make_base(signal_count=0, fill_count=0, reject_count=0, fill_rate="0")
        result = apply_perturbations(base, [_spec("entry_delay_bars", "10")])
        assert result.perturbed_signal_count == 0
        assert result.perturbed_fill_count == 0
        assert result.perturbed_reject_count == 0

    def test_small_delay_10_bars(self) -> None:
        # fraction_retained = 0.9, new_signal = 90
        # fill_fraction = 0.8, new_fill = floor(90 * 0.8) = 72, new_reject = 18
        base = _make_base(signal_count=100, fill_count=80, reject_count=20)
        result = apply_perturbations(base, [_spec("entry_delay_bars", "10")])
        assert result.perturbed_signal_count == 90
        assert result.perturbed_fill_count == 72
        assert result.perturbed_reject_count == 18

    def test_fill_reject_ratio_preserved(self) -> None:
        # After delay, fill/signal ratio should match original fill_fraction
        base = _make_base(signal_count=100, fill_count=80, reject_count=20)
        result = apply_perturbations(base, [_spec("entry_delay_bars", "50")])
        # new_signal=50, new_fill=40 → ratio=0.8 = original fill_fraction
        assert result.perturbed_fill_count == 40
        assert result.perturbed_signal_count == 50


# ===========================================================================
# TestFillRateReduction
# ===========================================================================


class TestFillRateReduction:
    def test_basic_delta_25_percent(self) -> None:
        # fills_lost = floor(80 * 0.25) = 20
        base = _make_base(signal_count=100, fill_count=80, reject_count=20)
        result = apply_perturbations(base, [_spec("fill_rate_reduction", "0.25")])
        assert result.perturbed_signal_count == 100
        assert result.perturbed_fill_count == 60
        assert result.perturbed_reject_count == 40
        assert result.signal_count_delta == 0
        assert result.fill_count_delta == -20
        assert result.reject_count_delta == 20

    def test_zero_reduction_no_change(self) -> None:
        base = _make_base()
        result = apply_perturbations(base, [_spec("fill_rate_reduction", "0")])
        assert result.perturbed_fill_count == 80
        assert result.fill_count_delta == 0

    def test_full_reduction_100_percent(self) -> None:
        # fills_lost = 80, new_fill = 0, new_reject = 100
        base = _make_base(signal_count=100, fill_count=80, reject_count=20)
        result = apply_perturbations(base, [_spec("fill_rate_reduction", "1")])
        assert result.perturbed_fill_count == 0
        assert result.perturbed_reject_count == 100
        assert result.fill_count_delta == -80

    def test_fill_rate_delta_is_decimal(self) -> None:
        base = _make_base(signal_count=100, fill_count=80, reject_count=20)
        result = apply_perturbations(base, [_spec("fill_rate_reduction", "0.25")])
        assert isinstance(result.fill_rate_delta, Decimal)

    def test_perturbed_fill_rate_correct(self) -> None:
        # perturbed: signal=100, fill=60 → fill_rate = 60/100 = 0.6
        base = _make_base(signal_count=100, fill_count=80, reject_count=20)
        result = apply_perturbations(base, [_spec("fill_rate_reduction", "0.25")])
        assert result.perturbed_fill_rate == Decimal("60") / Decimal("100")
        expected_delta = Decimal("60") / Decimal("100") - Decimal("0.8")
        assert result.fill_rate_delta == expected_delta


# ===========================================================================
# TestFeedGapBars
# ===========================================================================


class TestFeedGapBars:
    def test_basic_delta_100_bars(self) -> None:
        # fraction_retained = 1 - 100*0.005 = 0.5
        # new_signal = floor(100 * 0.5) = 50
        # fill_fraction = 0.8, new_fill = floor(50*0.8) = 40, new_reject = 10
        base = _make_base(signal_count=100, fill_count=80, reject_count=20)
        result = apply_perturbations(base, [_spec("feed_gap_bars", "100")])
        assert result.perturbed_signal_count == 50
        assert result.perturbed_fill_count == 40
        assert result.perturbed_reject_count == 10
        assert result.signal_count_delta == -50

    def test_200_bars_complete_signal_loss(self) -> None:
        # fraction_retained = max(0, 1 - 200*0.005) = 0.0
        base = _make_base(signal_count=100, fill_count=80, reject_count=20)
        result = apply_perturbations(base, [_spec("feed_gap_bars", "200")])
        assert result.perturbed_signal_count == 0
        assert result.perturbed_fill_count == 0
        assert result.perturbed_reject_count == 0

    def test_20_bar_gap_partial_loss(self) -> None:
        # fraction_retained = 1 - 20*0.005 = 0.9
        # new_signal = 90, new_fill = floor(90*0.8) = 72, new_reject = 18
        base = _make_base(signal_count=100, fill_count=80, reject_count=20)
        result = apply_perturbations(base, [_spec("feed_gap_bars", "20")])
        assert result.perturbed_signal_count == 90
        assert result.perturbed_fill_count == 72
        assert result.perturbed_reject_count == 18

    def test_zero_signal_edge_case(self) -> None:
        base = _make_base(signal_count=0, fill_count=0, reject_count=0, fill_rate="0")
        result = apply_perturbations(base, [_spec("feed_gap_bars", "50")])
        assert result.perturbed_signal_count == 0
        assert result.perturbed_fill_count == 0


# ===========================================================================
# TestComposition
# ===========================================================================


class TestComposition:
    def test_slippage_then_fill_rate_reduction(self) -> None:
        # Step 1: slippage_bps=500 → fill=76, reject=24, signal=100
        # Step 2: fill_rate_reduction=0.25 → fills_lost=floor(76*0.25)=19
        #   new_fill=57, new_reject=43
        base = _make_base(signal_count=100, fill_count=80, reject_count=20)
        specs = [_spec("slippage_bps", "500"), _spec("fill_rate_reduction", "0.25")]
        result = apply_perturbations(base, specs)
        assert result.perturbed_signal_count == 100
        assert result.perturbed_fill_count == 57
        assert result.perturbed_reject_count == 43
        assert result.fill_count_delta == -23
        assert result.reject_count_delta == 23

    def test_signal_drop_then_slippage(self) -> None:
        # Step 1: entry_delay_bars=50 → signal=50, fill=40, reject=10
        # Step 2: slippage_bps=500 → fills_lost=floor(40*500/10000)=2
        #   new_fill=38, new_reject=12, signal=50
        base = _make_base(signal_count=100, fill_count=80, reject_count=20)
        specs = [_spec("entry_delay_bars", "50"), _spec("slippage_bps", "500")]
        result = apply_perturbations(base, specs)
        assert result.perturbed_signal_count == 50
        assert result.perturbed_fill_count == 38
        assert result.perturbed_reject_count == 12

    def test_applied_types_sorted_and_deduplicated(self) -> None:
        base = _make_base()
        specs = [_spec("slippage_bps", "100"), _spec("slippage_bps", "200")]
        result = apply_perturbations(base, specs)
        assert result.applied_perturbation_types == ("slippage_bps",)

    def test_applied_types_multiple_sorted(self) -> None:
        base = _make_base()
        specs = [
            _spec("slippage_bps", "100"),
            _spec("fill_rate_reduction", "0.1"),
            _spec("entry_delay_bars", "10"),
        ]
        result = apply_perturbations(base, specs)
        assert result.applied_perturbation_types == (
            "entry_delay_bars",
            "fill_rate_reduction",
            "slippage_bps",
        )


# ===========================================================================
# TestFingerprintDeterminism
# ===========================================================================


class TestFingerprintDeterminism:
    def test_same_inputs_produce_identical_fingerprint(self) -> None:
        base = _make_base()
        specs = [_spec("slippage_bps", "500")]
        r1 = apply_perturbations(base, specs)
        r2 = apply_perturbations(base, specs)
        assert r1.provenance_fingerprint == r2.provenance_fingerprint

    def test_different_magnitude_different_fingerprint(self) -> None:
        base = _make_base()
        r1 = apply_perturbations(base, [_spec("slippage_bps", "500")])
        r2 = apply_perturbations(base, [_spec("slippage_bps", "600")])
        assert r1.provenance_fingerprint != r2.provenance_fingerprint

    def test_different_base_different_fingerprint(self) -> None:
        base1 = _make_base(signal_count=100)
        base2 = _make_base(signal_count=200, fill_count=160, reject_count=40)
        specs = [_spec("slippage_bps", "500")]
        r1 = apply_perturbations(base1, specs)
        r2 = apply_perturbations(base2, specs)
        assert r1.provenance_fingerprint != r2.provenance_fingerprint

    def test_different_type_different_fingerprint(self) -> None:
        base = _make_base()
        r1 = apply_perturbations(base, [_spec("slippage_bps", "100")])
        r2 = apply_perturbations(base, [_spec("fill_rate_reduction", "0.1")])
        assert r1.provenance_fingerprint != r2.provenance_fingerprint

    def test_fingerprint_is_64_char_hex_string(self) -> None:
        base = _make_base()
        result = apply_perturbations(base, [_spec("slippage_bps", "100")])
        fp = result.provenance_fingerprint
        assert isinstance(fp, str)
        assert len(fp) == 64
        assert all(c in "0123456789abcdef" for c in fp)


# ===========================================================================
# TestDecimalCorrectness
# ===========================================================================


class TestDecimalCorrectness:
    def test_fill_rate_delta_is_decimal_type(self) -> None:
        base = _make_base(signal_count=100, fill_count=80, reject_count=20)
        result = apply_perturbations(base, [_spec("fill_rate_reduction", "0.25")])
        assert isinstance(result.fill_rate_delta, Decimal)

    def test_perturbed_fill_rate_is_decimal_type(self) -> None:
        base = _make_base()
        result = apply_perturbations(base, [_spec("slippage_bps", "500")])
        assert isinstance(result.perturbed_fill_rate, Decimal)

    def test_base_fill_rate_preserved_as_decimal(self) -> None:
        base = _make_base(fill_rate="0.8")
        result = apply_perturbations(base, [_spec("slippage_bps", "0")])
        assert isinstance(result.base_fill_rate, Decimal)
        assert result.base_fill_rate == Decimal("0.8")

    def test_fill_rate_delta_exact_value(self) -> None:
        # fill=60, signal=100 → fill_rate=0.6; delta = 0.6 - 0.8 = -0.2
        base = _make_base(signal_count=100, fill_count=80, reject_count=20, fill_rate="0.8")
        result = apply_perturbations(base, [_spec("fill_rate_reduction", "0.25")])
        expected = Decimal("60") / Decimal("100") - Decimal("0.8")
        assert result.fill_rate_delta == expected

    def test_zero_signal_fill_rate_is_zero_decimal(self) -> None:
        base = _make_base(signal_count=0, fill_count=0, reject_count=0, fill_rate="0")
        result = apply_perturbations(base, [_spec("entry_delay_bars", "10")])
        assert result.perturbed_fill_rate == Decimal("0")
        assert isinstance(result.perturbed_fill_rate, Decimal)

    def test_no_float_in_fill_rate_fields(self) -> None:
        base = _make_base()
        result = apply_perturbations(base, [_spec("slippage_bps", "500")])
        assert not isinstance(result.base_fill_rate, float)
        assert not isinstance(result.perturbed_fill_rate, float)
        assert not isinstance(result.fill_rate_delta, float)


# ===========================================================================
# TestWriteArtifact
# ===========================================================================


class TestWriteArtifact:
    def test_writes_json_file(self, tmp_path: Path) -> None:
        base = _make_base()
        result = apply_perturbations(base, [_spec("slippage_bps", "500")])
        write_counterfactual_artifact(result, tmp_path)
        out = tmp_path / "counterfactual_result.json"
        assert out.exists()

    def test_json_is_valid_and_contains_key_fields(self, tmp_path: Path) -> None:
        base = _make_base()
        result = apply_perturbations(base, [_spec("slippage_bps", "500")])
        write_counterfactual_artifact(result, tmp_path)
        data = json.loads((tmp_path / "counterfactual_result.json").read_text())
        assert data["symbol"] == "BTCUSDT"
        assert data["provenance_fingerprint"] == result.provenance_fingerprint
        assert "fill_count_delta" in data
        assert "fill_rate_delta" in data
        assert "applied_perturbation_types" in data

    def test_fill_rate_delta_serialized_as_string(self, tmp_path: Path) -> None:
        base = _make_base()
        result = apply_perturbations(base, [_spec("fill_rate_reduction", "0.25")])
        write_counterfactual_artifact(result, tmp_path)
        data = json.loads((tmp_path / "counterfactual_result.json").read_text())
        assert isinstance(data["fill_rate_delta"], str)

    def test_creates_nested_parent_dirs(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "c"
        base = _make_base()
        result = apply_perturbations(base, [_spec("slippage_bps", "100")])
        write_counterfactual_artifact(result, nested)
        assert (nested / "counterfactual_result.json").exists()

    def test_fail_closed_on_io_error(self, tmp_path: Path) -> None:
        base = _make_base()
        result = apply_perturbations(base, [_spec("slippage_bps", "100")])
        with patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
            with pytest.raises(CounterfactualError, match="failed to write"):
                write_counterfactual_artifact(result, tmp_path)

    def test_artifact_keys_are_sorted(self, tmp_path: Path) -> None:
        base = _make_base()
        result = apply_perturbations(base, [_spec("slippage_bps", "100")])
        write_counterfactual_artifact(result, tmp_path)
        raw = (tmp_path / "counterfactual_result.json").read_text()
        data = json.loads(raw)
        keys = list(data.keys())
        assert keys == sorted(keys)


# ===========================================================================
# TestBuildSummary
# ===========================================================================


class TestBuildSummary:
    def test_contains_symbol(self) -> None:
        base = _make_base(symbol="ETHUSDT")
        result = apply_perturbations(base, [_spec("slippage_bps", "500")])
        summary = build_perturbation_summary(result)
        assert "ETHUSDT" in summary

    def test_contains_fill_delta(self) -> None:
        base = _make_base()
        result = apply_perturbations(base, [_spec("slippage_bps", "500")])
        summary = build_perturbation_summary(result)
        assert "fill_delta" in summary

    def test_contains_signal_delta(self) -> None:
        base = _make_base()
        result = apply_perturbations(base, [_spec("entry_delay_bars", "50")])
        summary = build_perturbation_summary(result)
        assert "signal_delta" in summary

    def test_contains_reject_delta(self) -> None:
        base = _make_base()
        result = apply_perturbations(base, [_spec("fill_rate_reduction", "0.25")])
        summary = build_perturbation_summary(result)
        assert "reject_delta" in summary

    def test_contains_fill_rate_delta(self) -> None:
        base = _make_base()
        result = apply_perturbations(base, [_spec("fill_rate_reduction", "0.25")])
        summary = build_perturbation_summary(result)
        assert "fill_rate_delta" in summary

    def test_contains_applied_type(self) -> None:
        base = _make_base()
        result = apply_perturbations(base, [_spec("slippage_bps", "500")])
        summary = build_perturbation_summary(result)
        assert "slippage_bps" in summary

    def test_contains_fingerprint(self) -> None:
        base = _make_base()
        result = apply_perturbations(base, [_spec("slippage_bps", "500")])
        summary = build_perturbation_summary(result)
        assert result.provenance_fingerprint in summary

    def test_summary_is_string(self) -> None:
        base = _make_base()
        result = apply_perturbations(base, [_spec("slippage_bps", "100")])
        summary = build_perturbation_summary(result)
        assert isinstance(summary, str)
        assert len(summary) > 0
