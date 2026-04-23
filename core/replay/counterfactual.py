"""
Counterfactual perturbation engine for ARVP (#1850).

Pure, fail-closed, deterministic "same day, but..." perturbation analysis
on caller-supplied replay baselines. No Runtime, DB, or Redis wiring.

Perturbation types:
  slippage_bps        [0, 10000]  -- fill attrition via spread shock
  entry_delay_bars    [1, 1000]   -- signal loss via delayed entry
  fill_rate_reduction [0, 1]      -- direct fill fraction reduction
  feed_gap_bars       [1, 10000]  -- signal loss via feed outage
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from pathlib import Path
from typing import Sequence

from core.replay.canonical_json import canonical_hash, canonical_json_dumps


class CounterfactualError(Exception):
    """Raised on invalid input, out-of-range magnitude, or I/O failure."""


# ---------------------------------------------------------------------------
# Perturbation type registry
# ---------------------------------------------------------------------------

_VALID_TYPES: frozenset[str] = frozenset(
    {"slippage_bps", "entry_delay_bars", "fill_rate_reduction", "feed_gap_bars"}
)

_MAGNITUDE_BOUNDS: dict[str, tuple[Decimal, Decimal]] = {
    "slippage_bps": (Decimal("0"), Decimal("10000")),
    "entry_delay_bars": (Decimal("1"), Decimal("1000")),
    "fill_rate_reduction": (Decimal("0"), Decimal("1")),
    "feed_gap_bars": (Decimal("1"), Decimal("10000")),
}


# ---------------------------------------------------------------------------
# Domain structs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PerturbationSpec:
    """A single, validated perturbation instruction."""

    perturbation_type: str
    magnitude: Decimal

    def __post_init__(self) -> None:
        if self.perturbation_type not in _VALID_TYPES:
            raise CounterfactualError(
                f"unknown perturbation type: {self.perturbation_type!r}; "
                f"valid types: {sorted(_VALID_TYPES)}"
            )
        lo, hi = _MAGNITUDE_BOUNDS[self.perturbation_type]
        if not (lo <= self.magnitude <= hi):
            raise CounterfactualError(
                f"magnitude {self.magnitude} out of range [{lo}, {hi}] "
                f"for type {self.perturbation_type!r}"
            )

    def to_dict(self) -> dict:
        return {
            "magnitude": str(self.magnitude),
            "perturbation_type": self.perturbation_type,
        }


@dataclass(frozen=True)
class CounterfactualBaseWindow:
    """Caller-supplied replay baseline. Validated at construction time."""

    symbol: str
    strategy_id: str
    window_start: str
    window_end: str
    signal_count: int
    fill_count: int
    reject_count: int
    fill_rate: Decimal

    def __post_init__(self) -> None:
        if not self.symbol:
            raise CounterfactualError("symbol must not be empty")
        if not self.strategy_id:
            raise CounterfactualError("strategy_id must not be empty")
        if not self.window_start:
            raise CounterfactualError("window_start must not be empty")
        if not self.window_end:
            raise CounterfactualError("window_end must not be empty")
        if self.signal_count < 0:
            raise CounterfactualError("signal_count must be >= 0")
        if self.fill_count < 0:
            raise CounterfactualError("fill_count must be >= 0")
        if self.reject_count < 0:
            raise CounterfactualError("reject_count must be >= 0")
        if not (Decimal("0") <= self.fill_rate <= Decimal("1")):
            raise CounterfactualError("fill_rate must be in [0, 1]")

    def to_dict(self) -> dict:
        return {
            "fill_count": self.fill_count,
            "fill_rate": str(self.fill_rate),
            "reject_count": self.reject_count,
            "signal_count": self.signal_count,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "window_end": self.window_end,
            "window_start": self.window_start,
        }


@dataclass(frozen=True)
class CounterfactualResult:
    """Immutable result of applying a perturbation sequence to a base window."""

    symbol: str
    strategy_id: str
    window_start: str
    window_end: str
    # Base (unperturbed) stats
    base_signal_count: int
    base_fill_count: int
    base_reject_count: int
    base_fill_rate: Decimal
    # Perturbed stats
    perturbed_signal_count: int
    perturbed_fill_count: int
    perturbed_reject_count: int
    perturbed_fill_rate: Decimal
    # Deltas (perturbed - base)
    signal_count_delta: int
    fill_count_delta: int
    reject_count_delta: int
    fill_rate_delta: Decimal
    # Metadata
    applied_perturbation_types: tuple  # sorted, deduplicated
    provenance_fingerprint: str

    def to_dict(self) -> dict:
        return {
            "applied_perturbation_types": list(self.applied_perturbation_types),
            "base_fill_count": self.base_fill_count,
            "base_fill_rate": str(self.base_fill_rate),
            "base_reject_count": self.base_reject_count,
            "base_signal_count": self.base_signal_count,
            "fill_count_delta": self.fill_count_delta,
            "fill_rate_delta": str(self.fill_rate_delta),
            "perturbed_fill_count": self.perturbed_fill_count,
            "perturbed_fill_rate": str(self.perturbed_fill_rate),
            "perturbed_reject_count": self.perturbed_reject_count,
            "perturbed_signal_count": self.perturbed_signal_count,
            "provenance_fingerprint": self.provenance_fingerprint,
            "reject_count_delta": self.reject_count_delta,
            "signal_count_delta": self.signal_count_delta,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "window_end": self.window_end,
            "window_start": self.window_start,
        }


# ---------------------------------------------------------------------------
# Internal perturbation handlers — pure functions
# ---------------------------------------------------------------------------


def _apply_slippage_bps(
    signal: int, fill: int, reject: int, magnitude: Decimal
) -> tuple[int, int, int]:
    """Signal unchanged; fills lost proportionally to bps; lost fills become rejects."""
    fills_lost = int(
        (Decimal(fill) * magnitude / Decimal("10000")).to_integral_value(
            rounding=ROUND_DOWN
        )
    )
    return signal, max(0, fill - fills_lost), reject + fills_lost


def _apply_entry_delay_bars(
    signal: int, fill: int, reject: int, magnitude: Decimal
) -> tuple[int, int, int]:
    """Signal drops by 1% per bar; surviving signals retain original fill/reject ratio."""
    fraction_retained = max(
        Decimal("0"), Decimal("1") - magnitude * Decimal("0.01")
    )
    new_signal = int(
        (Decimal(signal) * fraction_retained).to_integral_value(rounding=ROUND_DOWN)
    )
    new_signal = max(0, new_signal)
    if signal > 0:
        fill_fraction = Decimal(fill) / Decimal(signal)
        new_fill = int(
            (Decimal(new_signal) * fill_fraction).to_integral_value(rounding=ROUND_DOWN)
        )
    else:
        new_fill = 0
    new_fill = max(0, new_fill)
    new_reject = max(0, new_signal - new_fill)
    return new_signal, new_fill, new_reject


def _apply_fill_rate_reduction(
    signal: int, fill: int, reject: int, magnitude: Decimal
) -> tuple[int, int, int]:
    """Signal unchanged; magnitude fraction of fills converted to rejects."""
    fills_lost = int(
        (Decimal(fill) * magnitude).to_integral_value(rounding=ROUND_DOWN)
    )
    return signal, max(0, fill - fills_lost), reject + fills_lost


def _apply_feed_gap_bars(
    signal: int, fill: int, reject: int, magnitude: Decimal
) -> tuple[int, int, int]:
    """Signal drops by 0.5% per bar; surviving signals retain original fill/reject ratio."""
    fraction_retained = max(
        Decimal("0"), Decimal("1") - magnitude * Decimal("0.005")
    )
    new_signal = int(
        (Decimal(signal) * fraction_retained).to_integral_value(rounding=ROUND_DOWN)
    )
    new_signal = max(0, new_signal)
    if signal > 0:
        fill_fraction = Decimal(fill) / Decimal(signal)
        new_fill = int(
            (Decimal(new_signal) * fill_fraction).to_integral_value(rounding=ROUND_DOWN)
        )
    else:
        new_fill = 0
    new_fill = max(0, new_fill)
    new_reject = max(0, new_signal - new_fill)
    return new_signal, new_fill, new_reject


_PERTURBATION_HANDLERS: dict = {
    "slippage_bps": _apply_slippage_bps,
    "entry_delay_bars": _apply_entry_delay_bars,
    "fill_rate_reduction": _apply_fill_rate_reduction,
    "feed_gap_bars": _apply_feed_gap_bars,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def apply_perturbations(
    base: CounterfactualBaseWindow,
    specs: Sequence[PerturbationSpec],
) -> CounterfactualResult:
    """Apply a sequence of perturbations to the base window.

    Pure and fail-closed. Perturbations are applied sequentially; each
    handler receives the accumulated perturbed state from prior steps.
    All counts are clamped to 0 after each step.

    Args:
        base: Validated baseline replay window.
        specs: Non-empty sequence of perturbation specs to apply in order.

    Returns:
        CounterfactualResult with perturbed stats, deltas, and a
        deterministic provenance fingerprint.

    Raises:
        CounterfactualError: If base is None, specs is empty, or any spec
            is invalid (caught at PerturbationSpec construction time).
    """
    if base is None:
        raise CounterfactualError("base must not be None")
    if not specs:
        raise CounterfactualError(
            "no perturbations specified; provide at least one PerturbationSpec"
        )

    fingerprint = canonical_hash(
        {
            "base": base.to_dict(),
            "perturbations": [s.to_dict() for s in specs],
        }
    )

    signal = base.signal_count
    fill = base.fill_count
    reject = base.reject_count

    applied_types: list[str] = []
    for spec in specs:
        handler = _PERTURBATION_HANDLERS[spec.perturbation_type]
        signal, fill, reject = handler(signal, fill, reject, spec.magnitude)
        # Safety clamp after each step
        signal = max(0, signal)
        fill = max(0, fill)
        reject = max(0, reject)
        applied_types.append(spec.perturbation_type)

    perturbed_fill_rate = (
        Decimal(fill) / Decimal(signal) if signal > 0 else Decimal("0")
    )

    return CounterfactualResult(
        symbol=base.symbol,
        strategy_id=base.strategy_id,
        window_start=base.window_start,
        window_end=base.window_end,
        base_signal_count=base.signal_count,
        base_fill_count=base.fill_count,
        base_reject_count=base.reject_count,
        base_fill_rate=base.fill_rate,
        perturbed_signal_count=signal,
        perturbed_fill_count=fill,
        perturbed_reject_count=reject,
        perturbed_fill_rate=perturbed_fill_rate,
        signal_count_delta=signal - base.signal_count,
        fill_count_delta=fill - base.fill_count,
        reject_count_delta=reject - base.reject_count,
        fill_rate_delta=perturbed_fill_rate - base.fill_rate,
        applied_perturbation_types=tuple(sorted(set(applied_types))),
        provenance_fingerprint=fingerprint,
    )


def build_perturbation_summary(result: CounterfactualResult) -> str:
    """Return an operator-readable, metrically grounded perturbation summary.

    Strictly metric — no ungrounded narrative. All deltas are explicit.
    """
    lines = [
        "Counterfactual Perturbation Summary",
        "===================================",
        f"Symbol:              {result.symbol}",
        f"Strategy:            {result.strategy_id}",
        f"Window:              {result.window_start} -> {result.window_end}",
        f"Applied types:       {', '.join(result.applied_perturbation_types)}",
        "",
        "Base stats:",
        f"  signals:           {result.base_signal_count}",
        f"  fills:             {result.base_fill_count}",
        f"  rejects:           {result.base_reject_count}",
        f"  fill_rate:         {result.base_fill_rate}",
        "",
        "Perturbed stats:",
        f"  signals:           {result.perturbed_signal_count}",
        f"  fills:             {result.perturbed_fill_count}",
        f"  rejects:           {result.perturbed_reject_count}",
        f"  fill_rate:         {result.perturbed_fill_rate}",
        "",
        "Deltas:",
        f"  signal_delta:      {result.signal_count_delta:+d}",
        f"  fill_delta:        {result.fill_count_delta:+d}",
        f"  reject_delta:      {result.reject_count_delta:+d}",
        f"  fill_rate_delta:   {result.fill_rate_delta}",
        "",
        f"Fingerprint:         {result.provenance_fingerprint}",
    ]
    return "\n".join(lines)


def write_counterfactual_artifact(
    result: CounterfactualResult, artifact_root: Path
) -> None:
    """Write counterfactual_result.json to artifact_root. Fail-closed on I/O error.

    Args:
        result: Completed CounterfactualResult to serialize.
        artifact_root: Directory to write the artifact into (created if absent).

    Raises:
        CounterfactualError: On any I/O failure.
    """
    try:
        artifact_root = Path(artifact_root)
        artifact_root.mkdir(parents=True, exist_ok=True)
        out_path = artifact_root / "counterfactual_result.json"
        payload = canonical_json_dumps(result.to_dict())
        out_path.write_text(payload, encoding="utf-8")
    except (OSError, IOError) as exc:
        raise CounterfactualError(
            f"failed to write counterfactual artifact to {artifact_root}: {exc}"
        ) from exc
