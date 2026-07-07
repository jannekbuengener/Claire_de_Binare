"""Shared helpers for ARVP window qualification contract tests (#3827)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from core.replay.arvp_regime_scorecards import build_replay_regime_scorecard_from_trace
from core.replay.dataset_provider import DatasetLoadError, FileBackedDatasetProvider
from core.replay.dataset_spec import DatasetSpec
from core.replay.paper_reference_window_export import (
    PaperReferenceExportError,
    build_export_request,
    export_paper_reference_window,
)
from core.replay.scheduler import ReplayScheduler, SchedulerConfig, SchedulerError

_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "arvp"
    / "window_qualification"
    / "cases_v1.json"
)

QualificationVerdict = Literal["PASS", "WARN", "BLOCKED"]


@dataclass(frozen=True)
class WindowQualificationResult:
    verdict: QualificationVerdict
    limitations: tuple[str, ...]
    cadence_ok: bool
    warmup_live_ok: bool
    regime_available: bool
    paper_reference_available: bool
    promotes: bool


def load_window_qualification_cases() -> list[dict[str, Any]]:
    payload = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError("window qualification fixture must contain cases list")
    return cases


def _write_candles(tmp_path: Path, candles: list[dict[str, Any]]) -> Path:
    path = tmp_path / "candles.json"
    path.write_text(json.dumps(candles), encoding="utf-8")
    return path


def _paper_rows(*, complete: bool, start_ts_ms: int, end_ts_ms: int) -> list[dict[str, Any]]:
    mid_ts = start_ts_ms + ((end_ts_ms - start_ts_ms) // 2)
    base_signal = {
        "event_pk": "sig-1",
        "correlation_id": "corr-1",
        "signal_id": "signal-1",
        "decision_id": None,
        "order_id": None,
        "fill_id": None,
        "event_type": "SIGNAL",
        "symbol": "BTCUSDT",
        "timestamp_ms": start_ts_ms,
        "payload": {
            "strategy_id": "primary_breakout_v1",
            "bot_id": "bot-a",
            "metadata": {"bot_id": "bot-a", "config_hash": "cfg-a"},
        },
    }
    if not complete:
        return [base_signal]
    return [
        base_signal,
        {
            "event_pk": "dec-1",
            "correlation_id": "corr-1",
            "signal_id": "signal-1",
            "decision_id": "decision-1",
            "order_id": None,
            "fill_id": None,
            "event_type": "DECISION",
            "symbol": "BTCUSDT",
            "timestamp_ms": mid_ts,
            "payload": {"strategy_id": "primary_breakout_v1"},
        },
        {
            "event_pk": "ord-1",
            "correlation_id": "corr-1",
            "signal_id": "signal-1",
            "decision_id": "decision-1",
            "order_id": "paper_order-1",
            "fill_id": None,
            "event_type": "ORDER",
            "symbol": "BTCUSDT",
            "timestamp_ms": mid_ts,
            "payload": {"strategy_id": "primary_breakout_v1"},
        },
        {
            "event_pk": "fill-1",
            "correlation_id": "corr-1",
            "signal_id": "signal-1",
            "decision_id": "decision-1",
            "order_id": "paper_order-1",
            "fill_id": "fill-1",
            "event_type": "FILL",
            "symbol": "BTCUSDT",
            "timestamp_ms": end_ts_ms,
            "payload": {"strategy_id": "primary_breakout_v1"},
        },
    ]


def _paper_rows_from_ref(
    ref: str | None, *, start_ts_ms: int, end_ts_ms: int
) -> list[dict[str, Any]] | None:
    if ref is None:
        return None
    if ref == "complete_chain_paper_order":
        return _paper_rows(complete=True, start_ts_ms=start_ts_ms, end_ts_ms=end_ts_ms)
    if ref == "signal_only":
        return _paper_rows(complete=False, start_ts_ms=start_ts_ms, end_ts_ms=end_ts_ms)
    raise ValueError(f"unknown paper event ref: {ref}")


def qualify_arvp_window_case(
    case: dict[str, Any], tmp_path: Path
) -> WindowQualificationResult:
    """Evaluate one fixture case across dataset, scheduler, regime, and paper surfaces."""
    limitations: list[str] = []
    cadence_ok = False
    warmup_live_ok = False
    regime_available = False
    paper_reference_available = False

    candles = case["candles"]
    warmup_candles = int(case["warmup_candles"])
    if warmup_candles >= len(candles):
        limitations.append(
            f"Insufficient candles: {len(candles)} total, {warmup_candles} warmup required"
        )
        return WindowQualificationResult(
            verdict="BLOCKED",
            limitations=tuple(limitations),
            cadence_ok=False,
            warmup_live_ok=False,
            regime_available=False,
            paper_reference_available=False,
            promotes=False,
        )

    candle_path = _write_candles(tmp_path, candles)
    start_ts_ms = int(candles[warmup_candles]["ts_ms"])
    end_ts_ms = int(candles[-1]["ts_ms"])

    try:
        spec = DatasetSpec(
            source="file",
            file_path=str(candle_path),
            symbol="BTCUSDT",
            timeframe="1m",
            start_ts_ms=start_ts_ms,
            end_ts_ms=end_ts_ms,
            warmup_candles=warmup_candles,
        )
        dataset = FileBackedDatasetProvider().load(spec)
        cadence_ok = True
        scheduler = ReplayScheduler().schedule(
            dataset, SchedulerConfig(profile="instant")
        )
        warmup_live_ok = scheduler.live_candle_count > 0 and scheduler.warmup_count == warmup_candles
    except (DatasetLoadError, SchedulerError) as exc:
        limitations.append(str(exc))
        return WindowQualificationResult(
            verdict="BLOCKED",
            limitations=tuple(limitations),
            cadence_ok=cadence_ok,
            warmup_live_ok=warmup_live_ok,
            regime_available=False,
            paper_reference_available=False,
            promotes=False,
        )

    regime_trace = case.get("regime_trace")
    if isinstance(regime_trace, dict):
        scorecard = build_replay_regime_scorecard_from_trace(regime_trace)
        regime_available = scorecard.status == "ok"
        if not regime_available:
            limitations.extend(scorecard.notes or ["regime segments unavailable"])
    else:
        limitations.append("regime trace missing")

    paper_rows = _paper_rows_from_ref(
        case.get("paper_events"), start_ts_ms=start_ts_ms, end_ts_ms=end_ts_ms
    )
    if paper_rows is not None:
        request = build_export_request(
            strategy_id="primary_breakout_v1",
            symbol="BTCUSDT",
            start_ts_ms_utc=start_ts_ms,
            end_ts_ms_utc=end_ts_ms,
            extracted_by="window-qualification-contract",
            extracted_at_utc="2026-07-07T00:00:00+00:00",
            source_query_intent="contract-test",
        )
        try:
            export_paper_reference_window(
                request=request,
                rows=paper_rows,
            )
            paper_reference_available = True
        except PaperReferenceExportError as exc:
            limitations.append(str(exc))
    else:
        limitations.append("paper reference events missing")

    if not cadence_ok or not warmup_live_ok:
        verdict: QualificationVerdict = "BLOCKED"
    elif not regime_available or not paper_reference_available:
        verdict = "WARN"
    else:
        verdict = "PASS"

    promotes = verdict == "PASS" and not limitations
    return WindowQualificationResult(
        verdict=verdict,
        limitations=tuple(limitations),
        cadence_ok=cadence_ok,
        warmup_live_ok=warmup_live_ok,
        regime_available=regime_available,
        paper_reference_available=paper_reference_available,
        promotes=promotes,
    )
