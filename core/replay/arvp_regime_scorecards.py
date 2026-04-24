"""ARVP regime scorecards for replay and comparison outputs (#1904).

Goal:
  - Provide a repo-backed, deterministic regime-segmented reading surface.

Inputs:
  - Replay-side: a runner-supplied trace that includes per-step regime_id
    and per-step signal counts, plus trade closures with exit regime_id.
  - Comparison-side: optional regime breakdown if caller supplies it; this module
    does not invent regime segmentation from aggregate comparison deltas.

Design rules:
  - Deterministic: same inputs -> identical artifact bytes + fingerprint.
  - Explicit: missing regime context is surfaced as unavailable/insufficient-data.
  - Reporting only: no policy semantics, no live-readiness meaning.
  - Fail-closed: invalid inputs raise ARVPRegimeScorecardError at the API layer.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash, canonical_json_dumps

_SCHEMA_VERSION = "arvp_regime_scorecard.v1"
_FILENAME_JSON = "arvp_regime_scorecard.json"
_FILENAME_MD = "arvp_regime_scorecard_summary.md"

_STATUS_OK = "ok"
_STATUS_UNAVAILABLE = "unavailable"
_STATUS_INSUFFICIENT = "insufficient-data"


class ARVPRegimeScorecardError(ValueError):
    """Raised when regime scorecard inputs cannot be parsed or written."""


def _require_mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ARVPRegimeScorecardError(f"{name} must be a JSON object")
    return value


def _require_non_empty_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ARVPRegimeScorecardError(f"{name} must be a non-empty string")
    return value


def _optional_non_empty_string(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _require_non_empty_string(value, name)


def _require_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ARVPRegimeScorecardError(f"{name} must be an int")
    return value


def _optional_decimal(value: object, name: str) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, str):
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError) as exc:
            raise ARVPRegimeScorecardError(f"{name} must be a Decimal string: {exc}") from exc
    raise ARVPRegimeScorecardError(f"{name} must be a string or null")


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ARVPRegimeScorecardError(f"Failed to read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ARVPRegimeScorecardError(f"Invalid JSON in {path}: {exc}") from exc


def _regime_str_from_raw(raw: object) -> str | None:
    # Accept canonical strings, or the stable numeric mapping used in market_state.
    if isinstance(raw, str) and raw.strip():
        return raw.strip().upper()
    if isinstance(raw, int) and not isinstance(raw, bool):
        if raw == 0:
            return "TREND"
        if raw == 1:
            return "RANGE"
        if raw == 2:
            return "HIGH_VOL_CHAOTIC"
        if raw == 3:
            return "CRISIS"
        return "UNKNOWN"
    return None


@dataclass(frozen=True, slots=True)
class RegimeSegmentScore:
    regime_id: str
    observation_count: int
    signal_count: int
    trade_close_count: int
    pnl_sum_r: Decimal | None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "observation_count": self.observation_count,
            "regime_id": self.regime_id,
            "signal_count": self.signal_count,
            "trade_close_count": self.trade_close_count,
        }
        if self.pnl_sum_r is not None:
            payload["pnl_sum_r"] = str(self.pnl_sum_r)
        return payload


@dataclass(frozen=True, slots=True)
class ARVPRegimeScorecard:
    schema_version: str
    status: str  # ok | unavailable | insufficient-data
    run_id: str
    source: str  # replay_trace | comparison | unknown
    scorecard_fingerprint: str
    segments: tuple[RegimeSegmentScore, ...]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "notes": list(self.notes),
            "run_id": self.run_id,
            "schema_version": self.schema_version,
            "scorecard_fingerprint": self.scorecard_fingerprint,
            "segments": [s.to_dict() for s in self.segments],
            "source": self.source,
            "status": self.status,
        }


def build_scorecard_summary(scorecard: ARVPRegimeScorecard) -> str:
    lines = [
        "# ARVP Regime Scorecard Summary",
        "",
        f"Status:      {scorecard.status}",
        f"Run:         {scorecard.run_id}",
        f"Source:      {scorecard.source}",
        f"Fingerprint: {scorecard.scorecard_fingerprint}",
        "",
        "## Per-Regime",
        "",
        "| Regime | Observations | Signals | Trade closes | PnL sum (R) |",
        "|--------|--------------|---------|-------------|-------------|",
    ]
    if scorecard.segments:
        for seg in scorecard.segments:
            pnl = str(seg.pnl_sum_r) if seg.pnl_sum_r is not None else "—"
            lines.append(
                f"| {seg.regime_id} | {seg.observation_count} | {seg.signal_count} | {seg.trade_close_count} | {pnl} |"
            )
    else:
        lines.append("| — | — | — | — | — |")
    if scorecard.notes:
        lines += ["", "## Notes"]
        lines += [f"- {n}" for n in scorecard.notes]
    return "\n".join(lines) + "\n"


def build_replay_regime_scorecard_from_trace(
    trace: Mapping[str, Any],
) -> ARVPRegimeScorecard:
    """Build a regime scorecard from a runner-supplied replay trace.

    Expected minimal trace shape (v1; intentionally permissive):
      - run_id: string
      - steps: list[{ ts_ms:int, regime_id:(int|str|None), signals_emitted:int }]
      - trades: list[{ exit_ts_ms:int, exit_regime_id:(int|str|None), r_return:(str|None) }]
    """
    t = _require_mapping(trace, "trace")
    run_id = _require_non_empty_string(t.get("run_id"), "run_id")
    steps = t.get("steps")
    if not isinstance(steps, list):
        raise ARVPRegimeScorecardError("steps must be a list")
    trades = t.get("trades")
    if not isinstance(trades, list):
        raise ARVPRegimeScorecardError("trades must be a list")

    obs_counts: dict[str, int] = {}
    signal_counts: dict[str, int] = {}
    close_counts: dict[str, int] = {}
    pnl_sums: dict[str, Decimal] = {}
    notes: list[str] = []

    missing_regime_steps = 0
    for idx, raw in enumerate(steps):
        step = _require_mapping(raw, f"steps[{idx}]")
        _require_int(step.get("ts_ms"), f"steps[{idx}].ts_ms")
        signals_emitted = _require_int(
            step.get("signals_emitted"), f"steps[{idx}].signals_emitted"
        )
        if signals_emitted < 0:
            raise ARVPRegimeScorecardError(
                f"steps[{idx}].signals_emitted must be >= 0"
            )
        regime = _regime_str_from_raw(step.get("regime_id"))
        if regime is None:
            missing_regime_steps += 1
            continue
        obs_counts[regime] = obs_counts.get(regime, 0) + 1
        signal_counts[regime] = signal_counts.get(regime, 0) + signals_emitted

    missing_regime_trades = 0
    for idx, raw in enumerate(trades):
        tr = _require_mapping(raw, f"trades[{idx}]")
        _require_int(tr.get("exit_ts_ms"), f"trades[{idx}].exit_ts_ms")
        regime = _regime_str_from_raw(tr.get("exit_regime_id"))
        if regime is None:
            missing_regime_trades += 1
            continue
        close_counts[regime] = close_counts.get(regime, 0) + 1
        r_return = _optional_non_empty_string(tr.get("r_return"), f"trades[{idx}].r_return")
        if r_return is not None:
            try:
                pnl_sums[regime] = pnl_sums.get(regime, Decimal("0")) + Decimal(r_return)
            except (InvalidOperation, ValueError) as exc:
                raise ARVPRegimeScorecardError(
                    f"trades[{idx}].r_return must be Decimal-like: {exc}"
                ) from exc

    if not obs_counts and missing_regime_steps:
        status = _STATUS_UNAVAILABLE
        notes.append("unavailable: no regime_id present in replay trace steps")
    elif not obs_counts:
        status = _STATUS_INSUFFICIENT
        notes.append("insufficient-data: no steps in trace")
    else:
        status = _STATUS_OK
        if missing_regime_steps:
            notes.append(f"partial_regime_coverage_steps: missing={missing_regime_steps}")
        if missing_regime_trades:
            notes.append(f"partial_regime_coverage_trades: missing={missing_regime_trades}")

    all_regimes = sorted(set(obs_counts) | set(signal_counts) | set(close_counts) | set(pnl_sums))
    segments: list[RegimeSegmentScore] = []
    for regime in all_regimes:
        pnl = pnl_sums.get(regime)
        segments.append(
            RegimeSegmentScore(
                regime_id=regime,
                observation_count=obs_counts.get(regime, 0),
                signal_count=signal_counts.get(regime, 0),
                trade_close_count=close_counts.get(regime, 0),
                pnl_sum_r=pnl,
            )
        )

    fp = canonical_hash(
        {
            "run_id": run_id,
            "schema_version": _SCHEMA_VERSION,
            "segments": [s.to_dict() for s in segments],
            "notes": notes,
            "source": "replay_trace",
            "status": status,
        }
    )

    return ARVPRegimeScorecard(
        schema_version=_SCHEMA_VERSION,
        status=status,
        run_id=run_id,
        source="replay_trace",
        scorecard_fingerprint=fp,
        segments=tuple(segments),
        notes=tuple(notes),
    )


def build_comparison_regime_scorecard_or_unavailable(
    comparison: Mapping[str, Any],
    *,
    run_id: str,
) -> ARVPRegimeScorecard:
    """Build a comparison-aware regime scorecard when input supports it.

    Current comparison artifact (shadow_comparison.json) is aggregate-only.
    This function accepts an optional caller-supplied field:
      comparison["regime_segments"] = list[{ regime_id, observation_count, signal_count, ... }]

    If absent, returns status=unavailable (explicitly).
    """
    c = _require_mapping(comparison, "comparison")
    _require_non_empty_string(run_id, "run_id")
    raw_segments = c.get("regime_segments")
    notes: list[str] = []
    if raw_segments is None:
        notes.append("unavailable: comparison input has no regime_segments")
        fp = canonical_hash(
            {
                "run_id": run_id,
                "schema_version": _SCHEMA_VERSION,
                "source": "comparison",
                "status": _STATUS_UNAVAILABLE,
                "notes": notes,
            }
        )
        return ARVPRegimeScorecard(
            schema_version=_SCHEMA_VERSION,
            status=_STATUS_UNAVAILABLE,
            run_id=run_id,
            source="comparison",
            scorecard_fingerprint=fp,
            segments=tuple(),
            notes=tuple(notes),
        )

    if not isinstance(raw_segments, list):
        raise ARVPRegimeScorecardError("comparison.regime_segments must be a list")

    segments: list[RegimeSegmentScore] = []
    for idx, raw in enumerate(raw_segments):
        seg = _require_mapping(raw, f"regime_segments[{idx}]")
        regime = _require_non_empty_string(seg.get("regime_id"), f"regime_segments[{idx}].regime_id").upper()
        observation_count = _require_int(
            seg.get("observation_count"), f"regime_segments[{idx}].observation_count"
        )
        signal_count = _require_int(
            seg.get("signal_count"), f"regime_segments[{idx}].signal_count"
        )
        trade_close_count = _require_int(
            seg.get("trade_close_count"), f"regime_segments[{idx}].trade_close_count"
        )
        pnl_sum_r = _optional_decimal(seg.get("pnl_sum_r"), f"regime_segments[{idx}].pnl_sum_r")
        segments.append(
            RegimeSegmentScore(
                regime_id=regime,
                observation_count=observation_count,
                signal_count=signal_count,
                trade_close_count=trade_close_count,
                pnl_sum_r=pnl_sum_r,
            )
        )

    segments.sort(key=lambda s: s.regime_id)
    fp = canonical_hash(
        {
            "run_id": run_id,
            "schema_version": _SCHEMA_VERSION,
            "segments": [s.to_dict() for s in segments],
            "notes": notes,
            "source": "comparison",
            "status": _STATUS_OK,
        }
    )
    return ARVPRegimeScorecard(
        schema_version=_SCHEMA_VERSION,
        status=_STATUS_OK,
        run_id=run_id,
        source="comparison",
        scorecard_fingerprint=fp,
        segments=tuple(segments),
        notes=tuple(notes),
    )


def write_regime_scorecard_bundle(
    *,
    scorecard: ARVPRegimeScorecard,
    output_dir: pathlib.Path,
) -> tuple[pathlib.Path, pathlib.Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / _FILENAME_JSON
    md_path = output_dir / _FILENAME_MD
    try:
        json_path.write_text(canonical_json_dumps(scorecard.to_dict()), encoding="utf-8")
        md_path.write_text(build_scorecard_summary(scorecard), encoding="utf-8")
    except OSError as exc:
        raise ARVPRegimeScorecardError(
            f"Failed to write regime scorecard bundle to {output_dir}: {exc}"
        ) from exc
    return json_path, md_path

