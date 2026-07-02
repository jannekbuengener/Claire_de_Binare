"""Offline, fail-closed Strategy League scorer v1.

Makes the scoring rules from
``docs/strategy/CDB_PROFITABILITY_LEAGUE_SCORING_FORMULA_V1.md`` (#3682) executable
as an offline validation mechanism. Given one or more
``profitability_evidence_packet.v1`` payloads, it emits a
``profitability_league_table_report.v1``-shaped report.

Explicitly NOT authorized by this module:

- No runtime scorer service, no BLUE/RED change, no runtime mutation.
- No DB/secrets mutation.
- No candidate promotion, no automatic capital allocation.
- Offline scoring is decision support only, **not** a trading authorization.
- ``PROMOTE_TO_NEXT_RESEARCH_GATE`` is an advisory label, not an executable action.
- LR remains **NO-GO**. No Live-Go. No Echtgeld-Go.

Scores are advisory research metrics on ``[0.0, 100.0]`` (non-financial), so
``float`` is used deliberately; no monetary value is computed here.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema.validators import validator_for

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = PROJECT_ROOT / "docs" / "contracts"

_PACKET_SCHEMA_PATH = CONTRACTS_DIR / "profitability_evidence_packet.v1.schema.json"
_REPORT_SCHEMA_PATH = CONTRACTS_DIR / "profitability_league_table_report.v1.schema.json"

FORMULA_REF = "docs/strategy/CDB_PROFITABILITY_LEAGUE_SCORING_FORMULA_V1.md"
SCORER_VERSION = "profitability_league_scorer.v1"
DEFAULT_MODEL_ID = "pltm-profitability-scoring-v1"

# Default weights (MUST sum to 100.0) — mirror Formula v1 / fixture
# ``pltm-profitability-scoring-v1``.
_WEIGHTS: dict[str, float] = {
    "NET_ECONOMICS": 25.0,
    "ROBUSTNESS": 20.0,
    "EVIDENCE_COMPLETENESS": 15.0,
    "SAFETY_STATUS": 15.0,
    "PAPER_REFERENCE_CONFIDENCE": 15.0,
    "EXECUTION_REALISM": 10.0,
}
_DIMENSION_ORDER: tuple[str, ...] = (
    "NET_ECONOMICS",
    "ROBUSTNESS",
    "EVIDENCE_COMPLETENESS",
    "SAFETY_STATUS",
    "PAPER_REFERENCE_CONFIDENCE",
    "EXECUTION_REALISM",
)

# Recommendations that constitute a hard safety gate (sentinel + not rankable).
_SAFETY_HARD_RECOMMENDATIONS = frozenset({"UNSAFE", "REJECT", "NO_RECOMMENDATION"})


class ProfitabilityLeagueScorerError(ValueError):
    """Raised when scoring cannot complete safely."""


@dataclass(frozen=True, slots=True)
class DimensionScore:
    dimension: str
    score: float


@dataclass(frozen=True, slots=True)
class CandidateScore:
    candidate_id: str
    total_score: float
    ranking_ready: bool
    net_return: float | None
    dimension_scores: tuple[DimensionScore, ...]
    recommendation: str
    limitations_summary: tuple[str, ...]
    sentinel_mode: bool
    hard_gate_failures: tuple[str, ...]
    safety_blocked: bool
    max_drawdown: float | None

    def dimension_map(self) -> dict[str, float]:
        return {item.dimension: item.score for item in self.dimension_scores}


# --------------------------------------------------------------------------- #
# Numeric helpers
# --------------------------------------------------------------------------- #


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _round1(value: float) -> float:
    return round(float(value), 1)


def _as_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _packet_max_drawdown(pep: Mapping[str, Any]) -> float | None:
    packet_level = _as_number(pep.get("max_drawdown"))
    if packet_level is not None:
        return packet_level
    scenarios = pep.get("scenario_results") or []
    values: list[float] = []
    for scenario in scenarios:
        if isinstance(scenario, Mapping):
            candidate = _as_number(scenario.get("max_drawdown"))
            if candidate is not None:
                values.append(candidate)
    return max(values) if values else None


# --------------------------------------------------------------------------- #
# Hard gates (Formula v1 "Global Fail-Closed Rules", rows 1–9 + row 10)
# --------------------------------------------------------------------------- #


def hard_gate_failures(
    pep: Mapping[str, Any],
    *,
    dataset_quality_verdict: str | None = None,
) -> tuple[str, ...]:
    """Return human-readable reasons why ``ranking_ready`` MUST be ``false``.

    A non-empty result means sentinel mode: all scores are ``0.0``.
    """

    reasons: list[str] = []

    net_return = _as_number(pep.get("net_return"))
    if pep.get("net_return") is None or net_return is None:
        reasons.append("net_return is null")  # row 1

    if pep.get("fees") is None or _as_number(pep.get("fees")) is None:
        reasons.append("fees is null (net economics unassessable)")  # row 2

    replay_status = pep.get("replay_vs_paper_status")
    if replay_status in ("not_run", "missing_reference"):
        reasons.append(f"replay_vs_paper_status={replay_status}")  # row 3

    drift = pep.get("simulator_drift")
    if drift in ("not_assessed", "unusable"):
        reasons.append(f"simulator_drift={drift}")  # row 4

    regime = pep.get("regime_scorecard")
    regime_status = regime.get("status") if isinstance(regime, Mapping) else None
    if regime_status != "ok":
        reasons.append(f"regime_scorecard.status={regime_status!r} (not ok)")  # row 5

    recommendation = pep.get("recommendation")
    if recommendation in _SAFETY_HARD_RECOMMENDATIONS:
        reasons.append(f"recommendation={recommendation}")  # row 6

    trade_count = _as_int(pep.get("trade_count"))
    if trade_count is None or trade_count < 10:
        reasons.append(f"trade_count={pep.get('trade_count')!r} (< 10)")  # row 7

    scenarios = pep.get("scenario_results") or []
    ran = [
        scenario
        for scenario in scenarios
        if isinstance(scenario, Mapping) and scenario.get("status") != "NOT_RUN"
    ]
    if len(ran) < 3:
        reasons.append(
            f"scenario_results with status!=NOT_RUN = {len(ran)} (< 3)"
        )  # row 8

    if dataset_quality_verdict == "BLOCKED":
        reasons.append("dataset quality verdict=BLOCKED")  # row 9

    return tuple(reasons)


def _economics_gate_passes(pep: Mapping[str, Any]) -> bool:
    """Aggregate economics gate: net economics strictly positive."""

    net_return = _as_number(pep.get("net_return"))
    return net_return is not None and net_return > 0.0


def _is_safety_blocked(pep: Mapping[str, Any]) -> bool:
    recommendation = pep.get("recommendation")
    if recommendation in ("UNSAFE", "REJECT"):
        return True
    kill_events = _as_int(pep.get("kill_switch_events"))
    return kill_events is not None and kill_events > 0


# --------------------------------------------------------------------------- #
# Dimension scorers (Formula v1 "Dimension Specifications")
# --------------------------------------------------------------------------- #


def score_net_economics(pep: Mapping[str, Any]) -> float:
    net_return = _as_number(pep.get("net_return"))
    gross_return = _as_number(pep.get("gross_return"))
    if net_return is None or gross_return is None:
        return 0.0

    neutral = 50.0
    if net_return <= 0:
        score = _clamp(neutral + net_return * 250.0, 0.0, 49.9)
    else:
        score = _clamp(neutral + net_return * 200.0, 50.0, 100.0)

    max_drawdown = _packet_max_drawdown(pep)
    if max_drawdown is not None and max_drawdown > 0.20:
        score = _clamp(score - 15.0, 0.0, 100.0)
    elif max_drawdown is not None and max_drawdown > 0.10:
        score = _clamp(score - 8.0, 0.0, 100.0)
    return score


def score_robustness(pep: Mapping[str, Any]) -> float:
    scenarios = [
        scenario
        for scenario in (pep.get("scenario_results") or [])
        if isinstance(scenario, Mapping)
    ]
    if not scenarios:
        return 0.0
    if all(scenario.get("status") == "NOT_RUN" for scenario in scenarios):
        return 0.0

    score = 100.0
    for scenario in scenarios:
        status = scenario.get("status")
        if status == "FAIL":
            score -= 8.0
        if status == "BLOCKED":
            score -= 12.0
        if status == "WARNING":
            score -= 4.0
        notes = scenario.get("notes") or ""
        if "gate_result=FAIL" in notes:
            score -= 3.0
        scenario_net = _as_number(scenario.get("net_return"))
        if scenario_net is not None and scenario_net < -0.05:
            score -= 2.0

    loss_streak = _as_int(pep.get("loss_streak"))
    if loss_streak is not None:
        if loss_streak >= 6:
            score -= 10.0
        elif loss_streak >= 4:
            score -= 5.0

    trade_count = _as_int(pep.get("trade_count"))
    if trade_count is not None and trade_count < 10:
        score -= 15.0

    return _clamp(score, 0.0, 100.0)


def score_evidence_completeness(pep: Mapping[str, Any]) -> float:
    score = 100.0
    if pep.get("profit_factor") is None:
        score -= 8.0
    if pep.get("avg_win") is None:
        score -= 6.0
    if pep.get("avg_loss") is None:
        score -= 6.0
    if pep.get("max_drawdown") is None:
        score -= 6.0

    regime = pep.get("regime_scorecard")
    regime_status = regime.get("status") if isinstance(regime, Mapping) else None
    if regime_status != "ok":
        score -= 20.0

    source_run_refs = pep.get("source_run_refs") or []
    if len(source_run_refs) < 5:
        score -= 10.0

    missing_evidence = pep.get("missing_evidence")
    if missing_evidence:
        score -= 5.0 * min(len(missing_evidence), 4)

    score = _clamp(score, 0.0, 100.0)
    if regime_status == "unavailable":
        score = min(score, 30.0)
    return score


def score_safety_status(pep: Mapping[str, Any]) -> float:
    base_by_recommendation = {
        "UNSAFE": 0.0,
        "REJECT": 10.0,
        "NO_RECOMMENDATION": 15.0,
        "PARK": 45.0,
        "PROMOTE_TO_NEXT_RESEARCH_GATE": 70.0,
    }
    base = base_by_recommendation.get(pep.get("recommendation"), 0.0)

    risk_blocks = _as_int(pep.get("risk_blocks"))
    if risk_blocks is not None and risk_blocks > 0:
        base = min(base, 25.0)

    kill_events = _as_int(pep.get("kill_switch_events"))
    if kill_events is not None and kill_events > 0:
        base = min(base, 10.0)

    if not pep.get("safety_boundaries"):
        base = min(base, 30.0)

    return _clamp(base, 0.0, 100.0)


def score_paper_reference_confidence(pep: Mapping[str, Any]) -> float:
    base_by_status = {
        "aligned": 90.0,
        "pessimistic_drift": 75.0,
        "optimistic_drift": 40.0,
        "ambiguous_drift": 25.0,
        "missing_reference": 0.0,
        "not_run": 0.0,
    }
    base = base_by_status.get(pep.get("replay_vs_paper_status"), 0.0)

    drift = pep.get("simulator_drift")
    if drift == "unusable":
        return 0.0
    if drift == "not_assessed":
        return min(_clamp(base, 0.0, 100.0), 20.0)

    if drift == "none":
        adjusted = base + 5.0
    elif drift == "pessimistic":
        adjusted = base + 0.0
    elif drift == "optimistic":
        adjusted = base - 10.0
    elif drift == "ambiguous":
        adjusted = base - 15.0
    else:
        adjusted = base

    return _clamp(adjusted, 0.0, 100.0)


def score_execution_realism(pep: Mapping[str, Any]) -> float:
    fees = _as_number(pep.get("fees"))
    if pep.get("fees") is None or fees is None:
        return 0.0

    score = 0.0
    if fees >= 0:
        score = 40.0

    spread_cost = _as_number(pep.get("spread_cost"))
    if spread_cost is not None and spread_cost > 0:
        score += 25.0
    elif spread_cost is not None and spread_cost == 0:
        score += 5.0

    slippage_cost = _as_number(pep.get("slippage_cost"))
    if slippage_cost is not None and slippage_cost > 0:
        score += 25.0
    elif slippage_cost is not None and slippage_cost == 0:
        score += 5.0

    gross_return = _as_number(pep.get("gross_return"))
    net_return = _as_number(pep.get("net_return"))
    if gross_return is not None and net_return is not None:
        if abs(gross_return - net_return) < 1e-9 and fees == 0:
            score = min(score, 15.0)

    score = _clamp(score, 0.0, 100.0)
    if spread_cost is None and slippage_cost is None:
        score = min(score, 40.0)
    return score


_DIMENSION_SCORERS = {
    "NET_ECONOMICS": score_net_economics,
    "ROBUSTNESS": score_robustness,
    "EVIDENCE_COMPLETENESS": score_evidence_completeness,
    "SAFETY_STATUS": score_safety_status,
    "PAPER_REFERENCE_CONFIDENCE": score_paper_reference_confidence,
    "EXECUTION_REALISM": score_execution_realism,
}


# --------------------------------------------------------------------------- #
# Candidate + report assembly
# --------------------------------------------------------------------------- #


def score_candidate(
    pep: Mapping[str, Any],
    *,
    dataset_quality_verdict: str | None = None,
) -> CandidateScore:
    """Score a single candidate PEP per Formula v1 (fail-closed)."""

    if not isinstance(pep, Mapping):
        raise ProfitabilityLeagueScorerError("PEP must be a JSON object / mapping")

    candidate_id = pep.get("candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        raise ProfitabilityLeagueScorerError(
            "PEP candidate_id must be a non-empty string"
        )

    recommendation = pep.get("recommendation")
    if not isinstance(recommendation, str) or not recommendation.strip():
        raise ProfitabilityLeagueScorerError(
            "PEP recommendation must be a non-empty string"
        )

    failures = hard_gate_failures(pep, dataset_quality_verdict=dataset_quality_verdict)
    sentinel_mode = bool(failures)
    net_return = _as_number(pep.get("net_return"))
    max_drawdown = _packet_max_drawdown(pep)
    limitations: list[str] = []

    if sentinel_mode:
        dimension_scores = tuple(
            DimensionScore(dimension=name, score=0.0) for name in _DIMENSION_ORDER
        )
        total_score = 0.0
        ranking_ready = False
        limitations.append(
            "Sentinel mode: hard gate(s) force ranking_ready=false and zero scores: "
            + "; ".join(failures)
            + "."
        )
        limitations.append(
            f"Formula ref: {FORMULA_REF} — zero scores are not performance metrics."
        )
    else:
        raw = {name: _DIMENSION_SCORERS[name](pep) for name in _DIMENSION_ORDER}
        dimension_scores = tuple(
            DimensionScore(dimension=name, score=_round1(raw[name]))
            for name in _DIMENSION_ORDER
        )
        total_score = _round1(
            sum(raw[name] * _WEIGHTS[name] / 100.0 for name in _DIMENSION_ORDER)
        )
        if recommendation == "PROMOTE_TO_NEXT_RESEARCH_GATE":
            ranking_ready = True
        elif recommendation == "PARK":
            ranking_ready = _economics_gate_passes(pep)
            if not ranking_ready:
                limitations.append(
                    "PARK research hold: aggregate economics gate not passed "
                    "(net_return<=0); computed scores are advisory, not promotion."
                )
        else:
            ranking_ready = False

    if recommendation == "PARK":
        limitations.append(
            "PARK is a research hold; not promotion, not paper-ready, not live-ready."
        )
    if ranking_ready:
        limitations.append(
            "ranking_ready reflects comparison eligibility only, not promotion "
            "or capital authorization."
        )
    limitations.append(
        "LR remains NO-GO. Offline scoring is decision support only, "
        "not a trading authorization."
    )

    return CandidateScore(
        candidate_id=candidate_id.strip(),
        total_score=total_score,
        ranking_ready=ranking_ready,
        net_return=net_return,
        dimension_scores=dimension_scores,
        recommendation=recommendation.strip(),
        limitations_summary=tuple(limitations),
        sentinel_mode=sentinel_mode,
        hard_gate_failures=failures,
        safety_blocked=_is_safety_blocked(pep),
        max_drawdown=max_drawdown,
    )


def _ranking_sort_key(score: CandidateScore) -> tuple[Any, ...]:
    dims = score.dimension_map()
    return (
        -score.total_score,
        -dims.get("PAPER_REFERENCE_CONFIDENCE", 0.0),
        -dims.get("ROBUSTNESS", 0.0),
        score.max_drawdown if score.max_drawdown is not None else float("inf"),
        -dims.get("EVIDENCE_COMPLETENESS", 0.0),
        len(score.limitations_summary),
        score.candidate_id,
    )


def _table_status(scores: Sequence[CandidateScore]) -> str:
    if not scores:
        return "BLOCKED"
    if all(score.ranking_ready for score in scores):
        return "COMPLETE"
    if all(score.safety_blocked for score in scores):
        return "BLOCKED"
    return "PARTIAL"


def _generated_at_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def build_league_table_report(
    peps: Sequence[Mapping[str, Any]],
    *,
    report_id: str | None = None,
    model_id: str = DEFAULT_MODEL_ID,
    generated_at: str | None = None,
    dataset_quality_verdicts: Mapping[str, str] | None = None,
    validate: bool = True,
) -> dict[str, Any]:
    """Build a ``profitability_league_table_report.v1`` report from PEPs.

    Ranking is score-derived only among ``ranking_ready=true`` candidates;
    ``ranking_ready=false`` candidates are visibility-ordered (lexicographic).
    """

    if not peps:
        raise ProfitabilityLeagueScorerError(
            "at least one PEP is required (report requires >= 1 candidate)"
        )

    verdicts = dataset_quality_verdicts or {}
    scores = [
        score_candidate(
            pep,
            dataset_quality_verdict=(
                verdicts.get(pep.get("candidate_id"))
                if isinstance(pep, Mapping)
                else None
            ),
        )
        for pep in peps
    ]

    ready = sorted(
        (score for score in scores if score.ranking_ready), key=_ranking_sort_key
    )
    not_ready = sorted(
        (score for score in scores if not score.ranking_ready),
        key=lambda score: score.candidate_id,
    )
    ordered = list(ready) + list(not_ready)

    candidate_rankings = []
    for rank, score in enumerate(ordered, start=1):
        candidate_rankings.append(
            {
                "candidate_id": score.candidate_id,
                "rank": rank,
                "total_score": score.total_score,
                "ranking_ready": score.ranking_ready,
                "net_return": score.net_return,
                "dimension_scores": [
                    {"dimension": item.dimension, "score": item.score}
                    for item in score.dimension_scores
                ],
                "recommendation": score.recommendation,
                "limitations_summary": list(score.limitations_summary),
            }
        )

    report = {
        "schema_version": "profitability_league_table_report.v1",
        "report_id": report_id or _default_report_id(),
        "model_id": model_id,
        "generated_at": generated_at or _generated_at_now(),
        "table_status": _table_status(scores),
        "candidate_rankings": candidate_rankings,
        "limitations": [
            f"Offline Strategy League scorer v1 ({SCORER_VERSION}) output per "
            f"{FORMULA_REF} — advisory research evidence only.",
            "Scores do not authorize promotion, paper capital, or live capital. "
            "LR remains NO-GO.",
            "ranking_ready=false candidates are visibility-ordered only; "
            "total_score must not be used to order them.",
        ],
    }

    if validate:
        _validate_report(report)
    return report


def _default_report_id() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"pltr-offline-scorer-{stamp}"


# --------------------------------------------------------------------------- #
# Schema validation (fail-closed)
# --------------------------------------------------------------------------- #


def _load_schema(schema_path: Path) -> dict[str, Any]:
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ProfitabilityLeagueScorerError(
            f"Failed to read schema {schema_path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ProfitabilityLeagueScorerError(
            f"Invalid JSON in schema {schema_path}: {exc}"
        ) from exc


def _validate_against_schema(
    payload: Mapping[str, Any], *, schema_path: Path, artifact_role: str
) -> None:
    schema = _load_schema(schema_path)
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda err: (
            ".".join(str(part) for part in err.path),
            err.message,
        ),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "<root>"
        raise ProfitabilityLeagueScorerError(
            f"Schema mismatch for {artifact_role} at {location}: {first.message}"
        )


def _validate_report(report: Mapping[str, Any]) -> None:
    _validate_against_schema(
        report, schema_path=_REPORT_SCHEMA_PATH, artifact_role="league_table_report"
    )


def _read_pep_file(path: Path, *, validate: bool) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ProfitabilityLeagueScorerError(
            f"Failed to read PEP {path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ProfitabilityLeagueScorerError(
            f"Invalid JSON in PEP {path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ProfitabilityLeagueScorerError(f"PEP {path} must be a JSON object")
    if validate:
        _validate_against_schema(
            payload, schema_path=_PACKET_SCHEMA_PATH, artifact_role=f"pep:{path.name}"
        )
    return payload


# --------------------------------------------------------------------------- #
# Read-only CLI (no runtime binding, no DB writes)
# --------------------------------------------------------------------------- #


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Offline Strategy League scorer v1 (Formula v1). Reads "
            "profitability_evidence_packet.v1 file(s) and emits a "
            "profitability_league_table_report.v1 report. Decision support only; "
            "no runtime, no DB writes, no promotion, no capital allocation."
        )
    )
    parser.add_argument(
        "--pep",
        dest="peps",
        action="append",
        required=True,
        type=Path,
        help="Path to a profitability_evidence_packet.v1 JSON file (repeatable).",
    )
    parser.add_argument("--report-id", default=None)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--generated-at-utc", default=None)
    parser.add_argument(
        "--out-json",
        type=Path,
        default=None,
        help="Optional output path for the report JSON. Defaults to stdout.",
    )
    parser.add_argument(
        "--no-validate-input",
        action="store_true",
        help="Skip PEP schema validation (report output is always validated).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_argument_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 1

    try:
        peps = [
            _read_pep_file(path, validate=not args.no_validate_input)
            for path in args.peps
        ]
        report = build_league_table_report(
            peps,
            report_id=args.report_id,
            model_id=args.model_id,
            generated_at=args.generated_at_utc,
        )
        serialized = json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True)
        if args.out_json is not None:
            args.out_json.parent.mkdir(parents=True, exist_ok=True)
            args.out_json.write_text(serialized + "\n", encoding="utf-8")
    except ProfitabilityLeagueScorerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.out_json is not None:
        print(
            "OK: league table report written "
            f"(report_id={report['report_id']}, table_status={report['table_status']}, "
            f"candidates={len(report['candidate_rankings'])})"
        )
    else:
        print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
