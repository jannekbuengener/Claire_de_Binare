"""Deterministic ARVP strategy metric extraction (#4015).

Reads canonical vacation queue jobs and emits normalized ``arvp_strategy_metrics.v1``
records with stable ordering and content hashing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from core.replay.canonical_json import canonical_hash, canonical_json_dumps

from .candle_rankability import (
    FLAG_WARMUP_TRIM_APPLIED,
    legacy_resolve_candles_total,
    resolve_candle_rankability,
)
from .metric_contract import (
    CANONICAL_JOB_COUNT,
    CANONICAL_SELECTOR,
    QUEUE_RECORD_COUNT,
    SUPERSEDED_JOB_COUNT,
    is_rankable_job_metrics,
    metric_is_missing,
    select_canonical_jobs,
)

SCHEMA_VERSION = "arvp_strategy_metrics.v1"
EVIDENCE_CLASS = "historical_cross_venue_research"
VENUE = "binance"
ALLOWED_SCENARIOS = frozenset({"baseline", "pessimistic_execution", "feed_gap"})

REQUIRED_METRIC_FIELDS = (
    "gross_pnl_quote",
    "net_pnl_quote",
    "fees_total_quote",
    "max_drawdown_r",
    "profit_factor",
    "expectancy_r",
    "closed_trades_total",
    "win_rate",
)

OPTIONAL_METRIC_FIELDS = (
    "fee_adjusted_max_drawdown_r",
    "fee_adjusted_profit_factor",
    "fee_adjusted_expectancy_r",
    "avg_win_r",
    "avg_loss_r",
    "candles_total",
)

PROFIT_FACTOR_INFINITY_TOKEN = "infinity"
PROFIT_FACTOR_NEGATIVE_INFINITY_TOKEN = "-infinity"


class StrategyMetricExtractionError(ValueError):
    """Fail-closed extraction violation."""


@dataclass(frozen=True, slots=True)
class ExtractionSummary:
    queue_record_count: int
    canonical_job_count: int
    excluded_superseded_job_count: int
    record_count: int
    content_hash: str


def _repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise StrategyMetricExtractionError(f"JSON root must be object: {path}")
    return payload


def _load_dataset_spec(spec_path: str | None, repo_root: Path) -> dict[str, Any]:
    if not spec_path:
        return {}
    candidate = Path(spec_path)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    if not candidate.is_file():
        return {}
    payload = _load_json(candidate)
    return payload


def _window_class_from_spec(spec: Mapping[str, Any], dataset_id: str) -> str:
    overlap = spec.get("overlap_class")
    if isinstance(overlap, str) and overlap.strip():
        return overlap.strip()
    if "_stress" in dataset_id or dataset_id.endswith("_v2"):
        return "stress"
    return "unknown"


def _purpose_from_spec(spec: Mapping[str, Any]) -> str | None:
    purpose = spec.get("purpose")
    if isinstance(purpose, str) and purpose.strip():
        return purpose.strip()
    return None


def _window_id_from_spec(spec: Mapping[str, Any], dataset_id: str) -> str:
    for key in ("window_id", "dataset_id"):
        value = spec.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return dataset_id


def _normalize_numeric(value: Any, *, field: str) -> Any:
    if value is None:
        return None
    if field in {"profit_factor", "fee_adjusted_profit_factor"}:
        if isinstance(value, str):
            token = value.strip().lower()
            if token == PROFIT_FACTOR_INFINITY_TOKEN:
                return PROFIT_FACTOR_INFINITY_TOKEN
            if token == PROFIT_FACTOR_NEGATIVE_INFINITY_TOKEN:
                return PROFIT_FACTOR_NEGATIVE_INFINITY_TOKEN
        if isinstance(value, (int, float)):
            if math.isinf(value):
                return (
                    PROFIT_FACTOR_INFINITY_TOKEN
                    if value > 0
                    else PROFIT_FACTOR_NEGATIVE_INFINITY_TOKEN
                )
            if math.isnan(value):
                raise StrategyMetricExtractionError(
                    f"non-finite value for {field}: NaN"
                )
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise StrategyMetricExtractionError(
                f"non-finite value for {field}: {value!r}"
            )
    if field == "closed_trades_total":
        return int(value)
    if field == "candles_total":
        return int(value)
    if isinstance(value, bool):
        raise StrategyMetricExtractionError(f"unexpected bool for {field}")
    if isinstance(value, (int, float)):
        return value
    raise StrategyMetricExtractionError(
        f"unsupported numeric type for {field}: {type(value).__name__}"
    )


def _resolve_metric_value(
    metrics: Mapping[str, Any],
    field: str,
) -> Any:
    if metric_is_missing(metrics, field):
        return None
    return _normalize_numeric(metrics[field], field=field)


def resolve_candles_total(
    dataset_summary: Mapping[str, Any],
) -> tuple[int | None, list[str]]:
    """Deprecated pre-#4065 helper; retained for audit comparison tests only."""
    return legacy_resolve_candles_total(dataset_summary)


def _scenario_payload_sha256(payload: Mapping[str, Any]) -> str:
    material = canonical_json_dumps(dict(payload)).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _slippage_availability(metrics: Mapping[str, Any]) -> str:
    availability = metrics.get("metrics_availability")
    if isinstance(availability, dict):
        if availability.get("slippage_per_trade_available") is True:
            return "available"
        if availability.get("slippage_per_trade_available") is False:
            return "not_available"
    return "not_available"


def _regime_availability(dataset_spec: Mapping[str, Any]) -> str:
    regime = dataset_spec.get("regime_distribution")
    if isinstance(regime, dict) and regime:
        return "available"
    return "not_available"


def _exposure_availability(
    metrics: Mapping[str, Any],
    candles_total: int | None,
) -> str:
    if candles_total is None:
        return "not_available"
    if "signals_total" not in metrics:
        return "not_available"
    return "partial"


def _rankability_assessment(
    metrics: Mapping[str, Any],
    *,
    data_quality_flags: Sequence[str],
    rankability_blocking_flags: Sequence[str],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if "closed_trades_total" not in metrics:
        reasons.append("missing_closed_trades_total")
        return False, reasons
    if not is_rankable_job_metrics(metrics):
        reasons.append("zero_closed_trades_total")
        return False, reasons
    for field in REQUIRED_METRIC_FIELDS:
        if field == "closed_trades_total":
            continue
        if metric_is_missing(metrics, field):
            reasons.append(f"missing_{field}")
    for flag in rankability_blocking_flags:
        reasons.append(flag)
    for flag in data_quality_flags:
        if flag.startswith("missing_"):
            reasons.append(flag)
    if reasons:
        return False, sorted(set(reasons))
    return True, []


def extract_scenario_record(
    *,
    campaign_id: str,
    job: Mapping[str, Any],
    scenario_id: str,
    repo_root: Path,
    campaign_source_sha: str | None = None,
) -> dict[str, Any]:
    if scenario_id not in ALLOWED_SCENARIOS:
        raise StrategyMetricExtractionError(f"unsupported scenario_id: {scenario_id}")

    scenario_metrics = job.get("scenario_metrics")
    if not isinstance(scenario_metrics, dict):
        raise StrategyMetricExtractionError(
            f"{job.get('job_id')}: missing scenario_metrics"
        )
    payload = scenario_metrics.get(scenario_id)
    if not isinstance(payload, dict):
        raise StrategyMetricExtractionError(
            f"{job.get('job_id')}: missing scenario payload for {scenario_id}"
        )

    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        raise StrategyMetricExtractionError(
            f"{job.get('job_id')}: missing metrics for {scenario_id}"
        )

    dataset_id = str(job.get("dataset_id") or "")
    dataset_spec = _load_dataset_spec(job.get("spec_path"), repo_root)
    dataset_summary = payload.get("dataset_summary")
    if not isinstance(dataset_summary, dict):
        dataset_summary = {}

    parameter_fingerprint = str(job.get("fingerprint") or "") or None
    candle = resolve_candle_rankability(
        dataset_summary=dataset_summary,
        strategy_id=str(job.get("strategy_id") or ""),
        campaign_id=campaign_id,
        parameter_fingerprint=parameter_fingerprint,
        campaign_source_sha=campaign_source_sha,
        repo_root=repo_root,
    )
    data_quality_flags = list(candle.data_quality_flags)

    rankable, not_rankable_reasons = _rankability_assessment(
        metrics,
        data_quality_flags=data_quality_flags,
        rankability_blocking_flags=candle.rankability_blocking_flags,
    )

    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "campaign_id": campaign_id,
        "job_id": str(job.get("job_id") or ""),
        "strategy_id": str(job.get("strategy_id") or ""),
        "window_id": _window_id_from_spec(dataset_spec, dataset_id),
        "window_class": _window_class_from_spec(dataset_spec, dataset_id),
        "purpose": _purpose_from_spec(dataset_spec),
        "scenario": scenario_id,
        "source_artifact": f"queue_state.scenario_metrics.{scenario_id}",
        "source_artifact_sha256": _scenario_payload_sha256(payload),
        "evidence_class": EVIDENCE_CLASS,
        "venue": VENUE,
        "canonical_job": True,
        "slippage_availability": _slippage_availability(metrics),
        "regime_availability": _regime_availability(dataset_spec),
        "exposure_availability": _exposure_availability(
            metrics, candle.candles_evaluated
        ),
        "rankable": rankable,
        "not_rankable_reasons": not_rankable_reasons,
        "data_quality_flags": sorted(set(data_quality_flags)),
        "rankability_blocking_flags": list(candle.rankability_blocking_flags),
    }

    for field in REQUIRED_METRIC_FIELDS + OPTIONAL_METRIC_FIELDS:
        if field == "candles_total":
            record[field] = candle.candles_total
            continue
        record[field] = _resolve_metric_value(metrics, field)

    record["candles_input_total"] = candle.candles_input_total
    record["warmup_bars"] = candle.warmup_bars
    record["candles_evaluated"] = candle.candles_evaluated
    record["warmup_provenance"] = candle.warmup_provenance
    if FLAG_WARMUP_TRIM_APPLIED in data_quality_flags:
        record["warmup_trim_applied"] = True

    regime_stats = payload.get("regime_stats")
    if isinstance(regime_stats, dict):
        record["regime_stats"] = regime_stats

    return record


def _record_sort_key(record: Mapping[str, Any]) -> tuple[str, str]:
    return (str(record.get("job_id") or ""), str(record.get("scenario") or ""))


def extract_campaign_metrics(
    queue_state: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> tuple[list[dict[str, Any]], ExtractionSummary]:
    root = repo_root or Path(__file__).resolve().parents[2]
    campaign_id = str(queue_state.get("campaign_id") or "")
    if not campaign_id:
        raise StrategyMetricExtractionError("queue_state.campaign_id is required")
    campaign_source_sha = queue_state.get("source_sha")
    source_sha = str(campaign_source_sha) if campaign_source_sha else None

    jobs_raw = queue_state.get("jobs") or []
    if not isinstance(jobs_raw, list):
        raise StrategyMetricExtractionError("queue_state.jobs must be a list")

    queue_record_count = len(jobs_raw)
    canonical_jobs = select_canonical_jobs(jobs_raw)
    canonical_job_count = len(canonical_jobs)
    excluded_superseded = queue_record_count - canonical_job_count

    if (
        canonical_job_count != CANONICAL_JOB_COUNT
        and queue_record_count == QUEUE_RECORD_COUNT
    ):
        raise StrategyMetricExtractionError(
            f"expected {CANONICAL_JOB_COUNT} canonical jobs, got {canonical_job_count}"
        )
    if (
        excluded_superseded != SUPERSEDED_JOB_COUNT
        and queue_record_count == QUEUE_RECORD_COUNT
    ):
        raise StrategyMetricExtractionError(
            f"expected {SUPERSEDED_JOB_COUNT} superseded exclusions, got {excluded_superseded}"
        )

    records: list[dict[str, Any]] = []
    for job in sorted(canonical_jobs, key=lambda item: str(item.get("job_id") or "")):
        scenarios = job.get("scenarios") or sorted(ALLOWED_SCENARIOS)
        for scenario_id in sorted(str(s) for s in scenarios):
            if scenario_id not in ALLOWED_SCENARIOS:
                continue
            records.append(
                extract_scenario_record(
                    campaign_id=campaign_id,
                    job=job,
                    scenario_id=scenario_id,
                    repo_root=root,
                    campaign_source_sha=source_sha,
                )
            )

    records.sort(key=_record_sort_key)
    content_hash = canonical_hash([_hashable_record(record) for record in records])

    summary = ExtractionSummary(
        queue_record_count=queue_record_count,
        canonical_job_count=canonical_job_count,
        excluded_superseded_job_count=excluded_superseded,
        record_count=len(records),
        content_hash=content_hash,
    )
    return records, summary


def _hashable_record(record: Mapping[str, Any]) -> dict[str, Any]:
    excluded = {
        "source_artifact_sha256",
    }
    return {k: v for k, v in record.items() if k not in excluded}


def build_extraction_bundle(
    queue_state: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    records, summary = extract_campaign_metrics(queue_state, repo_root=repo_root)
    return {
        "schema_version": SCHEMA_VERSION,
        "campaign_id": str(queue_state.get("campaign_id") or ""),
        "canonical_job_selection": {
            "selector": CANONICAL_SELECTOR,
            "queue_record_count": summary.queue_record_count,
            "canonical_job_count": summary.canonical_job_count,
            "excluded_superseded_job_count": summary.excluded_superseded_job_count,
        },
        "record_count": summary.record_count,
        "content_hash": summary.content_hash,
        "records": records,
    }


def extract_from_queue_state_path(
    queue_state_path: Path,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    root = repo_root or Path(__file__).resolve().parents[2]
    queue_state = _load_json(queue_state_path)
    return build_extraction_bundle(queue_state, repo_root=root)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract deterministic ARVP strategy metrics (arvp_strategy_metrics.v1)."
    )
    parser.add_argument(
        "--queue-state",
        required=True,
        help="Path to vacation queue_state.json",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for dataset_spec resolution",
    )
    parser.add_argument(
        "--output",
        help="Optional output JSON path for extraction bundle",
    )
    parser.add_argument(
        "--hash-only",
        action="store_true",
        help="Print only the deterministic content hash",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    bundle = extract_from_queue_state_path(
        Path(args.queue_state).resolve(),
        repo_root=repo_root,
    )
    if args.hash_only:
        print(bundle["content_hash"])
    else:
        print(
            json.dumps(
                {
                    "content_hash": bundle["content_hash"],
                    "record_count": bundle["record_count"],
                    "canonical_job_count": bundle["canonical_job_selection"][
                        "canonical_job_count"
                    ],
                    "excluded_superseded_job_count": bundle["canonical_job_selection"][
                        "excluded_superseded_job_count"
                    ],
                },
                indent=2,
            )
        )
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            canonical_json_dumps(bundle) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
