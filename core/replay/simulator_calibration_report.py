"""ARVP simulator calibration report (#1903).

Consumes:
  - replay-vs-paper comparison artifact: shadow_comparison.json (from #1902)

Produces:
  - simulator_calibration_report.json (machine-readable)
  - simulator_calibration_summary.md  (operator-facing)

Design rules:
  - Deterministic: same comparison input -> identical report + fingerprint.
  - Explicit: when explicit reject deltas are unavailable, any inference is
    labeled as proxy-only and must not be treated as reject evidence.
  - Fail-closed: invalid/missing comparison inputs produce status=unusable.
  - Reporting only: no simulator mutation, no auto-tuning, no governance policy.

Drift classification (explicitly grounded in comparison output):
  - If comparison.status != "aligned": classification = "unusable".
  - Otherwise:
      - Primary (explicit) signal: fill_rate_delta (if present)
          > 0  -> optimistic (replay looks better than paper)
          < 0  -> pessimistic
          == 0 -> neutral (no direction)
      - Secondary (proxy-only) signals (when fill_rate_delta missing):
          - inferred_unfilled_count_delta:
              < 0 -> optimistic (fewer unfilled orders than paper)
              > 0 -> pessimistic
          - fill_count_delta:
              > 0 -> optimistic (more fills than paper)
              < 0 -> pessimistic

    If both optimistic and pessimistic signals are present -> "ambiguous".
    If only optimistic signals -> "optimistic".
    If only pessimistic signals -> "pessimistic".
    If no directional signals -> "ambiguous" (insufficient evidence).
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from core.replay.canonical_json import canonical_hash, canonical_json_dumps
from core.replay.shadow_compare import ShadowCompareError, ShadowComparisonResult

_SCHEMA_VERSION = "simulator_calibration_report.v1"
_REPORT_FILENAME = "simulator_calibration_report.json"
_SUMMARY_FILENAME = "simulator_calibration_summary.md"

_STATUS_ALIGNED = "aligned"
_STATUS_UNUSABLE = "unusable"

_DRIFT_OPTIMISTIC = "optimistic"
_DRIFT_PESSIMISTIC = "pessimistic"
_DRIFT_AMBIGUOUS = "ambiguous"
_DRIFT_UNUSABLE = "unusable"

_EVIDENCE_EXPLICIT = "explicit"
_EVIDENCE_PROXY = "proxy"


class SimulatorCalibrationError(ValueError):
    """Raised when calibration inputs cannot be parsed or persisted."""


def _require_mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SimulatorCalibrationError(f"{name} must be a JSON object")
    return value


def _require_non_empty_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SimulatorCalibrationError(f"{name} must be a non-empty string")
    return value


def _require_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise SimulatorCalibrationError(f"{name} must be an int")
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
            raise SimulatorCalibrationError(f"{name} must be a Decimal string: {exc}") from exc
    raise SimulatorCalibrationError(f"{name} must be a string or null")


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SimulatorCalibrationError(f"Failed to read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SimulatorCalibrationError(f"Invalid JSON in {path}: {exc}") from exc


def load_shadow_comparison_artifact(payload: Mapping[str, Any]) -> ShadowComparisonResult:
    """Parse shadow_comparison.json dict into ShadowComparisonResult."""
    data = _require_mapping(payload, "shadow_comparison")

    status = _require_non_empty_string(data.get("status"), "status")
    if status not in (_STATUS_ALIGNED, _STATUS_UNUSABLE):
        raise SimulatorCalibrationError(f"status must be 'aligned' or 'unusable', got {status!r}")

    # Minimal required fields for calibration.
    fp = _require_non_empty_string(data.get("comparison_fingerprint"), "comparison_fingerprint")
    replay_run_id = _require_non_empty_string(data.get("replay_run_id"), "replay_run_id")
    paper_prov = _require_non_empty_string(data.get("paper_provenance_id"), "paper_provenance_id")
    symbol = _require_non_empty_string(data.get("symbol"), "symbol")
    strategy_id = _require_non_empty_string(data.get("strategy_id"), "strategy_id")

    signal_delta = _require_int(data.get("signal_count_delta"), "signal_count_delta")
    order_delta = _require_int(data.get("order_count_delta"), "order_count_delta")
    fill_delta = _require_int(data.get("fill_count_delta"), "fill_count_delta")
    unfilled_delta = _require_int(
        data.get("inferred_unfilled_count_delta"), "inferred_unfilled_count_delta"
    )

    # Optional explicit-reject fields.
    reject_delta = data.get("actual_reject_count_delta")
    if reject_delta is not None:
        reject_delta = _require_int(reject_delta, "actual_reject_count_delta")

    fill_rate_replay = _optional_decimal(data.get("fill_rate_replay"), "fill_rate_replay")
    fill_rate_paper = _optional_decimal(data.get("fill_rate_paper"), "fill_rate_paper")
    fill_rate_delta = _optional_decimal(data.get("fill_rate_delta"), "fill_rate_delta")

    alignment_issue = data.get("alignment_issue")
    if alignment_issue is not None:
        alignment_issue = _require_non_empty_string(alignment_issue, "alignment_issue")

    window_start_r = _require_non_empty_string(
        data.get("window_start_utc_replay"), "window_start_utc_replay"
    )
    window_end_r = _require_non_empty_string(
        data.get("window_end_utc_replay"), "window_end_utc_replay"
    )
    window_start_p = _require_non_empty_string(
        data.get("window_start_utc_paper"), "window_start_utc_paper"
    )
    window_end_p = _require_non_empty_string(
        data.get("window_end_utc_paper"), "window_end_utc_paper"
    )

    return ShadowComparisonResult(
        comparison_fingerprint=fp,
        status=status,
        alignment_issue=alignment_issue,
        replay_run_id=replay_run_id,
        paper_provenance_id=paper_prov,
        symbol=symbol,
        strategy_id=strategy_id,
        signal_count_delta=signal_delta,
        order_count_delta=order_delta,
        fill_count_delta=fill_delta,
        inferred_unfilled_count_delta=unfilled_delta,
        actual_reject_count_delta=reject_delta,
        fill_rate_replay=fill_rate_replay,
        fill_rate_paper=fill_rate_paper,
        fill_rate_delta=fill_rate_delta,
        window_start_utc_replay=window_start_r,
        window_end_utc_replay=window_end_r,
        window_start_utc_paper=window_start_p,
        window_end_utc_paper=window_end_p,
    )


@dataclass(frozen=True, slots=True)
class CalibrationSignal:
    name: str
    direction: str  # optimistic | pessimistic | neutral
    evidence_level: str  # explicit | proxy
    value: str
    note: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "direction": self.direction,
            "evidence_level": self.evidence_level,
            "name": self.name,
            "note": self.note,
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class SimulatorCalibrationReport:
    schema_version: str
    calibration_fingerprint: str
    status: str  # aligned | unusable (mirrors comparison usability)
    drift_classification: str  # optimistic | pessimistic | ambiguous | unusable
    comparison_fingerprint: str
    replay_run_id: str
    paper_provenance_id: str
    symbol: str
    strategy_id: str
    signals: tuple[CalibrationSignal, ...]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "calibration_fingerprint": self.calibration_fingerprint,
            "comparison_fingerprint": self.comparison_fingerprint,
            "drift_classification": self.drift_classification,
            "notes": list(self.notes),
            "paper_provenance_id": self.paper_provenance_id,
            "replay_run_id": self.replay_run_id,
            "schema_version": self.schema_version,
            "signals": [s.to_dict() for s in self.signals],
            "status": self.status,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
        }


def _direction_from_decimal(delta: Decimal) -> str:
    if delta > 0:
        return _DRIFT_OPTIMISTIC
    if delta < 0:
        return _DRIFT_PESSIMISTIC
    return "neutral"


def _direction_from_int(delta: int, *, optimistic_when_positive: bool) -> str:
    if delta == 0:
        return "neutral"
    if optimistic_when_positive:
        return _DRIFT_OPTIMISTIC if delta > 0 else _DRIFT_PESSIMISTIC
    return _DRIFT_OPTIMISTIC if delta < 0 else _DRIFT_PESSIMISTIC


def build_simulator_calibration_report(
    comparison: ShadowComparisonResult,
) -> SimulatorCalibrationReport:
    if comparison.status != _STATUS_ALIGNED:
        notes = []
        if comparison.alignment_issue:
            notes.append(f"unusable_input: {comparison.alignment_issue}")
        else:
            notes.append("unusable_input: comparison status != aligned")
        base = {
            "comparison": comparison.to_dict(),
            "rules_version": _SCHEMA_VERSION,
        }
        calib_fp = canonical_hash(base)
        return SimulatorCalibrationReport(
            schema_version=_SCHEMA_VERSION,
            calibration_fingerprint=calib_fp,
            status=_STATUS_UNUSABLE,
            drift_classification=_DRIFT_UNUSABLE,
            comparison_fingerprint=comparison.comparison_fingerprint,
            replay_run_id=comparison.replay_run_id,
            paper_provenance_id=comparison.paper_provenance_id,
            symbol=comparison.symbol,
            strategy_id=comparison.strategy_id,
            signals=tuple(),
            notes=tuple(notes),
        )

    signals: list[CalibrationSignal] = []
    notes: list[str] = []

    if comparison.fill_rate_delta is not None:
        direction = _direction_from_decimal(comparison.fill_rate_delta)
        signals.append(
            CalibrationSignal(
                name="fill_rate_delta",
                direction=direction,
                evidence_level=_EVIDENCE_EXPLICIT,
                value=str(comparison.fill_rate_delta),
                note="explicit rejects only; absent when explicit reject data missing",
            )
        )
    else:
        notes.append("explicit_rejects_unavailable: fill_rate_delta not present")
        signals.append(
            CalibrationSignal(
                name="inferred_unfilled_count_delta",
                direction=_direction_from_int(
                    comparison.inferred_unfilled_count_delta, optimistic_when_positive=False
                ),
                evidence_level=_EVIDENCE_PROXY,
                value=str(comparison.inferred_unfilled_count_delta),
                note="proxy only; derived from orders - fills, not explicit reject evidence",
            )
        )
        signals.append(
            CalibrationSignal(
                name="fill_count_delta",
                direction=_direction_from_int(comparison.fill_count_delta, optimistic_when_positive=True),
                evidence_level=_EVIDENCE_PROXY,
                value=str(comparison.fill_count_delta),
                note="proxy only; fill counts may mask reject reasons without explicit reject data",
            )
        )

    saw_opt = any(s.direction == _DRIFT_OPTIMISTIC for s in signals)
    saw_pess = any(s.direction == _DRIFT_PESSIMISTIC for s in signals)
    if comparison.fill_rate_delta is not None and signals[0].direction == "neutral":
        # Explicitly handle the "no direction" case.
        drift = _DRIFT_AMBIGUOUS
        notes.append("no_directional_signal: fill_rate_delta == 0")
    elif saw_opt and saw_pess:
        drift = _DRIFT_AMBIGUOUS
        notes.append("mixed_signals: optimistic and pessimistic indicators present")
    elif saw_opt:
        drift = _DRIFT_OPTIMISTIC
    elif saw_pess:
        drift = _DRIFT_PESSIMISTIC
    else:
        drift = _DRIFT_AMBIGUOUS
        notes.append("insufficient_signal: no optimistic/pessimistic indicators")

    calib_fp = canonical_hash(
        {
            "comparison_fingerprint": comparison.comparison_fingerprint,
            "drift_classification": drift,
            "notes": notes,
            "rules_version": _SCHEMA_VERSION,
            "signals": [s.to_dict() for s in signals],
        }
    )

    return SimulatorCalibrationReport(
        schema_version=_SCHEMA_VERSION,
        calibration_fingerprint=calib_fp,
        status=_STATUS_ALIGNED,
        drift_classification=drift,
        comparison_fingerprint=comparison.comparison_fingerprint,
        replay_run_id=comparison.replay_run_id,
        paper_provenance_id=comparison.paper_provenance_id,
        symbol=comparison.symbol,
        strategy_id=comparison.strategy_id,
        signals=tuple(signals),
        notes=tuple(notes),
    )


def build_calibration_summary(report: SimulatorCalibrationReport) -> str:
    """Operator-facing summary strictly grounded in report fields."""
    lines = [
        "# Simulator Calibration Summary",
        "",
        f"Status:          {report.status}",
        f"Drift:           {report.drift_classification}",
        f"Replay run:      {report.replay_run_id}",
        f"Paper reference: {report.paper_provenance_id}",
        f"Symbol:          {report.symbol}",
        f"Strategy:        {report.strategy_id}",
        f"Fingerprint:     {report.calibration_fingerprint}",
        f"Source compare:  {report.comparison_fingerprint}",
        "",
        "## Signals",
    ]
    if not report.signals:
        lines += ["(none)"]
    else:
        for s in report.signals:
            level = "explicit" if s.evidence_level == _EVIDENCE_EXPLICIT else "proxy"
            lines.append(f"- {s.name}: {s.direction} ({level}), value={s.value}")
            if s.note:
                lines.append(f"  note: {s.note}")
    if report.notes:
        lines += ["", "## Notes"]
        lines += [f"- {n}" for n in report.notes]
    return "\n".join(lines) + "\n"


def write_calibration_bundle(
    *,
    report: SimulatorCalibrationReport,
    output_dir: pathlib.Path,
) -> tuple[pathlib.Path, pathlib.Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / _REPORT_FILENAME
    md_path = output_dir / _SUMMARY_FILENAME
    try:
        json_path.write_text(canonical_json_dumps(report.to_dict()), encoding="utf-8")
        md_path.write_text(build_calibration_summary(report), encoding="utf-8")
    except OSError as exc:
        raise ShadowCompareError(
            f"Failed to write calibration bundle to {output_dir}: {exc}"
        ) from exc
    return json_path, md_path

