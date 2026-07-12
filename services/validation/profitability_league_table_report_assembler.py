"""Governance-safe Strategy League table report assembler (#4017).

Builds an extended ``profitability_league_table_report.v1`` from one or more
``profitability_evidence_packet.v1`` payloads (typically an ARVP candidate bundle).

Uses Formula v1 scoring from ``profitability_league_scorer.py`` but enforces
ARVP rankability gates for *official* ranking. Descriptive comparison is allowed;
forced winners are not.

Safety: LR NO-GO, ranking_ready=false for cross-venue research, no promotion.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema.validators import validator_for

from core.replay.canonical_json import canonical_hash

from services.validation.arvp_candidate_evidence_assembler import (
    RANKABILITY_NOT,
    RANKABILITY_PARTIAL,
    RANKABILITY_RANKABLE,
)
from services.validation.profitability_league_scorer import (
    DEFAULT_MODEL_ID,
    FORMULA_REF,
    SCORER_VERSION,
    ProfitabilityLeagueScorerError,
    _DIMENSION_ORDER,
    _PACKET_SCHEMA_PATH,
    _REPORT_SCHEMA_PATH,
    _WEIGHTS,
    _ranking_sort_key,
    score_candidate,
)

SCORING_FORMULA_VERSION = "profitability_league_scoring_formula.v1"
EXIT_STATUS_PARTIAL_NO_WINNER = "HISTORICAL_LEAGUE_PARTIAL_NO_RANKABLE_WINNER"

_COMPARISON_DIMENSIONS: tuple[str, ...] = (
    "net_economic_result",
    "drawdown",
    "expectancy",
    "profit_factor",
    "stability_across_windows",
    "cost_sensitivity",
    "feed_gap_sensitivity",
    "sample_size",
    "split_coverage",
    "stress_behavior",
    "evidence_quality",
)

_NORMALIZATION_DOC = {
    "formula_dimensions": {
        "range": "[0.0, 100.0]",
        "method": "clamp per Formula v1 dimension rules",
        "rounding": "one decimal place at emission",
    },
    "comparison_dimensions": {
        "method": "raw PEP / arvp_evidence values; null means missing, not zero",
        "overlap_policy": "quote PnL never summed across overlapping windows",
    },
}


class ProfitabilityLeagueTableReportAssemblerError(ValueError):
    """Raised when league report assembly cannot complete safely."""


@dataclass(frozen=True, slots=True)
class LeagueReportAssemblyResult:
    report: dict[str, Any]
    report_content_hash: str


def _load_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_report(report: Mapping[str, Any]) -> None:
    schema = _load_schema(_REPORT_SCHEMA_PATH)
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(dict(report)), key=lambda err: str(err.message))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "<root>"
        raise ProfitabilityLeagueTableReportAssemblerError(
            f"Report schema mismatch at {location}: {first.message}"
        )


def _validate_pep(pep: Mapping[str, Any], *, artifact_role: str) -> None:
    schema = _load_schema(_PACKET_SCHEMA_PATH)
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(dict(pep)), key=lambda err: str(err.message))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "<root>"
        raise ProfitabilityLeagueTableReportAssemblerError(
            f"Schema mismatch for {artifact_role} at {location}: {first.message}"
        )


def _rankability_status(pep: Mapping[str, Any]) -> str:
    status = pep.get("rankability_status")
    if status in (RANKABILITY_RANKABLE, RANKABILITY_NOT, RANKABILITY_PARTIAL):
        return str(status)
    return RANKABILITY_NOT


def _is_officially_rankable(pep: Mapping[str, Any], score_ranking_ready: bool) -> bool:
    return _rankability_status(pep) == RANKABILITY_RANKABLE and score_ranking_ready


def _missing_marker(value: object) -> bool:
    return value is None


def _comparison_dimensions(pep: Mapping[str, Any]) -> dict[str, Any]:
    arvp = pep.get("arvp_evidence") if isinstance(pep.get("arvp_evidence"), Mapping) else {}
    coverage = pep.get("arvp_coverage") if isinstance(pep.get("arvp_coverage"), Mapping) else {}
    readiness = (
        pep.get("coverage_readiness")
        if isinstance(pep.get("coverage_readiness"), Mapping)
        else {}
    )

    split_stability = arvp.get("split_stability") if isinstance(arvp, Mapping) else None
    scenario_sensitivity = (
        arvp.get("scenario_sensitivity") if isinstance(arvp, Mapping) else None
    )
    stress_evidence = arvp.get("stress_evidence") if isinstance(arvp, Mapping) else None

    return {
        "net_economic_result": {
            "gross_return": pep.get("gross_return"),
            "net_return": pep.get("net_return"),
            "fees": pep.get("fees"),
        },
        "drawdown": {
            "max_drawdown": pep.get("max_drawdown"),
            "fee_adjusted_max_drawdown_r": None,
        },
        "expectancy": pep.get("expectancy"),
        "profit_factor": pep.get("profit_factor"),
        "stability_across_windows": split_stability,
        "cost_sensitivity": scenario_sensitivity,
        "feed_gap_sensitivity": scenario_sensitivity,
        "sample_size": {
            "trade_count": pep.get("trade_count"),
            "scenario_records": (
                coverage.get("sample_counts", {}).get("scenario_records")
                if isinstance(coverage.get("sample_counts"), Mapping)
                else None
            ),
        },
        "split_coverage": {
            "purpose_splits": coverage.get("purpose_splits"),
            "window_classes": coverage.get("window_classes"),
        },
        "stress_behavior": stress_evidence,
        "evidence_quality": {
            "rankability_status": pep.get("rankability_status"),
            "rankability_reasons": pep.get("rankability_reasons") or [],
            "missing_evidence": pep.get("missing_evidence") or [],
            "coverage_readiness": readiness,
            "paper_reference_status": pep.get("paper_reference_status"),
            "same_venue_status": pep.get("same_venue_status"),
        },
    }


def _dimension_definitions() -> list[dict[str, Any]]:
    formula_dims = [
        {
            "dimension_id": name,
            "kind": "formula_v1",
            "weight_pct": _WEIGHTS[name],
            "formula_ref": FORMULA_REF,
        }
        for name in _DIMENSION_ORDER
    ]
    comparison_dims = [
        {
            "dimension_id": name,
            "kind": "comparison_raw",
            "description": f"Descriptive {name} from PEP / arvp_evidence",
        }
        for name in _COMPARISON_DIMENSIONS
    ]
    return formula_dims + comparison_dims


def _exclusion_reasons(
    pep: Mapping[str, Any],
    *,
    score_sentinel: bool,
    score_failures: Sequence[str],
    officially_rankable: bool,
) -> list[str]:
    reasons: list[str] = []
    status = _rankability_status(pep)
    if status == RANKABILITY_NOT:
        reasons.extend(pep.get("rankability_reasons") or [])
        reasons.append("rankability_status=NOT_RANKABLE")
    elif status == RANKABILITY_PARTIAL:
        reasons.extend(pep.get("rankability_reasons") or [])
        reasons.append("rankability_status=PARTIAL_EVIDENCE (no official rank)")
    if score_sentinel:
        reasons.extend(score_failures)
    if not officially_rankable:
        reasons.append("official_ranking_withheld_by_rankability_gate")
    if pep.get("paper_reference_status") == "not_run":
        reasons.append("paper_reference_status=not_run")
    if pep.get("same_venue_status") == "not_run":
        reasons.append("same_venue_status=not_run")
    return _dedupe(reasons)


def _dedupe(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _hashable_report(report: Mapping[str, Any]) -> dict[str, Any]:
    excluded = {"generated_at", "report_content_hash"}
    return {key: value for key, value in report.items() if key not in excluded}


def _report_content_hash(report: Mapping[str, Any]) -> str:
    return canonical_hash(_hashable_report(report))


def _coverage_counts(peps: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    not_rankable = partial = 0
    for pep in peps:
        status = _rankability_status(pep)
        if status == RANKABILITY_NOT:
            not_rankable += 1
        elif status == RANKABILITY_PARTIAL:
            partial += 1
    return {
        "candidate_count": len(peps),
        "not_rankable_count": not_rankable,
        "partial_evidence_count": partial,
    }


def _governance_status(peps: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    paper = {pep.get("paper_reference_status") for pep in peps}
    same_venue = {pep.get("same_venue_status") for pep in peps}
    return {
        "paper_reference_status": "not_run" if paper <= {"not_run", None} else "mixed",
        "same_venue_status": "not_run" if same_venue <= {"not_run", None} else "mixed",
        "promotion_status": "NOT_AUTHORIZED",
    }


def build_governance_league_table_report(
    peps: Sequence[Mapping[str, Any]],
    *,
    campaign_id: str,
    evidence_class: str,
    source_content_hash: str,
    candidate_bundle_hash: str,
    report_id: str | None = None,
    model_id: str = DEFAULT_MODEL_ID,
    generated_at: str = "2026-07-12T11:19:44Z",
    validate: bool = True,
) -> LeagueReportAssemblyResult:
    """Build governance-extended league table report from PEPs."""

    if not peps:
        raise ProfitabilityLeagueTableReportAssemblerError(
            "at least one PEP is required"
        )

    ordered_peps = sorted(peps, key=lambda pep: str(pep.get("strategy_id") or pep.get("candidate_id")))

    scored: list[tuple[Mapping[str, Any], Any]] = []
    for pep in ordered_peps:
        if validate:
            _validate_pep(pep, artifact_role=str(pep.get("candidate_id")))
        scored.append((pep, score_candidate(pep)))

    officially_rankable_entries: list[tuple[Mapping[str, Any], Any]] = [
        (pep, result)
        for pep, result in scored
        if _is_officially_rankable(pep, result.ranking_ready)
    ]
    officially_rankable_entries.sort(key=lambda item: _ranking_sort_key(item[1]))

    official_ranking: list[dict[str, Any]] = []
    for rank, (pep, result) in enumerate(officially_rankable_entries, start=1):
        official_ranking.append(
            {
                "candidate_id": result.candidate_id,
                "strategy_id": pep.get("strategy_id"),
                "official_rank": rank,
                "total_score": result.total_score,
                "ranking_ready": True,
                "net_return": result.net_return,
            }
        )

    candidate_rows: list[dict[str, Any]] = []
    candidate_rankings: list[dict[str, Any]] = []

    for pep, result in scored:
        status = _rankability_status(pep)
        officially_rankable = _is_officially_rankable(pep, result.ranking_ready)
        exclusions = _exclusion_reasons(
            pep,
            score_sentinel=result.sentinel_mode,
            score_failures=result.hard_gate_failures,
            officially_rankable=officially_rankable,
        )

        emit_total_score = (
            result.total_score
            if status != RANKABILITY_NOT and not result.sentinel_mode
            else None
        )
        if result.sentinel_mode:
            emit_total_score = 0.0 if status != RANKABILITY_NOT else None

        row: dict[str, Any] = {
            "candidate_id": result.candidate_id,
            "strategy_id": pep.get("strategy_id"),
            "rankability_status": status,
            "official_rank": next(
                (
                    item["official_rank"]
                    for item in official_ranking
                    if item["candidate_id"] == result.candidate_id
                ),
                None,
            ),
            "ranking_ready": result.ranking_ready,
            "sentinel_mode": result.sentinel_mode,
            "total_score": emit_total_score,
            "net_return": result.net_return,
            "comparison_dimensions": _comparison_dimensions(pep),
            "dimension_scores": [
                {"dimension": item.dimension, "score": item.score}
                for item in result.dimension_scores
            ],
            "recommendation": result.recommendation,
            "exclusion_reasons": exclusions,
            "limitations_summary": list(result.limitations_summary),
        }
        candidate_rows.append(row)

        if officially_rankable:
            candidate_rankings.append(
                {
                    "candidate_id": result.candidate_id,
                    "rank": row["official_rank"],
                    "total_score": result.total_score,
                    "ranking_ready": True,
                    "net_return": result.net_return,
                    "dimension_scores": row["dimension_scores"],
                    "recommendation": result.recommendation,
                    "limitations_summary": row["limitations_summary"],
                }
            )

    counts = _coverage_counts(ordered_peps)
    governance = _governance_status(ordered_peps)

    source_packet_hashes = [
        str(pep.get("content_hash"))
        for pep in ordered_peps
        if pep.get("content_hash")
    ]

    report: dict[str, Any] = {
        "schema_version": "profitability_league_table_report.v1",
        "report_id": report_id or "pltr-arvp-binance-historical-4017",
        "model_id": model_id,
        "generated_at": generated_at,
        "campaign_id": campaign_id,
        "generated_from_bundle_hash": candidate_bundle_hash,
        "evidence_class": evidence_class,
        "table_status": "PARTIAL",
        "ranking_ready": False,
        "official_ranking": official_ranking,
        "winner": None,
        "candidate_count": counts["candidate_count"],
        "officially_ranked_count": len(official_ranking),
        "not_rankable_count": counts["not_rankable_count"],
        "partial_evidence_count": counts["partial_evidence_count"],
        "candidate_rows": candidate_rows,
        "dimension_definitions": _dimension_definitions(),
        "weights": dict(_WEIGHTS),
        "normalization": _NORMALIZATION_DOC,
        "exclusion_reasons": {
            row["candidate_id"]: row["exclusion_reasons"] for row in candidate_rows
        },
        "candidate_rankings": candidate_rankings,
        "limitations": [
            "Governance-safe Strategy League report for historical cross-venue research.",
            "official_ranking is empty when no candidate satisfies rankability gates.",
            "Descriptive candidate_rows are not an official ranking.",
            f"Formula ref: {FORMULA_REF} ({SCORING_FORMULA_VERSION}).",
            "LR remains NO-GO. promotion_status=NOT_AUTHORIZED.",
            f"Exit status: {EXIT_STATUS_PARTIAL_NO_WINNER}.",
        ],
        "paper_reference_status": governance["paper_reference_status"],
        "same_venue_status": governance["same_venue_status"],
        "promotion_status": governance["promotion_status"],
        "source_content_hash": source_content_hash,
        "candidate_bundle_hash": candidate_bundle_hash,
        "source_packet_hashes": source_packet_hashes,
        "scoring_formula_version": SCORING_FORMULA_VERSION,
        "scorer_version": SCORER_VERSION,
    }

    content_hash = _report_content_hash(report)
    report["report_content_hash"] = content_hash

    if validate:
        _validate_report(report)

    return LeagueReportAssemblyResult(report=report, report_content_hash=content_hash)


def assemble_from_pep_paths(
    pep_paths: Sequence[Path],
    *,
    campaign_id: str,
    evidence_class: str,
    source_content_hash: str,
    candidate_bundle_hash: str,
    validate: bool = True,
) -> LeagueReportAssemblyResult:
    peps: list[dict[str, Any]] = []
    for path in sorted(pep_paths):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ProfitabilityLeagueTableReportAssemblerError(
                f"PEP {path} must be a JSON object"
            )
        peps.append(payload)
    return build_governance_league_table_report(
        peps,
        campaign_id=campaign_id,
        evidence_class=evidence_class,
        source_content_hash=source_content_hash,
        candidate_bundle_hash=candidate_bundle_hash,
        validate=validate,
    )


def assemble_from_candidate_bundle_dir(
    bundle_dir: Path,
    *,
    validate: bool = True,
) -> LeagueReportAssemblyResult:
    manifest_path = bundle_dir / "bundle_manifest.json"
    if not manifest_path.is_file():
        raise ProfitabilityLeagueTableReportAssemblerError(
            f"bundle manifest not found: {manifest_path}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ProfitabilityLeagueTableReportAssemblerError("bundle manifest must be object")

    bundle_hash = str(manifest.get("bundle_hash") or "")
    packets_meta = manifest.get("packets") or []
    if not bundle_hash or not isinstance(packets_meta, list):
        raise ProfitabilityLeagueTableReportAssemblerError(
            "bundle manifest missing bundle_hash or packets"
        )

    pep_paths = [bundle_dir / str(item.get("path", "")) for item in packets_meta]
    peps: list[dict[str, Any]] = []
    for path in pep_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ProfitabilityLeagueTableReportAssemblerError(
                f"PEP {path} must be a JSON object"
            )
        peps.append(payload)

    if not peps:
        raise ProfitabilityLeagueTableReportAssemblerError("bundle contains no PEP files")

    first = peps[0]
    campaign_id = str(first.get("campaign_id") or "")
    evidence_class = str(first.get("evidence_class") or "")
    source_content_hash = str(first.get("source_content_hash") or "")
    if not campaign_id or not source_content_hash:
        raise ProfitabilityLeagueTableReportAssemblerError(
            "PEPs must include campaign_id and source_content_hash"
        )

    return build_governance_league_table_report(
        peps,
        campaign_id=campaign_id,
        evidence_class=evidence_class,
        source_content_hash=source_content_hash,
        candidate_bundle_hash=bundle_hash,
        validate=validate,
    )


def write_report_output(
    result: LeagueReportAssemblyResult,
    *,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(result.report, ensure_ascii=True, indent=2, sort_keys=True)
    output_path.write_text(serialized + "\n", encoding="utf-8")
