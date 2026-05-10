"""Unit tests for core/replay/scheduler.py."""

from __future__ import annotations

import pytest

from core.replay.dataset_provider import DatasetResult
from core.replay.dataset_spec import DatasetSpec
from core.replay.scheduler import (
    ReplayScheduler,
    SchedulerConfig,
    SchedulerError,
    _PROFILE_SPEEDUP,
    _VALID_PROFILES,
)

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------
_ONE_MIN_MS = 60_000
_BASE_TS = 1_000_000


def _make_candles(n: int, start_ts_ms: int = _BASE_TS) -> tuple:
    return tuple(
        {
            "ts_ms": start_ts_ms + i * _ONE_MIN_MS,
            "high": 100.0,
            "low": 99.0,
            "close": 99.5,
        }
        for i in range(n)
    )


def _make_dataset(warmup_count: int, live_count: int, start_ts_ms: int = _BASE_TS) -> DatasetResult:
    all_candles = _make_candles(warmup_count + live_count, start_ts_ms=start_ts_ms)
    first_live_ts = all_candles[warmup_count]["ts_ms"]
    last_live_ts = all_candles[-1]["ts_ms"]
    spec = DatasetSpec(
        symbol="BTCUSDT",
        timeframe="1m",
        start_ts_ms=first_live_ts,
        end_ts_ms=last_live_ts,
        warmup_candles=warmup_count,
        source="file",
        file_path="/fake/test_candles.json",
    )
    return DatasetResult(
        spec=spec,
        candles=all_candles,
        fingerprint=spec.fingerprint(),
        warmup_count=warmup_count,
        effective_candle_count=live_count,
    )


# ---------------------------------------------------------------------------
# TestSchedulerConfigValidation
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestSchedulerConfigValidation:
    @pytest.mark.parametrize("profile", sorted(_VALID_PROFILES))
    def test_all_valid_profiles_pass(self, profile: str):
        SchedulerConfig(profile=profile).validate()  # must not raise

    def test_unknown_profile_raises(self):
        with pytest.raises(SchedulerError, match="Unknown speedup profile"):
            SchedulerConfig(profile="100x").validate()

    def test_empty_profile_raises(self):
        with pytest.raises(SchedulerError, match="Unknown speedup profile"):
            SchedulerConfig(profile="").validate()

    def test_case_sensitive_rejection(self):
        with pytest.raises(SchedulerError):
            SchedulerConfig(profile="INSTANT").validate()


# ---------------------------------------------------------------------------
# TestSchedulerInstantProfile
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestSchedulerInstantProfile:
    def test_instant_simulated_elapsed_is_none(self):
        dataset = _make_dataset(warmup_count=5, live_count=10)
        result = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="instant"))
        assert result.simulated_elapsed_ms is None

    def test_instant_has_correct_live_count(self):
        dataset = _make_dataset(warmup_count=5, live_count=10)
        result = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="instant"))
        assert result.live_candle_count == 10

    def test_instant_event_time_span(self):
        dataset = _make_dataset(warmup_count=0, live_count=5)
        result = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="instant"))
        expected_span = (5 - 1) * _ONE_MIN_MS
        assert result.event_time_span_ms == expected_span

    def test_single_live_candle_span_is_zero(self):
        dataset = _make_dataset(warmup_count=0, live_count=1)
        result = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="instant"))
        assert result.event_time_span_ms == 0
        assert result.simulated_elapsed_ms is None


# ---------------------------------------------------------------------------
# TestSchedulerNxProfiles
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestSchedulerNxProfiles:
    def test_1x_elapsed_equals_span(self):
        dataset = _make_dataset(warmup_count=0, live_count=11)
        result = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="1x"))
        assert result.simulated_elapsed_ms == result.event_time_span_ms

    def test_2x_elapsed_is_half_of_1x(self):
        dataset = _make_dataset(warmup_count=0, live_count=11)
        r1x = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="1x"))
        r2x = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="2x"))
        assert r2x.simulated_elapsed_ms == r1x.simulated_elapsed_ms // 2

    def test_5x_elapsed_correct(self):
        dataset = _make_dataset(warmup_count=0, live_count=11)
        r1x = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="1x"))
        r5x = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="5x"))
        expected = int(r1x.event_time_span_ms / _PROFILE_SPEEDUP["5x"])
        assert r5x.simulated_elapsed_ms == expected

    def test_10x_elapsed_correct(self):
        dataset = _make_dataset(warmup_count=0, live_count=11)
        r1x = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="1x"))
        r10x = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="10x"))
        expected = int(r1x.event_time_span_ms / _PROFILE_SPEEDUP["10x"])
        assert r10x.simulated_elapsed_ms == expected

    def test_higher_speedup_lower_elapsed(self):
        dataset = _make_dataset(warmup_count=0, live_count=61)
        r1x = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="1x"))
        r10x = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="10x"))
        assert r10x.simulated_elapsed_ms < r1x.simulated_elapsed_ms

    def test_single_live_candle_nx_elapsed_zero(self):
        dataset = _make_dataset(warmup_count=0, live_count=1)
        for profile in ("1x", "2x", "5x", "10x"):
            result = ReplayScheduler().schedule(dataset, SchedulerConfig(profile=profile))
            assert result.simulated_elapsed_ms == 0, f"profile={profile}"


# ---------------------------------------------------------------------------
# TestSchedulerWindowBoundary
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestSchedulerWindowBoundary:
    def test_warmup_live_split_content(self):
        dataset = _make_dataset(warmup_count=3, live_count=7)
        result = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="instant"))
        assert result.warmup_count == 3
        assert len(result.warmup_candles) == 3
        assert result.live_candle_count == 7
        assert len(result.live_candles) == 7

    def test_warmup_and_live_are_disjoint(self):
        dataset = _make_dataset(warmup_count=3, live_count=7)
        result = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="instant"))
        warmup_ts = {c["ts_ms"] for c in result.warmup_candles}
        live_ts = {c["ts_ms"] for c in result.live_candles}
        assert warmup_ts.isdisjoint(live_ts)

    def test_warmup_plus_live_equals_total(self):
        dataset = _make_dataset(warmup_count=4, live_count=6)
        result = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="instant"))
        assert len(result.warmup_candles) + len(result.live_candles) == len(dataset.candles)

    def test_live_window_starts_at_spec_start_ts(self):
        dataset = _make_dataset(warmup_count=5, live_count=10)
        result = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="instant"))
        assert result.live_candles[0]["ts_ms"] == dataset.spec.start_ts_ms

    def test_live_window_ends_at_spec_end_ts(self):
        dataset = _make_dataset(warmup_count=5, live_count=10)
        result = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="instant"))
        assert result.live_candles[-1]["ts_ms"] == dataset.spec.end_ts_ms

    def test_zero_warmup_all_live(self):
        dataset = _make_dataset(warmup_count=0, live_count=10)
        result = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="instant"))
        assert result.warmup_count == 0
        assert result.live_candle_count == 10
        assert len(result.warmup_candles) == 0

    def test_start_ts_mismatch_raises(self):
        all_candles = _make_candles(5)
        spec = DatasetSpec(
            symbol="BTCUSDT",
            timeframe="1m",
            start_ts_ms=all_candles[0]["ts_ms"] + 99,  # deliberate mismatch
            end_ts_ms=all_candles[-1]["ts_ms"],
            warmup_candles=0,
            source="file",
            file_path="/fake/mismatch.json",
        )
        dataset = DatasetResult(
            spec=spec,
            candles=all_candles,
            fingerprint=spec.fingerprint(),
            warmup_count=0,
            effective_candle_count=5,
        )
        with pytest.raises(SchedulerError, match="Live window start mismatch"):
            ReplayScheduler().schedule(dataset, SchedulerConfig(profile="instant"))

    def test_end_ts_mismatch_raises(self):
        all_candles = _make_candles(5)
        spec = DatasetSpec(
            symbol="BTCUSDT",
            timeframe="1m",
            start_ts_ms=all_candles[0]["ts_ms"],
            end_ts_ms=all_candles[-1]["ts_ms"] + 99,  # deliberate mismatch
            warmup_candles=0,
            source="file",
            file_path="/fake/mismatch.json",
        )
        dataset = DatasetResult(
            spec=spec,
            candles=all_candles,
            fingerprint=spec.fingerprint(),
            warmup_count=0,
            effective_candle_count=5,
        )
        with pytest.raises(SchedulerError, match="Live window end mismatch"):
            ReplayScheduler().schedule(dataset, SchedulerConfig(profile="instant"))

    def test_all_warmup_empty_live_raises(self):
        all_candles = _make_candles(5)
        # spec.start_ts_ms = all_candles[0] but warmup_count=5 → empty live
        spec = DatasetSpec(
            symbol="BTCUSDT",
            timeframe="1m",
            start_ts_ms=all_candles[0]["ts_ms"],
            end_ts_ms=all_candles[-1]["ts_ms"],
            warmup_candles=5,
            source="file",
            file_path="/fake/all_warmup.json",
        )
        dataset = DatasetResult(
            spec=spec,
            candles=all_candles,
            fingerprint=spec.fingerprint(),
            warmup_count=5,
            effective_candle_count=0,
        )
        with pytest.raises(SchedulerError, match="No live candles"):
            ReplayScheduler().schedule(dataset, SchedulerConfig(profile="instant"))

    def test_warmup_count_exceeds_candles_raises(self):
        all_candles = _make_candles(3)
        spec = DatasetSpec(
            symbol="BTCUSDT",
            timeframe="1m",
            start_ts_ms=all_candles[0]["ts_ms"],
            end_ts_ms=all_candles[-1]["ts_ms"],
            warmup_candles=3,
            source="file",
            file_path="/fake/overflow.json",
        )
        dataset = DatasetResult(
            spec=spec,
            candles=all_candles,
            fingerprint=spec.fingerprint(),
            warmup_count=10,  # larger than len(candles)
            effective_candle_count=0,
        )
        with pytest.raises(SchedulerError, match="warmup_count"):
            ReplayScheduler().schedule(dataset, SchedulerConfig(profile="instant"))


# ---------------------------------------------------------------------------
# TestSchedulerDeterminism
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestSchedulerDeterminism:
    def test_same_inputs_produce_identical_result(self):
        dataset = _make_dataset(warmup_count=5, live_count=10)
        config = SchedulerConfig(profile="2x")
        r1 = ReplayScheduler().schedule(dataset, config)
        r2 = ReplayScheduler().schedule(dataset, config)
        assert r1 == r2

    def test_to_dict_is_deterministic(self):
        dataset = _make_dataset(warmup_count=5, live_count=10)
        result = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="2x"))
        assert result.to_dict() == result.to_dict()

    def test_instant_to_dict_has_no_simulated_elapsed_key(self):
        dataset = _make_dataset(warmup_count=0, live_count=5)
        result = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="instant"))
        assert "simulated_elapsed_ms" not in result.to_dict()

    def test_nx_to_dict_has_simulated_elapsed_key(self):
        dataset = _make_dataset(warmup_count=0, live_count=5)
        for profile in ("1x", "2x", "5x", "10x"):
            result = ReplayScheduler().schedule(dataset, SchedulerConfig(profile=profile))
            assert "simulated_elapsed_ms" in result.to_dict(), f"profile={profile}"

    def test_to_dict_required_keys_present(self):
        dataset = _make_dataset(warmup_count=0, live_count=5)
        result = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="2x"))
        d = result.to_dict()
        for key in ("profile", "warmup_count", "live_candle_count", "event_time_span_ms"):
            assert key in d, f"missing key: {key}"

    def test_result_is_frozen(self):
        dataset = _make_dataset(warmup_count=0, live_count=5)
        result = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="instant"))
        with pytest.raises((AttributeError, TypeError)):
            result.profile = "2x"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TestSchedulerProfileNeutrality
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestSchedulerProfileNeutrality:
    def test_live_candles_order_same_across_profiles(self):
        dataset = _make_dataset(warmup_count=5, live_count=10)
        results = {
            profile: ReplayScheduler().schedule(dataset, SchedulerConfig(profile=profile))
            for profile in _VALID_PROFILES
        }
        reference_live = results["instant"].live_candles
        for profile, result in results.items():
            assert result.live_candles == reference_live, (
                f"live_candles differ for profile={profile}"
            )

    def test_warmup_split_same_across_profiles(self):
        dataset = _make_dataset(warmup_count=5, live_count=10)
        results = {
            profile: ReplayScheduler().schedule(dataset, SchedulerConfig(profile=profile))
            for profile in _VALID_PROFILES
        }
        reference_warmup = results["instant"].warmup_candles
        for profile, result in results.items():
            assert result.warmup_candles == reference_warmup, (
                f"warmup_candles differ for profile={profile}"
            )

    def test_different_profiles_different_simulated_elapsed(self):
        dataset = _make_dataset(warmup_count=0, live_count=61)
        r1x = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="1x"))
        r5x = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="5x"))
        r10x = ReplayScheduler().schedule(dataset, SchedulerConfig(profile="10x"))
        assert r1x.simulated_elapsed_ms > r5x.simulated_elapsed_ms
        assert r5x.simulated_elapsed_ms > r10x.simulated_elapsed_ms
