"""Assemble ARVP strategy metrics into profitability_evidence_packet.v1 bundles (#4016).

Aggregates normalized ``arvp_strategy_metrics.v1`` records per candidate
(strategy_id + parameter fingerprint) into deterministic, schema-valid PEP
packets with embedded split/window/scenario evidence slices.

Safety: LR NO-GO, ranking_ready=false, historical_cross_venue_research only.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema.validators import validator_for

from core.replay.canonical_json import canonical_hash, canonical_json_dumps

from services.validation.profitability_evidence_packet_assembler import (
    _deterministic_json_dumps,
    _sha256_hex,
    _slugify_for_packet_id,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = PROJECT_ROOT / "docs" / "contracts"
_PACKET_SCHEMA_PATH = CONTRACTS_DIR / "profitability_evidence_packet.v1.schema.json"
_METRICS_SCHEMA_PATH = CONTRACTS_DIR / "arvp_strategy_metrics.v1.schema.json"

SOURCE_CONTRACT = "arvp_strategy_metrics.v1"
EVIDENCE_CLASS = "historical_cross_venue_research"
SOURCE_VENUE = "Binance Spot BTCUSDT"
LR_STATUS = "NO-GO"
BOARD_STAGE = "trade-capable"
BOARD_STAGE_NOTE = (
    "Board stage trade-capable is orthogonal to LR NO-GO and authorizes no live capital."
)

SCENARIOS = ("baseline", "pessimistic_execution", "feed_gap")
PURPOSE_ORDER = ("development", "validation", "out_of_sample", "stress")
WINDOW_CLASS_ORDER = ("monthly", "quarterly", "yearly", "stress_v2", "stress", "unknown")

RANKABILITY_RANKABLE = "RANKABLE_FOR_CROSS_VENUE_COMPARISON"
RANKABILITY_NOT = "NOT_RANKABLE"
RANKABILITY_PARTIAL = "PARTIAL_EVIDENCE"

_DEFAULT_GENERATED_AT = "2026-07-12T11:19:44Z"
_PARAMETER_FINGERPRINT_DEFAULT = "campaign_default_v1"

_LIMITATIONS_BASE = (
    "Binance historical cross-venue research only; not MEXC same-venue confirmation.",
    "ranking_ready=false; no paper/live/promotion authorization.",
    "Overlapping calendar windows are descriptive only, not independent samples.",
    "Quote PnL across overlapping windows is never summed into total return.",
    "LR remains NO-GO.",
)


class ArvpCandidateEvidenceAssemblerError(ValueError):
    """Fail-closed ARVP candidate evidence assembly violation."""


@dataclass(frozen=True, slots=True)
class CandidateAssemblyResult:
    packets: list[dict[str, Any]]
    bundle_hash: str
    packet_count: int
    source_record_count: int
    candidates: tuple[str, ...]


def _load_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_packet(packet: dict[str, Any]) -> None:
    schema = _load_schema(_PACKET_SCHEMA_PATH)
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(packet), key=lambda err: str(err.message))
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.path) or "<root>"
        raise ArvpCandidateEvidenceAssemblerError(
            f"PEP schema mismatch at {path}: {first.message}"
        )


def _validate_metrics_bundle(bundle: Mapping[str, Any]) -> None:
    schema = _load_schema(_METRICS_SCHEMA_PATH)
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(dict(bundle)), key=lambda err: str(err.message))
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.path) or "<root>"
        raise ArvpCandidateEvidenceAssemblerError(
            f"Metrics bundle schema mismatch at {path}: {first.message}"
        )


def _as_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            return None
        return number
    if isinstance(value, str):
        token = value.strip().lower()
        if token in {"infinity", "-infinity"}:
            return None
        try:
            number = float(token)
        except ValueError:
            return None
        return number if math.isfinite(number) else None
    return None


def _as_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _median(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return float(statistics.median(values))


def _quantile(values: Sequence[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    index = (len(ordered) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return float(ordered[lower])
    weight = index - lower
    return float(ordered[lower] * (1 - weight) + ordered[upper] * weight)


def _stable_statistics(values: Sequence[float | None]) -> dict[str, Any]:
    numeric = [value for value in values if value is not None]
    traded = len(numeric)
    if traded == 0:
        return {
            "count_total_windows": 0,
            "count_traded_windows": 0,
            "count_zero_trade_windows": 0,
            "median": None,
            "minimum": None,
            "maximum": None,
            "lower_quantile": None,
            "upper_quantile": None,
            "positive_window_share": None,
            "negative_window_share": None,
        }

    positive = sum(1 for value in numeric if value > 0)
    negative = sum(1 for value in numeric if value < 0)
    return {
        "count_total_windows": traded,
        "count_traded_windows": traded,
        "count_zero_trade_windows": 0,
        "median": _median(numeric),
        "minimum": min(numeric),
        "maximum": max(numeric),
        "lower_quantile": _quantile(numeric, 0.25),
        "upper_quantile": _quantile(numeric, 0.75),
        "positive_window_share": positive / traded,
        "negative_window_share": negative / traded,
    }


def _safe_delta(
    baseline: float | None,
    other: float | None,
    *,
    relative: bool = False,
) -> dict[str, Any]:
    if baseline is None or other is None:
        return {
            "absolute_delta": None,
            "relative_delta": None,
            "delta_reason": "missing_operand",
        }
    absolute = other - baseline
    if not relative:
        return {
            "absolute_delta": absolute,
            "relative_delta": None,
            "delta_reason": None,
        }
    if baseline == 0:
        return {
            "absolute_delta": absolute,
            "relative_delta": None,
            "delta_reason": "zero_baseline_denominator",
        }
    return {
        "absolute_delta": absolute,
        "relative_delta": absolute / abs(baseline),
        "delta_reason": None,
    }


def _normalize_purpose(raw: object) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return "unknown"
    token = raw.strip().lower()
    if token in {"development", "dev"}:
        return "development"
    if token in {"validation", "val"}:
        return "validation"
    if token in {"out_of_sample", "oos"}:
        return "out_of_sample"
    if token == "stress":
        return "stress"
    return token


def _normalize_window_class(raw: object) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return "unknown"
    token = raw.strip().lower()
    if token in {"month", "monthly"}:
        return "monthly"
    if token in {"quarter", "quarterly"}:
        return "quarterly"
    if token in {"year", "yearly"}:
        return "yearly"
    if token in {"stress_v2", "stress-v2"}:
        return "stress_v2"
    return token


def _candidate_id(strategy_id: str) -> str:
    slug = _slugify_for_packet_id(strategy_id)[:48]
    return f"cand-{slug}-binance-3990"


def _packet_id(candidate_id: str, source_content_hash: str) -> str:
    slug = _slugify_for_packet_id(candidate_id.removeprefix("cand-"))[:48]
    digest = _sha256_hex(
        _deterministic_json_dumps(
            {"candidate_id": candidate_id, "source_content_hash": source_content_hash}
        ).encode("utf-8")
    )[:12]
    return f"pep-{slug}-{digest}"


def _parameter_fingerprint(strategy_id: str) -> tuple[str, list[str]]:
    # Campaign records carry strategy_id only; no per-job parameter vector.
    return (
        f"{strategy_id}:{_PARAMETER_FINGERPRINT_DEFAULT}",
        [
            "parameter_fingerprint derived from strategy_id campaign default; "
            "no independent parameter vector in arvp_strategy_metrics.v1 records."
        ],
    )


def _group_records_by_candidate(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        strategy_id = str(record.get("strategy_id") or "")
        if not strategy_id:
            raise ArvpCandidateEvidenceAssemblerError("record.strategy_id is required")
        grouped.setdefault(strategy_id, []).append(dict(record))
    for strategy_records in grouped.values():
        strategy_records.sort(
            key=lambda item: (
                str(item.get("job_id") or ""),
                str(item.get("scenario") or ""),
            )
        )
    return grouped


def _dedupe_flags(records: Sequence[Mapping[str, Any]]) -> list[str]:
    flags: list[str] = []
    seen: set[str] = set()
    for record in records:
        raw_flags = record.get("data_quality_flags")
        if not isinstance(raw_flags, list):
            continue
        for flag in raw_flags:
            if isinstance(flag, str) and flag and flag not in seen:
                seen.add(flag)
                flags.append(flag)
    return sorted(flags)


def _slice_rankability(record: Mapping[str, Any]) -> str:
    if record.get("rankable") is True:
        return RANKABILITY_RANKABLE
    trades = _as_int(record.get("closed_trades_total"))
    if trades == 0:
        return RANKABILITY_NOT
    return RANKABILITY_PARTIAL


def _economic_summary(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "job_id": record.get("job_id"),
        "window_id": record.get("window_id"),
        "purpose": _normalize_purpose(record.get("purpose")),
        "window_class": _normalize_window_class(record.get("window_class")),
        "scenario": record.get("scenario"),
        "net_pnl_quote": _as_float(record.get("net_pnl_quote")),
        "fees_total_quote": _as_float(record.get("fees_total_quote")),
        "profit_factor": record.get("profit_factor"),
        "expectancy_r": _as_float(record.get("expectancy_r")),
        "max_drawdown_r": _as_float(record.get("max_drawdown_r")),
        "fee_adjusted_max_drawdown_r": record.get("fee_adjusted_max_drawdown_r"),
        "closed_trades_total": _as_int(record.get("closed_trades_total")),
        "win_rate": _as_float(record.get("win_rate")),
        "rankable": bool(record.get("rankable")),
        "not_rankable_reasons": list(record.get("not_rankable_reasons") or []),
        "slippage_availability": record.get("slippage_availability"),
        "regime_availability": record.get("regime_availability"),
    }


def _records_by_job_scenario(
    records: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        job_id = str(record.get("job_id") or "")
        scenario = str(record.get("scenario") or "")
        index[(job_id, scenario)] = dict(record)
    return index


def _scenario_sensitivity(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_job: dict[str, dict[str, Mapping[str, Any]]] = {}
    for record in records:
        job_id = str(record.get("job_id") or "")
        scenario = str(record.get("scenario") or "")
        by_job.setdefault(job_id, {})[scenario] = record

    results: list[dict[str, Any]] = []
    for job_id in sorted(by_job):
        scenarios = by_job[job_id]
        baseline = scenarios.get("baseline")
        if baseline is None:
            continue
        base_net = _as_float(baseline.get("net_pnl_quote"))
        base_fees = _as_float(baseline.get("fees_total_quote"))
        base_dd = _as_float(baseline.get("max_drawdown_r"))

        pessimistic = scenarios.get("pessimistic_execution")
        feed_gap = scenarios.get("feed_gap")

        pessimistic_net = (
            _as_float(pessimistic.get("net_pnl_quote")) if pessimistic else None
        )
        feed_gap_net = _as_float(feed_gap.get("net_pnl_quote")) if feed_gap else None
        pessimistic_fees = (
            _as_float(pessimistic.get("fees_total_quote")) if pessimistic else None
        )
        feed_gap_fees = (
            _as_float(feed_gap.get("fees_total_quote")) if feed_gap else None
        )
        pessimistic_dd = (
            _as_float(pessimistic.get("max_drawdown_r")) if pessimistic else None
        )
        feed_gap_dd = _as_float(feed_gap.get("max_drawdown_r")) if feed_gap else None

        results.append(
            {
                "job_id": job_id,
                "window_id": baseline.get("window_id"),
                "purpose": _normalize_purpose(baseline.get("purpose")),
                "window_class": _normalize_window_class(baseline.get("window_class")),
                "baseline_net_pnl_quote": base_net,
                "cost_sensitivity": {
                    "pessimistic_execution": {
                        "net_pnl_quote_delta": _safe_delta(base_net, pessimistic_net),
                        "fees_total_quote_delta": _safe_delta(base_fees, pessimistic_fees),
                        "max_drawdown_r_delta": _safe_delta(base_dd, pessimistic_dd),
                    }
                },
                "gap_sensitivity": {
                    "feed_gap": {
                        "net_pnl_quote_delta": _safe_delta(base_net, feed_gap_net),
                        "fees_total_quote_delta": _safe_delta(base_fees, feed_gap_fees),
                        "max_drawdown_r_delta": _safe_delta(base_dd, feed_gap_dd),
                    }
                },
            }
        )
    return results


def _split_stability(
    records: Sequence[Mapping[str, Any]],
    *,
    scenario: str,
) -> list[dict[str, Any]]:
    scenario_records = [
        record for record in records if str(record.get("scenario") or "") == scenario
    ]
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for record in scenario_records:
        key = (
            _normalize_purpose(record.get("purpose")),
            _normalize_window_class(record.get("window_class")),
        )
        grouped.setdefault(key, []).append(record)

    stability: list[dict[str, Any]] = []
    for purpose in PURPOSE_ORDER:
        for window_class in WINDOW_CLASS_ORDER:
            key = (purpose, window_class)
            bucket = grouped.get(key)
            if not bucket:
                continue
            net_values = [_as_float(item.get("net_pnl_quote")) for item in bucket]
            trade_values = [_as_int(item.get("closed_trades_total")) for item in bucket]
            zero_trade = sum(1 for trades in trade_values if trades == 0)
            stability.append(
                {
                    "purpose": purpose,
                    "window_class": window_class,
                    "scenario": scenario,
                    "overlap_policy": "descriptive_non_iid",
                    "net_pnl_quote": _stable_statistics(net_values),
                    "closed_trades_total": _stable_statistics(
                        [float(v) for v in trade_values if v is not None]
                    ),
                    "count_zero_trade_windows": zero_trade,
                }
            )
    return stability


def _assess_candidate_rankability(records: Sequence[Mapping[str, Any]]) -> tuple[str, list[str]]:
    baseline_records = [
        record for record in records if str(record.get("scenario") or "") == "baseline"
    ]
    if not baseline_records:
        return RANKABILITY_NOT, ["missing_baseline_records"]

    rankable_count = sum(1 for record in baseline_records if record.get("rankable") is True)
    zero_trade = sum(
        1
        for record in baseline_records
        if _as_int(record.get("closed_trades_total")) == 0
    )
    reasons: list[str] = []
    if rankable_count == 0:
        reasons.append("no_rankable_baseline_windows")
        return RANKABILITY_NOT, reasons
    if zero_trade > 0:
        reasons.append(f"zero_trade_baseline_windows={zero_trade}")
    if rankable_count < len(baseline_records):
        reasons.append("partial_missing_required_metrics")
        return RANKABILITY_PARTIAL, reasons
    return RANKABILITY_RANKABLE, reasons


def _hashable_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    excluded = {"generated_at", "content_hash"}
    return {key: value for key, value in packet.items() if key not in excluded}


def _packet_content_hash(packet: Mapping[str, Any]) -> str:
    return canonical_hash(_hashable_packet(packet))


def _top_level_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    baseline = [
        record for record in records if str(record.get("scenario") or "") == "baseline"
    ]
    net_values = [_as_float(record.get("net_pnl_quote")) for record in baseline]
    gross_values = [_as_float(record.get("gross_pnl_quote")) for record in baseline]
    fee_values = [_as_float(record.get("fees_total_quote")) for record in baseline]
    pf_values = [
        value
        for record in baseline
        if (value := _as_float(record.get("profit_factor"))) is not None
    ]
    expectancy_values = [
        value
        for record in baseline
        if (value := _as_float(record.get("expectancy_r"))) is not None
    ]
    win_values = [
        value
        for record in baseline
        if (value := _as_float(record.get("win_rate"))) is not None
    ]
    dd_values = [
        value
        for record in baseline
        if (value := _as_float(record.get("max_drawdown_r"))) is not None
    ]
    trade_total = sum(
        trades
        for record in baseline
        if (trades := _as_int(record.get("closed_trades_total"))) is not None
    )

    return {
        "gross_return": _median([v for v in gross_values if v is not None]) or 0.0,
        "net_return": _median([v for v in net_values if v is not None]) or 0.0,
        "fees": _median([v for v in fee_values if v is not None]) or 0.0,
        "spread_cost": 0.0,
        "slippage_cost": 0.0,
        "profit_factor": _median(pf_values),
        "expectancy": _median(expectancy_values) or 0.0,
        "win_rate": _median(win_values) or 0.0,
        "avg_win": None,
        "avg_loss": None,
        "max_drawdown": max(dd_values) if dd_values else None,
        "loss_streak": 0,
        "trade_count": trade_total,
    }


def _scenario_results(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    baseline_stats = _stable_statistics(
        [
            _as_float(record.get("net_pnl_quote"))
            for record in records
            if str(record.get("scenario") or "") == "baseline"
        ]
    )
    pessimistic_stats = _stable_statistics(
        [
            _as_float(record.get("net_pnl_quote"))
            for record in records
            if str(record.get("scenario") or "") == "pessimistic_execution"
        ]
    )
    feed_gap_stats = _stable_statistics(
        [
            _as_float(record.get("net_pnl_quote"))
            for record in records
            if str(record.get("scenario") or "") == "feed_gap"
        ]
    )
    dd_baseline = [
        value
        for record in records
        if str(record.get("scenario") or "") == "baseline"
        and (value := _as_float(record.get("max_drawdown_r"))) is not None
    ]
    dd_pessimistic = [
        value
        for record in records
        if str(record.get("scenario") or "") == "pessimistic_execution"
        and (value := _as_float(record.get("max_drawdown_r"))) is not None
    ]
    dd_feed_gap = [
        value
        for record in records
        if str(record.get("scenario") or "") == "feed_gap"
        and (value := _as_float(record.get("max_drawdown_r"))) is not None
    ]

    return [
        {
            "scenario_id": "baseline",
            "status": "PASS",
            "net_return": baseline_stats["median"],
            "max_drawdown": max(dd_baseline) if dd_baseline else None,
            "notes": "Campaign baseline descriptive median net_pnl_quote; not summed across overlapping windows.",
        },
        {
            "scenario_id": "pessimistic_execution",
            "status": "WARNING",
            "net_return": pessimistic_stats["median"],
            "max_drawdown": max(dd_pessimistic) if dd_pessimistic else None,
            "notes": "Cost sensitivity scenario; median net_pnl_quote vs baseline per job in arvp_evidence.scenario_sensitivity.",
        },
        {
            "scenario_id": "feed_gap",
            "status": "WARNING",
            "net_return": feed_gap_stats["median"],
            "max_drawdown": max(dd_feed_gap) if dd_feed_gap else None,
            "notes": "Feed-gap sensitivity scenario; median net_pnl_quote vs baseline per job in arvp_evidence.scenario_sensitivity.",
        },
    ]


def build_candidate_evidence_packet(
    *,
    strategy_id: str,
    records: Sequence[Mapping[str, Any]],
    campaign_id: str,
    source_content_hash: str,
    source_record_count: int,
    generated_at: str = _DEFAULT_GENERATED_AT,
) -> dict[str, Any]:
    if not records:
        raise ArvpCandidateEvidenceAssemblerError(
            f"no records for strategy_id={strategy_id}"
        )

    candidate_id = _candidate_id(strategy_id)
    parameter_fingerprint, fingerprint_limitations = _parameter_fingerprint(strategy_id)
    rankability_status, rankability_reasons = _assess_candidate_rankability(records)
    summary = _top_level_summary(records)
    purposes = sorted(
        {_normalize_purpose(record.get("purpose")) for record in records},
        key=lambda item: PURPOSE_ORDER.index(item)
        if item in PURPOSE_ORDER
        else len(PURPOSE_ORDER),
    )
    window_classes = sorted(
        {_normalize_window_class(record.get("window_class")) for record in records},
        key=lambda item: WINDOW_CLASS_ORDER.index(item)
        if item in WINDOW_CLASS_ORDER
        else len(WINDOW_CLASS_ORDER),
    )

    limitations = list(_LIMITATIONS_BASE)
    limitations.extend(fingerprint_limitations)
    if rankability_status != RANKABILITY_RANKABLE:
        limitations.append(
            f"rankability_status={rankability_status}; not a promotion-ready candidate."
        )
    limitations.append(
        "Top-level gross_return/net_return are descriptive medians of per-window quote PnL, not additive total return."
    )
    limitations.append(
        "Regime fields describe window-level regime_availability only, not strategy regime performance."
    )

    packet: dict[str, Any] = {
        "schema_version": "profitability_evidence_packet.v1",
        "evidence_packet_id": _packet_id(candidate_id, source_content_hash),
        "candidate_id": candidate_id,
        "strategy_id": strategy_id,
        "parameter_fingerprint": parameter_fingerprint,
        "campaign_id": campaign_id,
        "generated_at": generated_at,
        "dataset_id": campaign_id,
        "dataset_fingerprint": f"sha256:{source_content_hash}",
        "source_contract": SOURCE_CONTRACT,
        "source_content_hash": source_content_hash,
        "source_record_count": source_record_count,
        "source_venue": SOURCE_VENUE,
        "evidence_class": EVIDENCE_CLASS,
        "lr_status": LR_STATUS,
        "board_stage": BOARD_STAGE,
        "board_stage_note": BOARD_STAGE_NOTE,
        "source_run_refs": [
            f"arvp_strategy_metrics.v1:{source_content_hash}",
            f"campaign_id:{campaign_id}",
        ],
        "source_artifact_references": [
            {
                "artifact_role": "arvp_strategy_metrics_bundle",
                "schema_ref": "docs/contracts/arvp_strategy_metrics.v1.schema.json",
                "content_hash": source_content_hash,
                "record_count": source_record_count,
            }
        ],
        "gross_return": summary["gross_return"],
        "net_return": summary["net_return"],
        "fees": summary["fees"],
        "spread_cost": summary["spread_cost"],
        "slippage_cost": summary["slippage_cost"],
        "profit_factor": summary["profit_factor"],
        "expectancy": summary["expectancy"],
        "win_rate": summary["win_rate"],
        "avg_win": summary["avg_win"],
        "avg_loss": summary["avg_loss"],
        "max_drawdown": summary["max_drawdown"],
        "loss_streak": summary["loss_streak"],
        "trade_count": summary["trade_count"],
        "regime_scorecard": {
            "status": "unavailable",
            "artifact_ref": None,
            "summary": (
                "Window-level regime_availability only; no strategy regime scorecard measured."
            ),
        },
        "scenario_results": _scenario_results(records),
        "replay_vs_paper_status": "not_run",
        "simulator_drift": "not_assessed",
        "risk_blocks": 0,
        "kill_switch_events": 0,
        "recommendation": "NO_RECOMMENDATION",
        "ranking_ready": False,
        "rankability_status": rankability_status,
        "rankability_reasons": rankability_reasons,
        "paper_reference_status": "not_run",
        "same_venue_status": "not_run",
        "data_quality_flags": _dedupe_flags(records),
        "limitations": limitations,
        "safety_boundaries": [
            "LR remains NO-GO.",
            "Board stage trade-capable is not Live-Go.",
            "Evidence packets are research-only and do not authorize paper or live execution.",
            "No automatic candidate promotion is authorized.",
            "Binance historical research does not confirm MEXC same-venue behavior.",
        ],
        "missing_evidence": [
            {
                "artifact_role": "replay_vs_paper_compare",
                "classification": "OPTIONAL_NOT_PROVIDED",
                "summary": "Paper reference not run for Binance cross-venue research campaign.",
            },
            {
                "artifact_role": "regime_scorecard",
                "classification": "UNAVAILABLE_FROM_INPUT",
                "summary": "Only regime_availability flags per window; no regime scorecard artifact.",
            },
        ],
        "coverage_readiness": {
            "coverage_report_ready": False,
            "ranking_inputs_complete": False,
            "data_quality_ready": True,
            "economics_ready": False,
            "scenario_ready": True,
            "replay_ready": False,
            "replay_vs_paper_ready": False,
            "regime_scorecard_ready": False,
            "harvester_refs_ready": True,
            "summary": (
                "ARVP cross-venue research packet; ranking_inputs_complete=false; "
                "ranking_ready=false by policy."
            ),
        },
        "arvp_coverage": {
            "purpose_splits": purposes,
            "window_classes": window_classes,
            "scenario_coverage": list(SCENARIOS),
            "sample_counts": {
                "scenario_records": len(records),
                "unique_jobs": len({record.get("job_id") for record in records}),
            },
            "trade_counts": {
                "baseline_closed_trades_total": sum(
                    trades
                    for record in records
                    if str(record.get("scenario") or "") == "baseline"
                    and (trades := _as_int(record.get("closed_trades_total"))) is not None
                ),
                "zero_trade_baseline_windows": sum(
                    1
                    for record in records
                    if str(record.get("scenario") or "") == "baseline"
                    and _as_int(record.get("closed_trades_total")) == 0
                ),
            },
        },
        "arvp_evidence": {
            "economic_metric_summaries": [
                _economic_summary(record) for record in sorted(records, key=lambda item: (
                    str(item.get("job_id") or ""),
                    str(item.get("scenario") or ""),
                ))
            ],
            "scenario_sensitivity": _scenario_sensitivity(records),
            "split_stability": _split_stability(records, scenario="baseline"),
            "cost_evidence": {
                "fees_total_quote": _stable_statistics(
                    [
                        _as_float(record.get("fees_total_quote"))
                        for record in records
                        if str(record.get("scenario") or "") == "baseline"
                    ]
                ),
                "slippage_availability": "not_available",
            },
            "stress_evidence": {
                "stress_windows": [
                    {
                        "job_id": record.get("job_id"),
                        "window_id": record.get("window_id"),
                        "scenario": record.get("scenario"),
                        "net_pnl_quote": _as_float(record.get("net_pnl_quote")),
                        "max_drawdown_r": _as_float(record.get("max_drawdown_r")),
                        "closed_trades_total": _as_int(record.get("closed_trades_total")),
                    }
                    for record in records
                    if _normalize_purpose(record.get("purpose")) == "stress"
                    or _normalize_window_class(record.get("window_class"))
                    in {"stress_v2", "stress"}
                ],
            },
        },
        "parent_issue": "#4013",
        "child_issue": "#4016",
    }
    packet["content_hash"] = _packet_content_hash(packet)
    _validate_packet(packet)
    return packet


def assemble_arvp_candidate_evidence(
    metrics_bundle: Mapping[str, Any],
    *,
    generated_at: str = _DEFAULT_GENERATED_AT,
) -> CandidateAssemblyResult:
    _validate_metrics_bundle(metrics_bundle)

    records_raw = metrics_bundle.get("records")
    if not isinstance(records_raw, list) or not records_raw:
        raise ArvpCandidateEvidenceAssemblerError("metrics bundle records must be non-empty")

    campaign_id = str(metrics_bundle.get("campaign_id") or "")
    source_content_hash = str(metrics_bundle.get("content_hash") or "")
    if not campaign_id or not source_content_hash:
        raise ArvpCandidateEvidenceAssemblerError(
            "metrics bundle campaign_id and content_hash are required"
        )

    source_record_count = int(metrics_bundle.get("record_count") or len(records_raw))
    if source_record_count != len(records_raw):
        raise ArvpCandidateEvidenceAssemblerError(
            "metrics bundle record_count must match records length"
        )

    grouped = _group_records_by_candidate(records_raw)
    packets: list[dict[str, Any]] = []
    for strategy_id in sorted(grouped):
        packet = build_candidate_evidence_packet(
            strategy_id=strategy_id,
            records=grouped[strategy_id],
            campaign_id=campaign_id,
            source_content_hash=source_content_hash,
            source_record_count=source_record_count,
            generated_at=generated_at,
        )
        packets.append(packet)

    bundle_hash = canonical_hash(
        [
            {
                "candidate_id": packet["candidate_id"],
                "content_hash": packet["content_hash"],
            }
            for packet in packets
        ]
    )

    return CandidateAssemblyResult(
        packets=packets,
        bundle_hash=bundle_hash,
        packet_count=len(packets),
        source_record_count=source_record_count,
        candidates=tuple(sorted(grouped)),
    )


def assemble_from_metrics_bundle_path(
    bundle_path: Path,
    *,
    generated_at: str = _DEFAULT_GENERATED_AT,
) -> CandidateAssemblyResult:
    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ArvpCandidateEvidenceAssemblerError("metrics bundle must be a JSON object")
    return assemble_arvp_candidate_evidence(payload, generated_at=generated_at)


def write_assembly_outputs(
    result: CandidateAssemblyResult,
    *,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "arvp_candidate_evidence_bundle.v1",
        "packet_count": result.packet_count,
        "bundle_hash": result.bundle_hash,
        "source_record_count": result.source_record_count,
        "candidates": list(result.candidates),
        "packets": [
            {
                "candidate_id": packet["candidate_id"],
                "evidence_packet_id": packet["evidence_packet_id"],
                "strategy_id": packet["strategy_id"],
                "content_hash": packet["content_hash"],
                "path": f"{packet['strategy_id']}.pep.json",
            }
            for packet in result.packets
        ],
    }
    manifest_path = output_dir / "bundle_manifest.json"
    manifest_path.write_text(canonical_json_dumps(manifest) + "\n", encoding="utf-8")

    for packet in result.packets:
        packet_path = output_dir / f"{packet['strategy_id']}.pep.json"
        packet_path.write_text(canonical_json_dumps(packet) + "\n", encoding="utf-8")

    return manifest
