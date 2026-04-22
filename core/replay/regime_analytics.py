"""ARVP regime analytics: regime-segmented KPI scoring.

Scope (#1846): deterministic regime-segmented scorecards and artifact writing.

Design rules:
  - Regime IDs are repo-backed string literals from services/regime/service.py.
  - Input protocol: caller supplies Sequence[RegimeKPIRecord]; regime context is
    explicit, never inferred.
  - Missing/non-canonical regime IDs are transparently recorded and counted as
    unknown — nothing is silently dropped.
  - All monetary values use Decimal with fixed quantization (no-float rule).
  - compute_regime_scorecard is a pure function; no I/O.
  - write_regime_scorecard_artifact is the sole I/O entry point; fail-closed.
  - Deterministic: same inputs + same run_id → identical scorecard and fingerprint.

Non-goals:
  - regime classification or new regime models (services/regime owns that)
  - reporter/runner modifications
  - replay-vs-paper comparison
  - management-grade UX reports (#1847)
  - dashboard or UI
  - CLI wiring
"""

from __future__ import annotations

import pathlib
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from core.replay.canonical_json import canonical_hash, canonical_json_dumps

# ---------------------------------------------------------------------------
# Canonical regime IDs (repo-backed from services/regime/service.py)
# ---------------------------------------------------------------------------

#: Sentinel for missing or non-canonical regime context in caller-supplied records.
#: Use this constant (not the bare string) for future-proofness.
UNKNOWN_REGIME: str = "__unknown__"

#: Canonical regime ID strings emitted by services/regime/service.py.
#: Records whose regime_id is not in this set are counted as unknown.
KNOWN_REGIME_IDS: frozenset[str] = frozenset(
    {"TREND", "RANGE", "HIGH_VOL_CHAOTIC", "UNKNOWN"}
)

# Fixed quantization precision for monetary and rate values.
_PNL_Q = Decimal("0.00000001")
_RATE_Q = Decimal("0.00000001")


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------


class RegimeAnalyticsError(ValueError):
    """Raised when regime analytics validation or I/O fails."""


# ---------------------------------------------------------------------------
# Input type
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RegimeKPIRecord:
    """A single tagged KPI measurement for one regime context window.

    Callers supply a sequence of these to compute_regime_scorecard.
    Use UNKNOWN_REGIME as regime_id when the regime context is missing.

    All counts must be non-negative integers; pnl_sum must be a Decimal.
    """

    regime_id: str
    signal_count: int
    fill_count: int
    reject_count: int
    pnl_sum: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.regime_id, str) or not self.regime_id:
            raise RegimeAnalyticsError("regime_id must be a non-empty string")
        for field_name, value in (
            ("signal_count", self.signal_count),
            ("fill_count", self.fill_count),
            ("reject_count", self.reject_count),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise RegimeAnalyticsError(
                    f"{field_name} must be a non-negative int"
                )
        if not isinstance(self.pnl_sum, Decimal):
            raise RegimeAnalyticsError("pnl_sum must be a Decimal")


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RegimeSegmentStats:
    """Aggregated KPI stats for a single regime segment.

    fill_rate = fill_count / (fill_count + reject_count), or Decimal(0)
    when both are zero.  Both pnl_sum and fill_rate are quantized to
    _PNL_Q / _RATE_Q respectively for deterministic serialization.
    """

    regime_id: str
    record_count: int
    signal_count: int
    fill_count: int
    reject_count: int
    pnl_sum: Decimal
    fill_rate: Decimal

    def to_dict(self) -> dict:
        return {
            "regime_id": self.regime_id,
            "record_count": self.record_count,
            "signal_count": self.signal_count,
            "fill_count": self.fill_count,
            "reject_count": self.reject_count,
            "pnl_sum": str(self.pnl_sum),
            "fill_rate": str(self.fill_rate),
        }


@dataclass(frozen=True, slots=True)
class RegimeScorecard:
    """Full regime-segmented scorecard for a replay run.

    segments is sorted by regime_id for deterministic ordering.
    unknown_regime_count counts records whose regime_id is not in KNOWN_REGIME_IDS.
    input_fingerprint is the SHA-256 of the canonical JSON of the input records.
    """

    run_id: str
    segments: tuple[RegimeSegmentStats, ...]
    total_records: int
    unknown_regime_count: int
    input_fingerprint: str

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "total_records": self.total_records,
            "unknown_regime_count": self.unknown_regime_count,
            "input_fingerprint": self.input_fingerprint,
            "segments": [s.to_dict() for s in self.segments],
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fill_rate(fill_count: int, reject_count: int) -> Decimal:
    total = fill_count + reject_count
    if total == 0:
        return Decimal("0").quantize(_RATE_Q)
    return (Decimal(fill_count) / Decimal(total)).quantize(_RATE_Q)


def _fingerprint(records: Sequence[RegimeKPIRecord]) -> str:
    """Deterministic SHA-256 fingerprint of input records (order-sensitive)."""
    serializable = [
        {
            "fill_count": r.fill_count,
            "pnl_sum": str(r.pnl_sum),
            "regime_id": r.regime_id,
            "reject_count": r.reject_count,
            "signal_count": r.signal_count,
        }
        for r in records
    ]
    return canonical_hash(serializable)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_regime_scorecard(
    records: Sequence[RegimeKPIRecord],
    *,
    run_id: str,
) -> RegimeScorecard:
    """Compute a deterministic regime-segmented scorecard from KPI records.

    Groups records by regime_id, aggregates per-regime KPIs, and counts
    unknown/non-canonical regime IDs explicitly.  An empty input yields a
    valid empty scorecard — no error is raised.

    Args:
        records: Sequence of RegimeKPIRecord instances supplied by the caller.
        run_id:  Canonical run identifier (non-empty string).

    Returns:
        RegimeScorecard with segments sorted by regime_id, aggregate totals,
        unknown_regime_count, and a deterministic input_fingerprint.

    Raises:
        RegimeAnalyticsError if run_id is invalid.
    """
    if not isinstance(run_id, str) or not run_id.strip():
        raise RegimeAnalyticsError("run_id must be a non-empty string")

    # Materialize once so the sequence is safe to iterate multiple times and
    # len() is always correct, even if the caller passes a one-shot iterable.
    records_list = list(records)

    fingerprint = _fingerprint(records_list)

    groups: dict[str, list[RegimeKPIRecord]] = defaultdict(list)
    for rec in records_list:
        groups[rec.regime_id].append(rec)

    unknown_count = sum(
        len(recs)
        for regime_id, recs in groups.items()
        if regime_id not in KNOWN_REGIME_IDS
    )

    segments: list[RegimeSegmentStats] = []
    for regime_id in sorted(groups.keys()):
        recs = groups[regime_id]
        signal_sum = sum(r.signal_count for r in recs)
        fill_sum = sum(r.fill_count for r in recs)
        reject_sum = sum(r.reject_count for r in recs)
        pnl_total = sum((r.pnl_sum for r in recs), Decimal("0")).quantize(_PNL_Q)
        segments.append(
            RegimeSegmentStats(
                regime_id=regime_id,
                record_count=len(recs),
                signal_count=signal_sum,
                fill_count=fill_sum,
                reject_count=reject_sum,
                pnl_sum=pnl_total,
                fill_rate=_fill_rate(fill_sum, reject_sum),
            )
        )

    return RegimeScorecard(
        run_id=run_id,
        segments=tuple(segments),
        total_records=len(records_list),
        unknown_regime_count=unknown_count,
        input_fingerprint=fingerprint,
    )


def write_regime_scorecard_artifact(
    scorecard: RegimeScorecard,
    artifact_root: str | pathlib.Path,
) -> None:
    """Write regime_scorecard.json into artifact_root.

    Uses canonical JSON serialization for deterministic output.  The
    directory is created if it does not exist.  Fail-closed: raises
    RegimeAnalyticsError on any I/O failure.

    Args:
        scorecard:     Fully computed RegimeScorecard instance.
        artifact_root: Directory to write regime_scorecard.json into.

    Raises:
        RegimeAnalyticsError on I/O failure.
    """
    out_dir = pathlib.Path(artifact_root)
    artifact_path = out_dir / "regime_scorecard.json"
    json_bytes = canonical_json_dumps(scorecard.to_dict()).encode("utf-8")
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        artifact_path.write_bytes(json_bytes)
    except OSError as exc:
        raise RegimeAnalyticsError(
            f"Failed to write regime_scorecard.json to {artifact_path}: {exc}"
        ) from exc
