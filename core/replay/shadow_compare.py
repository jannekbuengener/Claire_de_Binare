"""ARVP replay-vs-paper shadow comparison core.

Scope (#1848): deterministic, offline comparison of replay output windows
against explicit paper-trading reference windows.  No DB/Redis wiring.

Design rules:
  - Both sides are explicit, caller-supplied structs (no live data access).
  - compare_windows() is a pure function; fails closed on misalignment or
    missing reference.
  - All rate values use Decimal with fixed quantization (no-float rule).
  - Deterministic: same inputs produce identical comparison_fingerprint.
  - write_shadow_comparison_artifact() is the sole I/O entry point; fail-closed.

Fail-closed conditions:
  - paper reference is None:  ShadowCompareError("missing_reference: …")
  - symbol mismatch:          ShadowCompareError("misaligned: …")
  - strategy_id mismatch:     ShadowCompareError("misaligned: …")
  - no temporal overlap:      ShadowCompareError("misaligned: no temporal overlap …")

Non-goals:
  - DB/Redis collectors or live data access
  - Event-level timing comparison (no offline event data surface in repo)
  - Reporter/runner modifications
  - Dashboard or management-grade UX reports (#1847)
  - Regime analytics (#1846)
  - CLI wiring

relations:
  domain: validation
  upstream:
    - core.replay.canonical_json  (canonical_hash, canonical_json_dumps)
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from core.replay.canonical_json import canonical_hash, canonical_json_dumps

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RATE_Q = Decimal("0.00000001")
_SHADOW_COMPARISON_FILENAME = "shadow_comparison.json"

# Validation patterns (consistent with run_registry conventions)
_RUN_ID_RE = re.compile(r"^replay-[a-f0-9]{12}-\d{4}$")
_HEX_64_RE = re.compile(r"^[a-f0-9]{64}$")


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------


class ShadowCompareError(ValueError):
    """Raised when shadow comparison fails validation, alignment, or I/O."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _require_non_empty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ShadowCompareError(f"{field_name} must be a non-empty string")


def _require_non_negative_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ShadowCompareError(f"{field_name} must be a non-negative int")


def _parse_utc_datetime(value: str, field_name: str) -> datetime:
    _require_non_empty_string(value, field_name)
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ShadowCompareError(
            f"{field_name} must be a valid ISO-8601 datetime: {exc}"
        ) from exc
    if dt.tzinfo is None:
        raise ShadowCompareError(f"{field_name} must include timezone info")
    return dt


def _compute_fill_rate(fill_count: int, reject_count: int) -> Decimal:
    total = fill_count + reject_count
    if total == 0:
        return Decimal("0").quantize(_RATE_Q)
    return (Decimal(fill_count) / Decimal(total)).quantize(_RATE_Q)


# ---------------------------------------------------------------------------
# Input structs (caller-supplied; no live data access)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PaperReferenceWindow:
    """Explicit caller-supplied paper-trading reference window for comparison.

    Callers are responsible for selecting a window that is meaningful for the
    replay under comparison.  The comparison layer does not infer windows from
    live DB or Redis.

    provenance_id traces back to a specific paper run or export record and must
    be non-empty; its format is not constrained beyond that.
    """

    symbol: str
    strategy_id: str
    window_start_utc: str
    window_end_utc: str
    signal_count: int
    fill_count: int
    reject_count: int
    provenance_id: str

    def __post_init__(self) -> None:
        _require_non_empty_string(self.symbol, "symbol")
        _require_non_empty_string(self.strategy_id, "strategy_id")
        _require_non_empty_string(self.provenance_id, "provenance_id")
        start = _parse_utc_datetime(self.window_start_utc, "window_start_utc")
        end = _parse_utc_datetime(self.window_end_utc, "window_end_utc")
        if end <= start:
            raise ShadowCompareError(
                "window_end_utc must be strictly after window_start_utc"
            )
        for name, val in (
            ("signal_count", self.signal_count),
            ("fill_count", self.fill_count),
            ("reject_count", self.reject_count),
        ):
            _require_non_negative_int(val, name)

    def to_dict(self) -> dict:
        return {
            "fill_count": self.fill_count,
            "provenance_id": self.provenance_id,
            "reject_count": self.reject_count,
            "signal_count": self.signal_count,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "window_end_utc": self.window_end_utc,
            "window_start_utc": self.window_start_utc,
        }


@dataclass(frozen=True, slots=True)
class ReplayOutputWindow:
    """Explicit caller-supplied replay output window for comparison.

    Represents the observable output of a completed ARVP replay run,
    distilled into count-oriented metrics for comparison against paper.
    dataset_fingerprint must be the 64-char hex hash used in run_registry.
    """

    run_id: str
    symbol: str
    strategy_id: str
    window_start_utc: str
    window_end_utc: str
    signal_count: int
    fill_count: int
    reject_count: int
    dataset_fingerprint: str

    def __post_init__(self) -> None:
        if not _RUN_ID_RE.match(self.run_id):
            raise ShadowCompareError(
                "run_id must match 'replay-<12 hex>-<4 digit attempt>'"
            )
        _require_non_empty_string(self.symbol, "symbol")
        _require_non_empty_string(self.strategy_id, "strategy_id")
        start = _parse_utc_datetime(self.window_start_utc, "window_start_utc")
        end = _parse_utc_datetime(self.window_end_utc, "window_end_utc")
        if end <= start:
            raise ShadowCompareError(
                "window_end_utc must be strictly after window_start_utc"
            )
        for name, val in (
            ("signal_count", self.signal_count),
            ("fill_count", self.fill_count),
            ("reject_count", self.reject_count),
        ):
            _require_non_negative_int(val, name)
        if not _HEX_64_RE.match(self.dataset_fingerprint):
            raise ShadowCompareError(
                "dataset_fingerprint must be a 64-char lowercase hex hash"
            )

    def to_dict(self) -> dict:
        return {
            "dataset_fingerprint": self.dataset_fingerprint,
            "fill_count": self.fill_count,
            "reject_count": self.reject_count,
            "run_id": self.run_id,
            "signal_count": self.signal_count,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "window_end_utc": self.window_end_utc,
            "window_start_utc": self.window_start_utc,
        }


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ShadowComparisonResult:
    """Machine-readable replay-vs-paper comparison result.

    Produced by compare_windows() for aligned inputs only.
    All count deltas are computed as (replay − paper).
    fill_rate_delta = fill_rate_replay − fill_rate_paper.
    comparison_fingerprint is a deterministic SHA-256 hash of both input windows.
    alignment_issue is None for aligned results.
    """

    comparison_fingerprint: str
    status: str  # always "aligned" when returned from compare_windows()
    alignment_issue: str | None
    replay_run_id: str
    paper_provenance_id: str
    symbol: str
    strategy_id: str
    signal_count_delta: int
    fill_count_delta: int
    reject_count_delta: int
    fill_rate_replay: Decimal
    fill_rate_paper: Decimal
    fill_rate_delta: Decimal
    window_start_utc_replay: str
    window_end_utc_replay: str
    window_start_utc_paper: str
    window_end_utc_paper: str

    def to_dict(self) -> dict:
        result: dict = {
            "comparison_fingerprint": self.comparison_fingerprint,
            "fill_count_delta": self.fill_count_delta,
            "fill_rate_delta": str(self.fill_rate_delta),
            "fill_rate_paper": str(self.fill_rate_paper),
            "fill_rate_replay": str(self.fill_rate_replay),
            "paper_provenance_id": self.paper_provenance_id,
            "reject_count_delta": self.reject_count_delta,
            "replay_run_id": self.replay_run_id,
            "signal_count_delta": self.signal_count_delta,
            "status": self.status,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "window_end_utc_paper": self.window_end_utc_paper,
            "window_end_utc_replay": self.window_end_utc_replay,
            "window_start_utc_paper": self.window_start_utc_paper,
            "window_start_utc_replay": self.window_start_utc_replay,
        }
        if self.alignment_issue is not None:
            result["alignment_issue"] = self.alignment_issue
        return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compare_windows(
    replay: ReplayOutputWindow,
    paper: PaperReferenceWindow | None,
) -> ShadowComparisonResult:
    """Compare a replay output window against a paper-trading reference window.

    Both sides must be explicitly provided by the caller.  The function is
    pure and performs no I/O.

    Raises:
        ShadowCompareError: when paper is None (missing_reference), or when the
            two windows cannot be meaningfully compared (misaligned) due to
            symbol mismatch, strategy_id mismatch, or lack of temporal overlap.
    """
    if paper is None:
        raise ShadowCompareError(
            "missing_reference: no paper reference window supplied"
        )
    if replay.symbol != paper.symbol:
        raise ShadowCompareError(
            f"misaligned: symbol mismatch "
            f"(replay={replay.symbol!r}, paper={paper.symbol!r})"
        )
    if replay.strategy_id != paper.strategy_id:
        raise ShadowCompareError(
            f"misaligned: strategy_id mismatch "
            f"(replay={replay.strategy_id!r}, paper={paper.strategy_id!r})"
        )

    r_start = _parse_utc_datetime(replay.window_start_utc, "replay.window_start_utc")
    r_end = _parse_utc_datetime(replay.window_end_utc, "replay.window_end_utc")
    p_start = _parse_utc_datetime(paper.window_start_utc, "paper.window_start_utc")
    p_end = _parse_utc_datetime(paper.window_end_utc, "paper.window_end_utc")

    overlap_start = max(r_start, p_start)
    overlap_end = min(r_end, p_end)
    if overlap_end <= overlap_start:
        raise ShadowCompareError(
            f"misaligned: no temporal overlap between replay window "
            f"({replay.window_start_utc} – {replay.window_end_utc}) "
            f"and paper window "
            f"({paper.window_start_utc} – {paper.window_end_utc})"
        )

    fill_rate_r = _compute_fill_rate(replay.fill_count, replay.reject_count)
    fill_rate_p = _compute_fill_rate(paper.fill_count, paper.reject_count)
    fill_rate_delta = (fill_rate_r - fill_rate_p).quantize(_RATE_Q)

    fingerprint = canonical_hash({"paper": paper.to_dict(), "replay": replay.to_dict()})

    return ShadowComparisonResult(
        comparison_fingerprint=fingerprint,
        status="aligned",
        alignment_issue=None,
        replay_run_id=replay.run_id,
        paper_provenance_id=paper.provenance_id,
        symbol=replay.symbol,
        strategy_id=replay.strategy_id,
        signal_count_delta=replay.signal_count - paper.signal_count,
        fill_count_delta=replay.fill_count - paper.fill_count,
        reject_count_delta=replay.reject_count - paper.reject_count,
        fill_rate_replay=fill_rate_r,
        fill_rate_paper=fill_rate_p,
        fill_rate_delta=fill_rate_delta,
        window_start_utc_replay=replay.window_start_utc,
        window_end_utc_replay=replay.window_end_utc,
        window_start_utc_paper=paper.window_start_utc,
        window_end_utc_paper=paper.window_end_utc,
    )


def build_calibration_summary(result: ShadowComparisonResult) -> str:
    """Build a concise operator-readable calibration summary.

    Every line maps directly to a field in ShadowComparisonResult.
    No invented narrative or subjective commentary.
    """
    lines = [
        "# Replay-vs-Paper Calibration Summary",
        "",
        f"Status:           {result.status}",
        f"Replay run:       {result.replay_run_id}",
        f"Paper reference:  {result.paper_provenance_id}",
        f"Symbol:           {result.symbol}",
        f"Strategy:         {result.strategy_id}",
        f"Fingerprint:      {result.comparison_fingerprint}",
        "",
        "## Window Alignment",
        f"Replay:  {result.window_start_utc_replay} – {result.window_end_utc_replay}",
        f"Paper:   {result.window_start_utc_paper} – {result.window_end_utc_paper}",
        "",
        "## Count Deltas (replay − paper)",
        f"Signal count delta:  {result.signal_count_delta:+d}",
        f"Fill count delta:    {result.fill_count_delta:+d}",
        f"Reject count delta:  {result.reject_count_delta:+d}",
        "",
        "## Fill Rate",
        f"Replay fill rate:  {result.fill_rate_replay}",
        f"Paper fill rate:   {result.fill_rate_paper}",
        f"Fill rate delta:   {result.fill_rate_delta:+}",
    ]
    if result.alignment_issue is not None:
        lines += ["", f"Alignment issue: {result.alignment_issue}"]
    return "\n".join(lines)


def write_shadow_comparison_artifact(
    result: ShadowComparisonResult,
    artifact_root: str | pathlib.Path,
) -> None:
    """Write shadow_comparison.json into artifact_root.  Fail-closed on I/O errors."""
    artifact_root = pathlib.Path(artifact_root)
    try:
        artifact_root.mkdir(parents=True, exist_ok=True)
        out_path = artifact_root / _SHADOW_COMPARISON_FILENAME
        out_path.write_text(canonical_json_dumps(result.to_dict()), encoding="utf-8")
    except OSError as exc:
        raise ShadowCompareError(
            f"Failed to write {_SHADOW_COMPARISON_FILENAME} to {artifact_root}: {exc}"
        ) from exc
