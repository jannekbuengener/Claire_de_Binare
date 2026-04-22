"""ARVP Replay Scheduler — event-time metadata and warmup/live split.

Scope (#1842): deterministic speed profiles, window boundary validation,
warmup/live partitioning. No wall-clock pacing, no threading, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.replay.dataset_provider import DatasetResult

_VALID_PROFILES: frozenset[str] = frozenset({"instant", "1x", "2x", "5x", "10x"})
_PROFILE_SPEEDUP: dict[str, float | None] = {
    "instant": None,
    "1x": 1.0,
    "2x": 2.0,
    "5x": 5.0,
    "10x": 10.0,
}


class SchedulerError(ValueError):
    """Raised when scheduler configuration or dataset invariants fail validation."""


@dataclass(frozen=True, slots=True)
class SchedulerConfig:
    profile: str

    def validate(self) -> None:
        if not self.profile or self.profile not in _VALID_PROFILES:
            raise SchedulerError(
                f"Unknown speedup profile {self.profile!r}. "
                f"Valid profiles: {sorted(_VALID_PROFILES)}"
            )


@dataclass(frozen=True, slots=True)
class SchedulerResult:
    profile: str
    warmup_candles: tuple
    live_candles: tuple
    warmup_count: int
    live_candle_count: int
    event_time_span_ms: int
    simulated_elapsed_ms: int | None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "profile": self.profile,
            "warmup_count": self.warmup_count,
            "live_candle_count": self.live_candle_count,
            "event_time_span_ms": self.event_time_span_ms,
        }
        if self.simulated_elapsed_ms is not None:
            d["simulated_elapsed_ms"] = self.simulated_elapsed_ms
        return d


class ReplayScheduler:
    """Partitions a DatasetResult into warmup/live windows and derives timing metadata."""

    def schedule(
        self, dataset: DatasetResult, config: SchedulerConfig
    ) -> SchedulerResult:
        config.validate()

        spec = dataset.spec
        all_candles = dataset.candles
        warmup_count = dataset.warmup_count

        if warmup_count > len(all_candles):
            raise SchedulerError(
                f"warmup_count {warmup_count} exceeds total candles {len(all_candles)}"
            )

        warmup_candles: tuple = all_candles[:warmup_count]
        live_candles: tuple = all_candles[warmup_count:]

        if not live_candles:
            raise SchedulerError("No live candles remain after warmup split")

        if warmup_count != dataset.warmup_count:  # pragma: no cover — tautology guard
            raise SchedulerError("Inconsistent warmup_count between dataset and split")

        first_live_ts: int = int(live_candles[0]["ts_ms"])
        last_live_ts: int = int(live_candles[-1]["ts_ms"])

        if first_live_ts != spec.start_ts_ms:
            raise SchedulerError(
                f"Live window start mismatch: first live candle ts_ms={first_live_ts} "
                f"!= spec.start_ts_ms={spec.start_ts_ms}"
            )
        if last_live_ts != spec.end_ts_ms:
            raise SchedulerError(
                f"Live window end mismatch: last live candle ts_ms={last_live_ts} "
                f"!= spec.end_ts_ms={spec.end_ts_ms}"
            )

        event_time_span_ms: int = last_live_ts - first_live_ts

        speedup = _PROFILE_SPEEDUP[config.profile]
        simulated_elapsed_ms: int | None = (
            None if speedup is None else int(event_time_span_ms / speedup)
        )

        return SchedulerResult(
            profile=config.profile,
            warmup_candles=warmup_candles,
            live_candles=live_candles,
            warmup_count=warmup_count,
            live_candle_count=len(live_candles),
            event_time_span_ms=event_time_span_ms,
            simulated_elapsed_ms=simulated_elapsed_ms,
        )
