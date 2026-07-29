"""ARVP replay-vs-paper comparison: parse canonical inputs, write comparison artifacts.

Scope (#1902): glue layer that consumes:
  - replay-side artifact: replay_report.v1 (report.json)
  - paper-side artifact: arvp_paper_reference_window.v1 (paper_reference_window.json)

and produces:
  - shadow_comparison.json (machine-readable)
  - shadow_comparison_summary.md (operator-facing)

Design rules:
  - Deterministic: same inputs produce identical outputs.
  - Explicit: reject_count is only derived from explicit reject data. A separate
    inferred_unfilled_count is computed as max(0, order_count - fill_count) as an
    informational proxy and is NOT treated as reject evidence.
  - Fail-closed: invalid or missing inputs result in status=unusable and a non-zero
    exit code at the CLI layer.
  - No DB access, no live data access, no calibration logic, no regime analytics.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from core.replay.canonical_json import canonical_json_dumps
from core.replay.execution_economics_v1 import (
    MOCK_PAPER_ECONOMICS_ASSUMPTIONS,
    compare_economics_components,
    reconcile_gross_to_net,
)
from core.replay.shadow_compare import (
    PaperReferenceWindow,
    ReplayOutputWindow,
    ShadowCompareError,
    ShadowComparisonResult,
    build_comparison_summary,
    compare_windows_or_unusable,
    write_shadow_comparison_artifact,
)


class ReplayVsPaperCompareError(ValueError):
    """Raised when inputs cannot be parsed into comparison-grade windows."""


def _require_mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReplayVsPaperCompareError(f"{name} must be a JSON object")
    return value


def _require_non_empty_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReplayVsPaperCompareError(f"{name} must be a non-empty string")
    return value


def _require_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ReplayVsPaperCompareError(f"{name} must be an int")
    return value


def _ts_ms_to_utc_iso(ts_ms: int) -> str:
    dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
    return dt.isoformat()


def _infer_reject_count(order_count: int, fill_count: int) -> int:
    # Informational proxy only: orders without fills.
    return max(0, int(order_count) - int(fill_count))


def _safe_int(value: object, name: str) -> int:
    if value is None:
        raise ReplayVsPaperCompareError(f"{name} is required")
    try:
        iv = int(value)
    except (TypeError, ValueError) as exc:
        raise ReplayVsPaperCompareError(f"{name} must be int-like: {exc}") from exc
    if iv < 0:
        raise ReplayVsPaperCompareError(f"{name} must be >= 0")
    return iv


@dataclass(frozen=True, slots=True)
class ComparePaths:
    replay_report_json: pathlib.Path
    paper_reference_json: pathlib.Path


def load_replay_output_window(replay_report: Mapping[str, Any]) -> ReplayOutputWindow:
    """Parse replay_report.v1 dict into ReplayOutputWindow (comparison-grade)."""
    report = _require_mapping(replay_report, "replay_report")
    schema_version = report.get("schema_version")
    if schema_version != "replay_report.v1":
        raise ReplayVsPaperCompareError(
            f"replay_report.schema_version must be 'replay_report.v1', got {schema_version!r}"
        )

    run_spec = _require_mapping(report.get("run_spec"), "replay_report.run_spec")
    run_id = _require_non_empty_string(
        run_spec.get("replay_run_id"), "run_spec.replay_run_id"
    )
    symbol = _require_non_empty_string(run_spec.get("symbol"), "run_spec.symbol")
    strategy_id = _require_non_empty_string(
        run_spec.get("strategy_id"), "run_spec.strategy_id"
    )

    dataset_summary = _require_mapping(
        report.get("dataset_summary"), "replay_report.dataset_summary"
    )
    start_ts_ms = _safe_int(
        dataset_summary.get("period_start_ts_ms"), "dataset_summary.period_start_ts_ms"
    )
    end_ts_ms = _safe_int(
        dataset_summary.get("period_end_ts_ms"), "dataset_summary.period_end_ts_ms"
    )

    metrics = _require_mapping(report.get("metrics"), "replay_report.metrics")
    signal_count = _safe_int(metrics.get("signals_total"), "metrics.signals_total")
    buy = _safe_int(metrics.get("buy_signals_total"), "metrics.buy_signals_total")
    sell = _safe_int(metrics.get("sell_signals_total"), "metrics.sell_signals_total")
    fill_count = _safe_int(
        metrics.get("closed_trades_total"), "metrics.closed_trades_total"
    )
    order_count = buy + sell
    inferred_unfilled_count = _infer_reject_count(order_count, fill_count)

    metadata = run_spec.get("metadata") or {}
    metadata = _require_mapping(metadata, "run_spec.metadata")
    dataset_fingerprint = _require_non_empty_string(
        metadata.get("dataset_fingerprint"), "run_spec.metadata.dataset_fingerprint"
    )

    return ReplayOutputWindow(
        run_id=run_id,
        symbol=symbol,
        strategy_id=strategy_id,
        window_start_utc=_ts_ms_to_utc_iso(start_ts_ms),
        window_end_utc=_ts_ms_to_utc_iso(end_ts_ms),
        signal_count=signal_count,
        order_count=order_count,
        fill_count=fill_count,
        actual_reject_count=None,
        inferred_unfilled_count=inferred_unfilled_count,
        dataset_fingerprint=dataset_fingerprint,
    )


def _paper_provenance_id(paper: Mapping[str, Any]) -> str:
    extracted_by = paper.get("extracted_by")
    extracted_at_utc = paper.get("extracted_at_utc")
    if (
        isinstance(extracted_by, str)
        and extracted_by.strip()
        and isinstance(extracted_at_utc, str)
        and extracted_at_utc.strip()
    ):
        return f"{extracted_by.strip()}@{extracted_at_utc.strip()}"
    # Fall back to a deterministic placeholder if provenance fields are missing.
    return "paper_reference_window.v1"


def load_paper_reference_window(
    paper_reference: Mapping[str, Any],
) -> PaperReferenceWindow:
    """Parse arvp_paper_reference_window.v1 dict into PaperReferenceWindow.

    Counts are derived from the supplied event set:
      - signal_count: number of SIGNAL events in the main events list
      - causal_signal_count: number of SIGNAL events in causal_context_events
      - order_count: number of ORDER events with paper_ order_id
      - fill_count:  number of FILL events with paper_ order_id
      - reject_count: max(0, order_count - fill_count)
    """
    paper = _require_mapping(paper_reference, "paper_reference_window")
    contract_version = paper.get("contract_version")
    if contract_version != "arvp_paper_reference_window.v1":
        raise ReplayVsPaperCompareError(
            f"paper_reference_window.contract_version must be "
            f"'arvp_paper_reference_window.v1', got {contract_version!r}"
        )

    strategy_id = _require_non_empty_string(paper.get("strategy_id"), "strategy_id")
    symbol = _require_non_empty_string(paper.get("symbol"), "symbol")
    start_ts_ms = _require_int(paper.get("start_ts_ms_utc"), "start_ts_ms_utc")
    end_ts_ms = _require_int(paper.get("end_ts_ms_utc"), "end_ts_ms_utc")
    if end_ts_ms <= start_ts_ms:
        raise ReplayVsPaperCompareError("end_ts_ms_utc must be > start_ts_ms_utc")

    events = paper.get("events")
    if not isinstance(events, list) or not events:
        raise ReplayVsPaperCompareError("events must be a non-empty list")

    signal_count = 0
    order_count = 0
    fill_count = 0
    actual_reject_count = 0
    saw_explicit_rejects = False
    for idx, raw in enumerate(events):
        ev = _require_mapping(raw, f"events[{idx}]")
        ev_type = _require_non_empty_string(
            ev.get("event_type"), f"events[{idx}].event_type"
        )
        ev_symbol = _require_non_empty_string(ev.get("symbol"), f"events[{idx}].symbol")
        if ev_symbol != symbol:
            raise ReplayVsPaperCompareError(
                f"events[{idx}].symbol must match window symbol {symbol!r}, got {ev_symbol!r}"
            )
        ts_ms = _require_int(ev.get("timestamp_ms"), f"events[{idx}].timestamp_ms")
        payload = _require_mapping(ev.get("payload"), f"events[{idx}].payload")
        payload_strategy = _require_non_empty_string(
            payload.get("strategy_id"), f"events[{idx}].payload.strategy_id"
        )
        if payload_strategy != strategy_id:
            raise ReplayVsPaperCompareError(
                f"events[{idx}].payload.strategy_id must match window strategy_id {strategy_id!r}, got {payload_strategy!r}"
            )
        if ts_ms < start_ts_ms or ts_ms > end_ts_ms:
            raise ReplayVsPaperCompareError(
                f"events[{idx}].timestamp_ms must be within window [{start_ts_ms}, {end_ts_ms}]"
            )

        if ev_type == "SIGNAL":
            signal_count += 1
        elif ev_type == "ORDER":
            order_id = ev.get("order_id")
            if isinstance(order_id, str) and order_id.startswith("paper_"):
                order_count += 1
            # Explicit reject fields: only count if present (no inference).
            if ev.get("rejected") is True or ev.get("order_status") == "REJECTED":
                saw_explicit_rejects = True
                actual_reject_count += 1
        elif ev_type == "FILL":
            order_id = ev.get("order_id")
            if isinstance(order_id, str) and order_id.startswith("paper_"):
                fill_count += 1
        elif ev_type == "REJECT":
            order_id = ev.get("order_id")
            if isinstance(order_id, str) and order_id.startswith("paper_"):
                saw_explicit_rejects = True
                actual_reject_count += 1
        elif ev_type == "DECISION":
            # Included for completeness; no direct count KPI for #1902.
            pass
        else:
            raise ReplayVsPaperCompareError(
                f"Unknown event_type {ev_type!r} in events[{idx}]"
            )

    # --- Causal context events (#3058) ---
    causal_signal_count = 0
    causal_events_raw = paper.get("causal_context_events")
    if isinstance(causal_events_raw, list):
        for idx, raw in enumerate(causal_events_raw):
            cev = _require_mapping(raw, f"causal_context_events[{idx}]")
            cev_type = _require_non_empty_string(
                cev.get("event_type"), f"causal_context_events[{idx}].event_type"
            )
            if cev_type != "SIGNAL":
                raise ReplayVsPaperCompareError(
                    f"causal_context_events[{idx}] event_type must be SIGNAL, got {cev_type!r}"
                )
            causal_signal_count += 1

    inferred_unfilled_count = _infer_reject_count(order_count, fill_count)
    actual_reject_count_or_none = actual_reject_count if saw_explicit_rejects else None
    provenance_id = _paper_provenance_id(paper)

    return PaperReferenceWindow(
        symbol=symbol,
        strategy_id=strategy_id,
        window_start_utc=_ts_ms_to_utc_iso(start_ts_ms),
        window_end_utc=_ts_ms_to_utc_iso(end_ts_ms),
        signal_count=signal_count,
        order_count=order_count,
        fill_count=fill_count,
        actual_reject_count=actual_reject_count_or_none,
        inferred_unfilled_count=inferred_unfilled_count,
        provenance_id=provenance_id,
        causal_signal_count=causal_signal_count,
    )


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ReplayVsPaperCompareError(f"Failed to read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ReplayVsPaperCompareError(f"Invalid JSON in {path}: {exc}") from exc


def compare_from_paths(paths: ComparePaths) -> ShadowComparisonResult:
    replay_dict = load_json(paths.replay_report_json)
    paper_dict = load_json(paths.paper_reference_json)
    replay = load_replay_output_window(replay_dict)
    paper = load_paper_reference_window(paper_dict)
    try:
        return compare_windows_or_unusable(replay, paper)
    except ShadowCompareError as exc:
        # Defensive: compare_windows_or_unusable should not raise.
        raise ReplayVsPaperCompareError(
            f"Comparison failed unexpectedly: {exc}"
        ) from exc


def economics_payload_from_metrics(metrics: Mapping[str, Any]) -> dict[str, Any]:
    """Build a gross-to-net payload from replay/paper metrics mapping.

    Missing components are marked not_applicable / inactive rather than invented.
    When ``slippage_cost_quote`` is present, ``gross_pnl_quote`` is treated as
    fill-price-embedded and reference gross is reconstructed as embedded+slippage.
    """
    metrics_map = _require_mapping(metrics, "metrics")
    embedded = metrics_map.get("gross_pnl_quote", metrics_map.get("gross_pnl", 0))
    fees = metrics_map.get("fees_total_quote", metrics_map.get("total_fee_cost", 0))
    maker = metrics_map.get(
        "maker_fee_cost_quote", metrics_map.get("maker_fee_cost", 0)
    )
    taker = metrics_map.get("taker_fee_cost_quote", metrics_map.get("taker_fee_cost"))
    if taker is None:
        taker = fees
    slippage = metrics_map.get("slippage_cost_quote", metrics_map.get("slippage_cost"))
    if slippage is not None:
        slippage_status = "active"
        reference_gross = float(embedded or 0) + float(slippage)
    else:
        slippage_status = "not_applicable"
        reference_gross = float(embedded or 0)
    return reconcile_gross_to_net(
        gross_pnl=reference_gross,
        maker_fee_cost=maker if maker is not None else 0,
        taker_fee_cost=taker if taker is not None else 0,
        slippage_cost=0 if slippage is None else slippage,
        slippage_status=slippage_status,
        fill_price_embedded_gross=embedded,
    ).to_dict()


def compare_economics_from_reports(
    replay_report: Mapping[str, Any],
    paper_economics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Component-wise economics diff for replay-vs-paper research comparison.

    ``paper_economics`` may be a gross-to-net payload or a flat metrics map.
    When omitted, paper side is treated as mock defaults (fees/spread inactive).
    """
    report = _require_mapping(replay_report, "replay_report")
    metrics = _require_mapping(report.get("metrics"), "replay_report.metrics")
    replay_econ = economics_payload_from_metrics(metrics)
    if paper_economics is None:
        paper_econ = reconcile_gross_to_net(
            gross_pnl=0,
            taker_fee_cost=0,
            slippage_cost=0,
            slippage_status="not_applicable",
            reject_impact=0,
            reject_status="active",
            latency_or_delay_impact=0,
            latency_status="active",
            limitations=(
                "Paper economics omitted; mock defaults documented only.",
                "MockExecutor has no fee/spread model; reject/latency are seeded.",
            ),
        ).to_dict()
        paper_econ["mock_paper_assumptions"] = dict(MOCK_PAPER_ECONOMICS_ASSUMPTIONS)
    elif "components" in paper_economics:
        paper_econ = dict(paper_economics)
    else:
        paper_econ = economics_payload_from_metrics(paper_economics)
    return compare_economics_components(replay_econ, paper_econ)


def write_comparison_bundle(
    *,
    result: ShadowComparisonResult,
    output_dir: pathlib.Path,
    economics_component_diff: Mapping[str, Any] | None = None,
) -> tuple[pathlib.Path, pathlib.Path]:
    """Write comparison JSON + summary MD into output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    write_shadow_comparison_artifact(result, output_dir)
    summary = build_comparison_summary(result)
    md_path = output_dir / "shadow_comparison_summary.md"
    md_path.write_text(summary, encoding="utf-8")
    if economics_component_diff is not None:
        econ_path = output_dir / "economics_component_diff.json"
        econ_path.write_text(
            canonical_json_dumps(dict(economics_component_diff)), encoding="utf-8"
        )
    return output_dir / "shadow_comparison.json", md_path
