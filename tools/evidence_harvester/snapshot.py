from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


SNAPSHOT_SCHEMA_VERSION = "cdb.evidence_harvester.snapshot.v1"
COLLECTOR_REPORT_SCHEMA_VERSION = "evidence_harvester.collector_report.v1"
ALLOWED_SOURCE_MODES = {"fixture", "future_readonly"}
ALLOWED_ROW_STATUSES = {"info", "warning", "blocking"}
ALLOWED_PROVENANCE_STATUSES = {"allowed", "unknown", "contaminated"}

SAFETY_BANNER = (
    "Paper/research evidence only; no LR-Go, no Live-Go, no Echtgeld-Go."
)


class SnapshotValidationError(ValueError):
    pass


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _hash_payload(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def _parse_ts(value: Any, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise SnapshotValidationError(f"{field_name} must not be blank")
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise SnapshotValidationError(
                f"{field_name} must be an ISO-8601 UTC timestamp"
            ) from exc
    else:
        raise SnapshotValidationError(
            f"{field_name} must be an ISO-8601 UTC timestamp"
        )

    if parsed.tzinfo is None:
        raise SnapshotValidationError(f"{field_name} must be timezone-aware UTC")
    return parsed.astimezone(UTC)


def _format_ts(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SnapshotValidationError(f"{field_name} must be an object")
    return value


def _require_sequence(value: Any, field_name: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise SnapshotValidationError(f"{field_name} must be an array")
    return value


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise SnapshotValidationError(f"{field_name} must be a string")
    text = value.strip()
    if not text:
        raise SnapshotValidationError(f"{field_name} must not be blank")
    return text


def _require_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SnapshotValidationError(f"{field_name} must be an integer")
    return value


def _require_non_negative_int(value: Any, field_name: str) -> int:
    parsed = _require_int(value, field_name)
    if parsed < 0:
        raise SnapshotValidationError(f"{field_name} must be non-negative")
    return parsed


def _require_float(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SnapshotValidationError(f"{field_name} must be numeric")
    return float(value)


def _require_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise SnapshotValidationError(f"{field_name} must be a boolean")
    return value


def _require_exact_keys(
    mapping: Mapping[str, Any],
    field_name: str,
    expected: Sequence[str],
) -> None:
    actual = set(mapping.keys())
    required = set(expected)
    missing = sorted(required - actual)
    extra = sorted(actual - required)
    if missing or extra:
        problems: list[str] = []
        if missing:
            problems.append(f"missing keys: {', '.join(missing)}")
        if extra:
            problems.append(f"unexpected keys: {', '.join(extra)}")
        raise SnapshotValidationError(f"{field_name} malformed ({'; '.join(problems)})")


def _average_ratio(observed_total: int, expected_total: int) -> float:
    if expected_total <= 0:
        return 0.0
    return round(observed_total / expected_total, 6)


def _status_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {"blocking": 0, "warning": 0, "info": 0}
    for row in rows:
        counts[row["status"]] += 1
    return counts


def _overall_status_from_counts(counts: Mapping[str, int]) -> str:
    if counts.get("blocking", 0) > 0:
        return "blocked"
    if counts.get("warning", 0) > 0:
        return "warning"
    return "ok"


def _top_gap_types(gap_items: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    gap_types: dict[str, int] = {}
    for item in gap_items:
        gap_types[item["gap_type"]] = gap_types.get(item["gap_type"], 0) + 1
    return dict(sorted(gap_types.items(), key=lambda item: item[0]))


def _next_action_hints(gap_items: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    hints_by_type = {
        "stale_feed": "Restore fresh candle ingestion before relying on this snapshot.",
        "missing_candles": "Backfill or repair missing candle coverage in the affected streams.",
        "stale_regime": "Refresh regime generation so regime coverage is current.",
        "missing_regime": "Repair regime production to restore full regime coverage.",
        "zero_paper_chains": "Investigate why complete paper chains are missing for the affected scope.",
        "missing_signal_density": "Restore signal production before using paper-chain counts as evidence.",
        "partial_paper_chains": "Inspect partial paper chains and close the broken signal-to-fill path.",
        "provenance_contamination": "Remove unknown or contaminated provenance before treating the evidence as clean.",
    }
    hints: list[str] = []
    seen: set[str] = set()
    for item in gap_items:
        gap_type = item["gap_type"]
        if gap_type in seen:
            continue
        seen.add(gap_type)
        if gap_type in hints_by_type:
            hints.append(hints_by_type[gap_type])
    if not hints:
        hints.append("No immediate gap-driven action; continue passive evidence collection.")
    return tuple(hints)


def _validate_raw_evidence(payload: Any) -> dict[str, int]:
    mapping = _require_mapping(payload, "raw_evidence")
    keys = [
        "candle_input_count",
        "regime_input_count",
        "paper_chain_input_count",
        "provenance_input_count",
        "observed_input_count",
    ]
    _require_exact_keys(mapping, "raw_evidence", keys)
    return {
        key: _require_non_negative_int(mapping[key], f"raw_evidence.{key}") for key in keys
    }


def _validate_candle_rows(payload: Any) -> list[dict[str, Any]]:
    rows = _require_sequence(payload, "candle_coverages")
    normalized: list[dict[str, Any]] = []
    expected_keys = [
        "symbol",
        "venue",
        "timeframe",
        "status",
        "first_ts_utc",
        "last_ts_utc",
        "observed_count",
        "expected_count",
        "missing_count",
        "coverage_pct",
        "stale_minutes",
    ]
    for index, row in enumerate(rows):
        mapping = _require_mapping(row, f"candle_coverages[{index}]")
        _require_exact_keys(mapping, f"candle_coverages[{index}]", expected_keys)
        status = _require_string(mapping["status"], f"candle_coverages[{index}].status")
        if status not in ALLOWED_ROW_STATUSES:
            raise SnapshotValidationError(
                f"candle_coverages[{index}].status must be one of blocking|warning|info"
            )
        normalized.append(
            {
                "symbol": _require_string(
                    mapping["symbol"], f"candle_coverages[{index}].symbol"
                ),
                "venue": _require_string(
                    mapping["venue"], f"candle_coverages[{index}].venue"
                ),
                "timeframe": _require_string(
                    mapping["timeframe"], f"candle_coverages[{index}].timeframe"
                ),
                "status": status,
                "first_ts_utc": _format_ts(
                    _parse_ts(
                        mapping["first_ts_utc"],
                        f"candle_coverages[{index}].first_ts_utc",
                    )
                ),
                "last_ts_utc": _format_ts(
                    _parse_ts(
                        mapping["last_ts_utc"],
                        f"candle_coverages[{index}].last_ts_utc",
                    )
                ),
                "observed_count": _require_non_negative_int(
                    mapping["observed_count"],
                    f"candle_coverages[{index}].observed_count",
                ),
                "expected_count": _require_non_negative_int(
                    mapping["expected_count"],
                    f"candle_coverages[{index}].expected_count",
                ),
                "missing_count": _require_non_negative_int(
                    mapping["missing_count"],
                    f"candle_coverages[{index}].missing_count",
                ),
                "coverage_pct": round(
                    _require_float(
                        mapping["coverage_pct"],
                        f"candle_coverages[{index}].coverage_pct",
                    ),
                    6,
                ),
                "stale_minutes": _require_non_negative_int(
                    mapping["stale_minutes"],
                    f"candle_coverages[{index}].stale_minutes",
                ),
            }
        )
    return sorted(
        normalized,
        key=lambda item: (
            item["symbol"],
            item["venue"],
            item["timeframe"],
            item["first_ts_utc"],
        ),
    )


def _validate_regime_rows(payload: Any) -> list[dict[str, Any]]:
    rows = _require_sequence(payload, "regime_coverages")
    normalized: list[dict[str, Any]] = []
    expected_keys = [
        "symbol",
        "venue",
        "timeframe",
        "status",
        "first_ts_utc",
        "last_ts_utc",
        "observed_count",
        "expected_count",
        "missing_count",
        "coverage_pct",
        "stale_minutes",
        "regime_distribution",
    ]
    distribution_keys = ["regime", "count", "share"]
    for index, row in enumerate(rows):
        mapping = _require_mapping(row, f"regime_coverages[{index}]")
        _require_exact_keys(mapping, f"regime_coverages[{index}]", expected_keys)
        status = _require_string(mapping["status"], f"regime_coverages[{index}].status")
        if status not in ALLOWED_ROW_STATUSES:
            raise SnapshotValidationError(
                f"regime_coverages[{index}].status must be one of blocking|warning|info"
            )
        distribution_rows = _require_sequence(
            mapping["regime_distribution"],
            f"regime_coverages[{index}].regime_distribution",
        )
        distribution: list[dict[str, Any]] = []
        for dist_index, dist_row in enumerate(distribution_rows):
            dist_mapping = _require_mapping(
                dist_row,
                f"regime_coverages[{index}].regime_distribution[{dist_index}]",
            )
            _require_exact_keys(
                dist_mapping,
                f"regime_coverages[{index}].regime_distribution[{dist_index}]",
                distribution_keys,
            )
            distribution.append(
                {
                    "regime": _require_string(
                        dist_mapping["regime"],
                        (
                            "regime_coverages"
                            f"[{index}].regime_distribution[{dist_index}].regime"
                        ),
                    ),
                    "count": _require_non_negative_int(
                        dist_mapping["count"],
                        (
                            "regime_coverages"
                            f"[{index}].regime_distribution[{dist_index}].count"
                        ),
                    ),
                    "share": round(
                        _require_float(
                            dist_mapping["share"],
                            (
                                "regime_coverages"
                                f"[{index}].regime_distribution[{dist_index}].share"
                            ),
                        ),
                        6,
                    ),
                }
            )
        normalized.append(
            {
                "symbol": _require_string(
                    mapping["symbol"], f"regime_coverages[{index}].symbol"
                ),
                "venue": _require_string(
                    mapping["venue"], f"regime_coverages[{index}].venue"
                ),
                "timeframe": _require_string(
                    mapping["timeframe"], f"regime_coverages[{index}].timeframe"
                ),
                "status": status,
                "first_ts_utc": _format_ts(
                    _parse_ts(
                        mapping["first_ts_utc"],
                        f"regime_coverages[{index}].first_ts_utc",
                    )
                ),
                "last_ts_utc": _format_ts(
                    _parse_ts(
                        mapping["last_ts_utc"],
                        f"regime_coverages[{index}].last_ts_utc",
                    )
                ),
                "observed_count": _require_non_negative_int(
                    mapping["observed_count"],
                    f"regime_coverages[{index}].observed_count",
                ),
                "expected_count": _require_non_negative_int(
                    mapping["expected_count"],
                    f"regime_coverages[{index}].expected_count",
                ),
                "missing_count": _require_non_negative_int(
                    mapping["missing_count"],
                    f"regime_coverages[{index}].missing_count",
                ),
                "coverage_pct": round(
                    _require_float(
                        mapping["coverage_pct"],
                        f"regime_coverages[{index}].coverage_pct",
                    ),
                    6,
                ),
                "stale_minutes": _require_non_negative_int(
                    mapping["stale_minutes"],
                    f"regime_coverages[{index}].stale_minutes",
                ),
                "regime_distribution": tuple(
                    sorted(
                        distribution,
                        key=lambda item: item["regime"],
                    )
                ),
            }
        )
    return sorted(
        normalized,
        key=lambda item: (
            item["symbol"],
            item["venue"],
            item["timeframe"],
            item["first_ts_utc"],
        ),
    )


def _validate_paper_chain_rows(payload: Any) -> list[dict[str, Any]]:
    rows = _require_sequence(payload, "paper_chain_coverages")
    normalized: list[dict[str, Any]] = []
    expected_keys = [
        "symbol",
        "venue",
        "timeframe",
        "status",
        "observation_window_hours",
        "signal_count",
        "decision_count",
        "order_count",
        "fill_count",
        "complete_chain_count",
        "partial_chain_count",
        "signal_density_per_hour",
    ]
    for index, row in enumerate(rows):
        mapping = _require_mapping(row, f"paper_chain_coverages[{index}]")
        _require_exact_keys(mapping, f"paper_chain_coverages[{index}]", expected_keys)
        status = _require_string(
            mapping["status"], f"paper_chain_coverages[{index}].status"
        )
        if status not in ALLOWED_ROW_STATUSES:
            raise SnapshotValidationError(
                "paper_chain_coverages"
                f"[{index}].status must be one of blocking|warning|info"
            )
        normalized.append(
            {
                "symbol": _require_string(
                    mapping["symbol"], f"paper_chain_coverages[{index}].symbol"
                ),
                "venue": _require_string(
                    mapping["venue"], f"paper_chain_coverages[{index}].venue"
                ),
                "timeframe": _require_string(
                    mapping["timeframe"],
                    f"paper_chain_coverages[{index}].timeframe",
                ),
                "status": status,
                "observation_window_hours": round(
                    _require_float(
                        mapping["observation_window_hours"],
                        (
                            "paper_chain_coverages"
                            f"[{index}].observation_window_hours"
                        ),
                    ),
                    6,
                ),
                "signal_count": _require_non_negative_int(
                    mapping["signal_count"],
                    f"paper_chain_coverages[{index}].signal_count",
                ),
                "decision_count": _require_non_negative_int(
                    mapping["decision_count"],
                    f"paper_chain_coverages[{index}].decision_count",
                ),
                "order_count": _require_non_negative_int(
                    mapping["order_count"],
                    f"paper_chain_coverages[{index}].order_count",
                ),
                "fill_count": _require_non_negative_int(
                    mapping["fill_count"],
                    f"paper_chain_coverages[{index}].fill_count",
                ),
                "complete_chain_count": _require_non_negative_int(
                    mapping["complete_chain_count"],
                    f"paper_chain_coverages[{index}].complete_chain_count",
                ),
                "partial_chain_count": _require_non_negative_int(
                    mapping["partial_chain_count"],
                    f"paper_chain_coverages[{index}].partial_chain_count",
                ),
                "signal_density_per_hour": round(
                    _require_float(
                        mapping["signal_density_per_hour"],
                        (
                            "paper_chain_coverages"
                            f"[{index}].signal_density_per_hour"
                        ),
                    ),
                    6,
                ),
            }
        )
    return sorted(
        normalized,
        key=lambda item: (item["symbol"], item["venue"], item["timeframe"]),
    )


def _validate_provenance(payload: Any) -> dict[str, Any]:
    mapping = _require_mapping(payload, "provenance")
    expected_keys = [
        "allowed_sources",
        "source_findings",
        "unknown_source_count",
        "contaminated_source_count",
    ]
    _require_exact_keys(mapping, "provenance", expected_keys)
    allowed_sources = sorted(
        _require_string(item, f"provenance.allowed_sources[{index}]")
        for index, item in enumerate(
            _require_sequence(mapping["allowed_sources"], "provenance.allowed_sources")
        )
    )
    source_rows = _require_sequence(mapping["source_findings"], "provenance.source_findings")
    normalized_sources: list[dict[str, Any]] = []
    source_keys = ["source", "observed_count", "status"]
    for index, row in enumerate(source_rows):
        source_mapping = _require_mapping(row, f"provenance.source_findings[{index}]")
        _require_exact_keys(
            source_mapping,
            f"provenance.source_findings[{index}]",
            source_keys,
        )
        status = _require_string(
            source_mapping["status"],
            f"provenance.source_findings[{index}].status",
        )
        if status not in ALLOWED_PROVENANCE_STATUSES:
            raise SnapshotValidationError(
                "provenance.source_findings"
                f"[{index}].status must be one of allowed|unknown|contaminated"
            )
        normalized_sources.append(
            {
                "source": _require_string(
                    source_mapping["source"],
                    f"provenance.source_findings[{index}].source",
                ),
                "observed_count": _require_non_negative_int(
                    source_mapping["observed_count"],
                    f"provenance.source_findings[{index}].observed_count",
                ),
                "status": status,
            }
        )
    unknown_count = _require_non_negative_int(
        mapping["unknown_source_count"],
        "provenance.unknown_source_count",
    )
    contaminated_count = _require_non_negative_int(
        mapping["contaminated_source_count"],
        "provenance.contaminated_source_count",
    )
    if contaminated_count > 0:
        status = "blocked"
    elif unknown_count > 0:
        status = "warning"
    else:
        status = "ok"
    return {
        "status": status,
        "allowed_sources": tuple(allowed_sources),
        "unknown_source_count": unknown_count,
        "contaminated_source_count": contaminated_count,
        "source_findings": tuple(
            sorted(normalized_sources, key=lambda item: (item["status"], item["source"]))
        ),
    }


def _validate_gap_findings(payload: Any) -> dict[str, Any]:
    rows = _require_sequence(payload, "gap_findings")
    normalized: list[dict[str, Any]] = []
    expected_keys = ["gap_id", "gap_type", "severity", "message", "scope", "source_refs"]
    for index, row in enumerate(rows):
        mapping = _require_mapping(row, f"gap_findings[{index}]")
        _require_exact_keys(mapping, f"gap_findings[{index}]", expected_keys)
        severity = _require_string(
            mapping["severity"], f"gap_findings[{index}].severity"
        )
        if severity not in ALLOWED_ROW_STATUSES:
            raise SnapshotValidationError(
                f"gap_findings[{index}].severity must be one of blocking|warning|info"
            )
        source_refs = tuple(
            sorted(
                _require_string(item, f"gap_findings[{index}].source_refs[{ref_index}]")
                for ref_index, item in enumerate(
                    _require_sequence(
                        mapping["source_refs"],
                        f"gap_findings[{index}].source_refs",
                    )
                )
            )
        )
        normalized.append(
            {
                "gap_id": _require_string(
                    mapping["gap_id"], f"gap_findings[{index}].gap_id"
                ),
                "gap_type": _require_string(
                    mapping["gap_type"], f"gap_findings[{index}].gap_type"
                ),
                "severity": severity,
                "message": _require_string(
                    mapping["message"], f"gap_findings[{index}].message"
                ),
                "scope": _require_string(
                    mapping["scope"], f"gap_findings[{index}].scope"
                ),
                "source_refs": source_refs,
            }
        )
    counts = {"blocking": 0, "warning": 0, "info": 0}
    for item in normalized:
        counts[item["severity"]] += 1
    items = sorted(
        normalized,
        key=lambda item: (item["severity"], item["gap_type"], item["scope"], item["gap_id"]),
    )
    return {
        "summary": {
            "total_count": len(items),
            "blocking_count": counts["blocking"],
            "warning_count": counts["warning"],
            "info_count": counts["info"],
            "by_type": _top_gap_types(items),
        },
        "items": tuple(items),
    }


def _validate_summary(payload: Any) -> dict[str, Any]:
    mapping = _require_mapping(payload, "summary")
    keys = [
        "overall_status",
        "blocking_count",
        "warning_count",
        "info_count",
        "has_zero_paper_chains",
    ]
    _require_exact_keys(mapping, "summary", keys)
    overall_status = _require_string(mapping["overall_status"], "summary.overall_status")
    if overall_status not in {"ok", "warning", "blocked"}:
        raise SnapshotValidationError("summary.overall_status must be one of ok|warning|blocked")
    return {
        "overall_status": overall_status,
        "blocking_count": _require_non_negative_int(
            mapping["blocking_count"], "summary.blocking_count"
        ),
        "warning_count": _require_non_negative_int(
            mapping["warning_count"], "summary.warning_count"
        ),
        "info_count": _require_non_negative_int(mapping["info_count"], "summary.info_count"),
        "has_zero_paper_chains": _require_bool(
            mapping["has_zero_paper_chains"], "summary.has_zero_paper_chains"
        ),
    }


def _normalize_report(payload: Mapping[str, Any]) -> dict[str, Any]:
    expected_keys = [
        "schema_version",
        "report_id",
        "evidence_class",
        "evidence_class_version",
        "produced_by",
        "produced_at_utc",
        "source_mode",
        "raw_evidence",
        "candle_coverages",
        "regime_coverages",
        "paper_chain_coverages",
        "provenance",
        "gap_findings",
        "summary",
    ]
    _require_exact_keys(payload, "collector_report", expected_keys)

    schema_version = _require_string(payload["schema_version"], "collector_report.schema_version")
    if schema_version != COLLECTOR_REPORT_SCHEMA_VERSION:
        raise SnapshotValidationError(
            "collector_report.schema_version must be evidence_harvester.collector_report.v1"
        )
    source_mode = _require_string(payload["source_mode"], "collector_report.source_mode")
    if source_mode not in ALLOWED_SOURCE_MODES:
        raise SnapshotValidationError(
            "collector_report.source_mode must be one of fixture|future_readonly"
        )
    return {
        "schema_version": schema_version,
        "report_id": _require_string(payload["report_id"], "collector_report.report_id"),
        "evidence_class": _require_string(
            payload["evidence_class"], "collector_report.evidence_class"
        ),
        "evidence_class_version": _require_string(
            payload["evidence_class_version"],
            "collector_report.evidence_class_version",
        ),
        "produced_by": _require_string(
            payload["produced_by"], "collector_report.produced_by"
        ),
        "produced_at_utc": _format_ts(
            _parse_ts(payload["produced_at_utc"], "collector_report.produced_at_utc")
        ),
        "source_mode": source_mode,
        "raw_evidence": _validate_raw_evidence(payload["raw_evidence"]),
        "candle_coverages": tuple(_validate_candle_rows(payload["candle_coverages"])),
        "regime_coverages": tuple(_validate_regime_rows(payload["regime_coverages"])),
        "paper_chain_coverages": tuple(
            _validate_paper_chain_rows(payload["paper_chain_coverages"])
        ),
        "provenance": _validate_provenance(payload["provenance"]),
        "gap_findings": _validate_gap_findings(payload["gap_findings"]),
        "summary": _validate_summary(payload["summary"]),
    }


@dataclass(frozen=True, slots=True)
class EvidenceSnapshot:
    metadata: dict[str, Any]
    status: dict[str, Any]
    coverage: dict[str, Any]
    provenance: dict[str, Any]
    paper_chains: dict[str, Any]
    gap_findings: dict[str, Any]
    safety: dict[str, Any]
    next_action_hints: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_snapshot(
    collector_report_payload: Mapping[str, Any],
    generated_at_utc: datetime | str | None = None,
) -> EvidenceSnapshot:
    report = _normalize_report(collector_report_payload)
    generated_at = _format_ts(
        _parse_ts(generated_at_utc, "generated_at_utc")
        if generated_at_utc is not None
        else utc_now()
    )

    candle_rows = list(report["candle_coverages"])
    regime_rows = list(report["regime_coverages"])
    paper_rows = list(report["paper_chain_coverages"])
    gap_section = report["gap_findings"]
    gap_items = list(gap_section["items"])
    provenance = report["provenance"]

    candle_status_counts = _status_counts(candle_rows)
    regime_status_counts = _status_counts(regime_rows)
    paper_status_counts = _status_counts(paper_rows)

    candle_observed_total = sum(item["observed_count"] for item in candle_rows)
    candle_expected_total = sum(item["expected_count"] for item in candle_rows)
    regime_observed_total = sum(item["observed_count"] for item in regime_rows)
    regime_expected_total = sum(item["expected_count"] for item in regime_rows)

    paper_complete_total = sum(item["complete_chain_count"] for item in paper_rows)
    paper_partial_total = sum(item["partial_chain_count"] for item in paper_rows)
    paper_signal_total = sum(item["signal_count"] for item in paper_rows)
    paper_decision_total = sum(item["decision_count"] for item in paper_rows)
    paper_order_total = sum(item["order_count"] for item in paper_rows)
    paper_fill_total = sum(item["fill_count"] for item in paper_rows)
    paper_zero_complete_count = sum(
        1 for item in paper_rows if item["complete_chain_count"] == 0
    )
    paper_zero_signal_count = sum(1 for item in paper_rows if item["signal_count"] == 0)

    snapshot = EvidenceSnapshot(
        metadata={
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "generated_at_utc": generated_at,
            "collector_report_hash": _hash_payload(report),
            "collector_report_id": report["report_id"],
            "collector_report_schema_version": report["schema_version"],
            "source_mode": report["source_mode"],
            "evidence_class": report["evidence_class"],
            "evidence_class_version": report["evidence_class_version"],
            "produced_by": report["produced_by"],
            "collector_report_produced_at_utc": report["produced_at_utc"],
        },
        status={
            "overall_status": report["summary"]["overall_status"],
            "gap_counts": {
                "blocking": report["summary"]["blocking_count"],
                "warning": report["summary"]["warning_count"],
                "info": report["summary"]["info_count"],
            },
            "has_zero_paper_chains": report["summary"]["has_zero_paper_chains"],
            "raw_evidence": report["raw_evidence"],
        },
        coverage={
            "candles": {
                "status": _overall_status_from_counts(candle_status_counts),
                "total_streams": len(candle_rows),
                "observed_count_total": candle_observed_total,
                "expected_count_total": candle_expected_total,
                "coverage_pct": _average_ratio(
                    candle_observed_total,
                    candle_expected_total,
                ),
                "stale_stream_count": sum(
                    1 for item in candle_rows if item["status"] == "blocking"
                ),
                "status_counts": candle_status_counts,
                "items": tuple(candle_rows),
            },
            "regimes": {
                "status": _overall_status_from_counts(regime_status_counts),
                "total_streams": len(regime_rows),
                "observed_count_total": regime_observed_total,
                "expected_count_total": regime_expected_total,
                "coverage_pct": _average_ratio(
                    regime_observed_total,
                    regime_expected_total,
                ),
                "zero_coverage_stream_count": sum(
                    1 for item in regime_rows if item["observed_count"] == 0
                ),
                "status_counts": regime_status_counts,
                "items": tuple(regime_rows),
            },
        },
        provenance={
            "status": provenance["status"],
            "allowed_sources": provenance["allowed_sources"],
            "unknown_source_count": provenance["unknown_source_count"],
            "contaminated_source_count": provenance["contaminated_source_count"],
            "source_findings": provenance["source_findings"],
        },
        paper_chains={
            "status": _overall_status_from_counts(paper_status_counts),
            "total_streams": len(paper_rows),
            "signal_count_total": paper_signal_total,
            "decision_count_total": paper_decision_total,
            "order_count_total": paper_order_total,
            "fill_count_total": paper_fill_total,
            "complete_chain_count_total": paper_complete_total,
            "partial_chain_count_total": paper_partial_total,
            "zero_complete_stream_count": paper_zero_complete_count,
            "zero_signal_stream_count": paper_zero_signal_count,
            "average_signal_density_per_hour": round(
                sum(item["signal_density_per_hour"] for item in paper_rows) / len(paper_rows),
                6,
            )
            if paper_rows
            else 0.0,
            "status_counts": paper_status_counts,
            "items": tuple(paper_rows),
        },
        gap_findings={
            "summary": gap_section["summary"],
            "items": tuple(gap_items),
        },
        safety={
            "banner": SAFETY_BANNER,
            "lr_status": "NO-GO",
            "live_status": "NO-GO",
            "echtgeld_status": "NO-GO",
            "runtime_actions": "not_allowed",
            "db_execution": "not_allowed",
            "background_job_orchestration": "not_in_scope",
            "allowed_scope": "fixture/mock-based collector report snapshot generation only",
        },
        next_action_hints=_next_action_hints(gap_items),
    )
    return snapshot


def snapshot_to_markdown(snapshot: EvidenceSnapshot) -> str:
    payload = snapshot.to_dict()
    lines = [
        "# Daily Evidence Snapshot",
        "",
        "## Status",
        f"- Overall status: {payload['status']['overall_status']}",
        f"- Generated at (UTC): {payload['metadata']['generated_at_utc']}",
        f"- Collector report: {payload['metadata']['collector_report_id']}",
        f"- Collector report hash: {payload['metadata']['collector_report_hash']}",
        f"- Source mode: {payload['metadata']['source_mode']}",
        "",
        "## Coverage Summary",
        (
            "- Candle coverage: "
            f"{payload['coverage']['candles']['observed_count_total']}"
            "/"
            f"{payload['coverage']['candles']['expected_count_total']} observed "
            f"({payload['coverage']['candles']['coverage_pct']:.6f}), "
            f"stale_streams={payload['coverage']['candles']['stale_stream_count']}, "
            f"status={payload['coverage']['candles']['status']}"
        ),
        (
            "- Regime coverage: "
            f"{payload['coverage']['regimes']['observed_count_total']}"
            "/"
            f"{payload['coverage']['regimes']['expected_count_total']} observed "
            f"({payload['coverage']['regimes']['coverage_pct']:.6f}), "
            f"zero_coverage_streams={payload['coverage']['regimes']['zero_coverage_stream_count']}, "
            + f"status={payload['coverage']['regimes']['status']}"
        ),
        "",
        "## Paper Chain Summary",
        (
            "- Paper chains: "
            f"complete={payload['paper_chains']['complete_chain_count_total']}, "
            f"partial={payload['paper_chains']['partial_chain_count_total']}, "
            f"signals={payload['paper_chains']['signal_count_total']}, "
            f"avg_signal_density_per_hour="
            f"{payload['paper_chains']['average_signal_density_per_hour']:.6f}, "
            f"status={payload['paper_chains']['status']}"
        ),
        "",
        "## Provenance",
        f"- Status: {payload['provenance']['status']}",
        (
            "- Allowed sources: "
            + ", ".join(payload['provenance']['allowed_sources'])
            if payload['provenance']['allowed_sources']
            else "- Allowed sources: none"
        ),
        (
            "- Unknown observations: "
            f"{payload['provenance']['unknown_source_count']}; contaminated observations: "
            f"{payload['provenance']['contaminated_source_count']}"
        ),
        "",
        "## Gap Findings",
        (
            "- Summary: "
            f"blocking={payload['gap_findings']['summary']['blocking_count']}, "
            f"warning={payload['gap_findings']['summary']['warning_count']}, "
            f"info={payload['gap_findings']['summary']['info_count']}, "
            f"total={payload['gap_findings']['summary']['total_count']}"
        ),
    ]
    if payload["gap_findings"]["items"]:
        for item in payload["gap_findings"]["items"]:
            lines.append(
                f"- [{item['severity']}] {item['gap_type']} @ {item['scope']}: {item['message']}"
            )
    else:
        lines.append("- No gap findings.")
    lines.extend(
        [
            "",
            "## Safety Boundaries",
            f"- {payload['safety']['banner']}",
            f"- LR status: {payload['safety']['lr_status']}",
            f"- Live status: {payload['safety']['live_status']}",
            f"- Echtgeld status: {payload['safety']['echtgeld_status']}",
            (
                "- Background job orchestration: "
                f"{payload['safety']['background_job_orchestration']}"
            ),
            f"- Runtime actions: {payload['safety']['runtime_actions']}",
            f"- DB execution: {payload['safety']['db_execution']}",
            "",
            "## Next Action Hints",
        ]
    )
    for hint in payload["next_action_hints"]:
        lines.append(f"- {hint}")
    return "\n".join(lines) + "\n"


def load_collector_report_fixture(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SnapshotValidationError("Collector report fixture JSON root must be an object")
    return dict(payload)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic evidence snapshots from collector-report fixtures."
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        required=True,
        help="Path to a collector-report JSON fixture.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional path for the JSON snapshot artifact.",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        help="Optional path for the Markdown snapshot artifact.",
    )
    parser.add_argument(
        "--generated-at-utc",
        type=str,
        help="Optional ISO-8601 UTC timestamp for deterministic snapshot generation.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output instead of compact JSON.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.json_output and not args.markdown_output:
        raise SnapshotValidationError(
            "At least one of --json-output or --markdown-output must be provided"
        )

    report_payload = load_collector_report_fixture(args.fixture)
    snapshot = build_snapshot(report_payload, generated_at_utc=args.generated_at_utc)
    snapshot_payload = snapshot.to_dict()
    json_text = json.dumps(
        snapshot_payload,
        indent=2 if args.pretty else None,
        sort_keys=True,
        ensure_ascii=True,
    )
    markdown_text = snapshot_to_markdown(snapshot)

    if args.json_output:
        args.json_output.write_text(
            json_text + ("\n" if not json_text.endswith("\n") else ""),
            encoding="utf-8",
        )
    if args.markdown_output:
        args.markdown_output.write_text(markdown_text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
