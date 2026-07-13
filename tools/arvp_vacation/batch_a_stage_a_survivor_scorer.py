"""Batch-A Stage-A survivor gate scorer (#4032).

Evaluates historical development-screening gates for ``STAGE_A_SURVIVOR`` tier.
Uses the versioned ``batch_a_stage_a_gate_contract.v1`` — **not**
``profitability_league_scorer.hard_gate_failures``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from tools.arvp_vacation.batch_a_gate_common import (
    STAGE_A_GATE_CONTRACT_PATH,
    BatchAGateError,
    compute_gate_contract_sha256,
    gate_result,
    load_json_contract,
    max_of_field,
    median_of_field,
    positive_share,
    profit_factor_passes_gate,
    record_is_rankable,
    sum_of_field,
)
from tools.arvp_vacation.metric_contract import metric_is_missing
from tools.market_data.development_window_selector import (
    LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
)

STATUS_SURVIVOR = "STAGE_A_SURVIVOR"
STATUS_REJECTED = "REJECTED"
STATUS_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"

BASELINE_SCENARIO = "baseline"
PESSIMISTIC_SCENARIO = "pessimistic_execution"


@dataclass(frozen=True, slots=True)
class StageASurvivorResult:
    candidate_id: str
    status: str
    gate_results: dict[str, Any]
    gate_contract_sha256: str
    coverage: dict[str, Any]


def load_stage_a_gate_contract(
    path: Path | None = None,
) -> dict[str, Any]:
    return load_json_contract(path or STAGE_A_GATE_CONTRACT_PATH)


def _index_records(
    records: Sequence[Mapping[str, Any]],
    *,
    candidate_id: str,
) -> dict[str, dict[str, Mapping[str, Any]]]:
    indexed: dict[str, dict[str, Mapping[str, Any]]] = {}
    for record in records:
        record_candidate = str(record.get("strategy_id") or record.get("candidate_id") or "")
        if record_candidate != candidate_id:
            continue
        window_id = str(record.get("window_id") or "")
        scenario = str(
            record.get("scenario") or record.get("scenario_id") or ""
        )
        indexed.setdefault(window_id, {})[scenario] = record
    return indexed


def _technical_pass(
    record: Mapping[str, Any],
    *,
    blocked_verdicts: frozenset[str],
    job_metadata: Mapping[str, Mapping[str, Any]] | None,
) -> bool:
    job_id = str(record.get("job_id") or "")
    meta = (job_metadata or {}).get(job_id, {})
    status = str(meta.get("job_status") or record.get("job_status") or "completed")
    if status != "completed":
        return False
    verdict = str(
        meta.get("dataset_quality_verdict")
        or record.get("dataset_quality_verdict")
        or "PASS"
    )
    if verdict in blocked_verdicts:
        return False
    flags = record.get("data_quality_flags") or []
    if isinstance(flags, list):
        for flag in flags:
            if str(flag).startswith("missing_"):
                return False
    return True


def _evaluable_pair(
    pair: Mapping[str, Mapping[str, Any]],
    *,
    blocked_verdicts: frozenset[str],
    job_metadata: Mapping[str, Mapping[str, Any]] | None,
) -> bool:
    baseline = pair.get(BASELINE_SCENARIO)
    pessimistic = pair.get(PESSIMISTIC_SCENARIO)
    if baseline is None or pessimistic is None:
        return False
    if not _technical_pass(baseline, blocked_verdicts=blocked_verdicts, job_metadata=job_metadata):
        return False
    if not _technical_pass(
        pessimistic, blocked_verdicts=blocked_verdicts, job_metadata=job_metadata
    ):
        return False
    return record_is_rankable(baseline) and record_is_rankable(pessimistic)


def _paired_evaluable_windows(
    indexed: dict[str, dict[str, Mapping[str, Any]]],
    *,
    development_windows: Sequence[str],
    blocked_verdicts: frozenset[str],
    job_metadata: Mapping[str, Mapping[str, Any]] | None,
) -> list[tuple[str, dict[str, Mapping[str, Any]]]]:
    matched: list[tuple[str, dict[str, Mapping[str, Any]]]] = []
    for window_id in development_windows:
        pair = indexed.get(window_id)
        if pair is None:
            continue
        if _evaluable_pair(
            pair,
            blocked_verdicts=blocked_verdicts,
            job_metadata=job_metadata,
        ):
            matched.append((window_id, pair))
    return matched


def _coverage_summary(
    indexed: dict[str, dict[str, Mapping[str, Any]]],
    *,
    development_windows: Sequence[str],
    blocked_verdicts: frozenset[str],
    job_metadata: Mapping[str, Mapping[str, Any]] | None,
    development_window_count: int,
) -> dict[str, Any]:
    baseline_rankable = 0
    pessimistic_rankable = 0
    paired_evaluable = 0
    missing_pairs = 0
    for window_id in development_windows:
        pair = indexed.get(window_id)
        if pair is None or BASELINE_SCENARIO not in pair or PESSIMISTIC_SCENARIO not in pair:
            missing_pairs += 1
            continue
        if record_is_rankable(pair[BASELINE_SCENARIO]):
            baseline_rankable += 1
        if record_is_rankable(pair[PESSIMISTIC_SCENARIO]):
            pessimistic_rankable += 1
        if _evaluable_pair(
            pair,
            blocked_verdicts=blocked_verdicts,
            job_metadata=job_metadata,
        ):
            paired_evaluable += 1

    denom = development_window_count
    return {
        "development_window_count": denom,
        "baseline_rankable_count": baseline_rankable,
        "pessimistic_rankable_count": pessimistic_rankable,
        "paired_evaluable_count": paired_evaluable,
        "missing_pair_count": missing_pairs,
        "baseline_rankable_share": baseline_rankable / denom,
        "pessimistic_rankable_share": pessimistic_rankable / denom,
        "paired_evaluable_share": paired_evaluable / denom,
    }


def _rows_for_scope(
    scope: str,
    *,
    indexed: dict[str, dict[str, Mapping[str, Any]]],
    development_windows: Sequence[str],
    blocked_verdicts: frozenset[str],
    job_metadata: Mapping[str, Mapping[str, Any]] | None,
) -> list[Mapping[str, Any]]:
    if scope == "all_records":
        return [record for pair in indexed.values() for record in pair.values()]

    if scope == "baseline_rankable":
        rows: list[Mapping[str, Any]] = []
        for window_id in development_windows:
            pair = indexed.get(window_id) or {}
            baseline = pair.get(BASELINE_SCENARIO)
            if baseline and record_is_rankable(baseline):
                rows.append(baseline)
        return rows

    if scope == "pessimistic_rankable":
        rows = []
        for window_id in development_windows:
            pair = indexed.get(window_id) or {}
            pessimistic = pair.get(PESSIMISTIC_SCENARIO)
            if pessimistic and record_is_rankable(pessimistic):
                rows.append(pessimistic)
        return rows

    paired = _paired_evaluable_windows(
        indexed,
        development_windows=development_windows,
        blocked_verdicts=blocked_verdicts,
        job_metadata=job_metadata,
    )
    if scope == "paired_baseline_rankable":
        return [pair[BASELINE_SCENARIO] for _, pair in paired]
    if scope == "paired_pessimistic_rankable":
        return [pair[PESSIMISTIC_SCENARIO] for _, pair in paired]
    if scope == "paired_baseline_pessimistic_rankable":
        rows = []
        for _, pair in paired:
            rows.append(pair[BASELINE_SCENARIO])
            rows.append(pair[PESSIMISTIC_SCENARIO])
        return rows

    raise BatchAGateError(f"unknown gate scope: {scope!r}")


def score_stage_a_candidate(
    *,
    candidate_id: str,
    records: Sequence[Mapping[str, Any]],
    development_window_ids: Sequence[str] | None = None,
    gate_contract: Mapping[str, Any] | None = None,
    job_metadata: Mapping[str, Mapping[str, Any]] | None = None,
) -> StageASurvivorResult:
    contract = dict(gate_contract or load_stage_a_gate_contract())
    contract_sha = compute_gate_contract_sha256(contract)
    development_windows = tuple(
        development_window_ids or LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS
    )
    development_window_count = int(
        contract.get("development_window_count", len(development_windows))
    )
    blocked = frozenset(str(v) for v in contract.get("blocked_quality_verdicts") or [])

    indexed = _index_records(records, candidate_id=candidate_id)
    coverage = _coverage_summary(
        indexed,
        development_windows=development_windows,
        blocked_verdicts=blocked,
        job_metadata=job_metadata,
        development_window_count=development_window_count,
    )

    gate_results: dict[str, Any] = {"coverage": coverage, "gates": {}}
    insufficient = False
    required_fail = False
    skip_flags: list[str] = []

    for gate in contract.get("gates") or []:
        if not isinstance(gate, Mapping):
            raise BatchAGateError("gate entry must be mapping")
        gate_id = str(gate["gate_id"])
        scope = str(gate["scope"])
        operator = str(gate["operator"])
        missing_semantics = str(gate.get("missing_semantics", "fail"))
        threshold = gate.get("value")
        field = str(gate.get("field") or "")

        if gate_id in {"G-T01", "G-T02"}:
            rows = _rows_for_scope(
                "all_records",
                indexed=indexed,
                development_windows=development_windows,
                blocked_verdicts=blocked,
                job_metadata=job_metadata,
            )
            passed = bool(rows) and all(
                _technical_pass(
                    row,
                    blocked_verdicts=blocked,
                    job_metadata=job_metadata,
                )
                for row in rows
            )
            gate_results["gates"][gate_id] = gate_result(
                gate_id, passed=passed, observed=len(rows), threshold=threshold
            )
            if not passed and gate.get("required_for_survivor", True):
                required_fail = True
            continue

        if (
            scope in {"paired_evaluable", "baseline_rankable", "pessimistic_rankable"}
            and not field
        ):
            if scope == "paired_evaluable":
                observed = coverage["paired_evaluable_share"]
            elif scope == "baseline_rankable":
                observed = coverage["baseline_rankable_share"]
            else:
                observed = coverage["pessimistic_rankable_share"]
            passed = observed is not None and observed >= float(threshold)
            gate_results["gates"][gate_id] = gate_result(
                gate_id,
                passed=passed,
                observed=observed,
                threshold=threshold,
            )
            if not passed:
                if missing_semantics == "insufficient_evidence":
                    insufficient = True
                elif gate.get("required_for_survivor", True):
                    required_fail = True
            continue

        rows = _rows_for_scope(
            scope,
            indexed=indexed,
            development_windows=development_windows,
            blocked_verdicts=blocked,
            job_metadata=job_metadata,
        )

        if operator == "anti_auto_pass":
            baseline_rows = _rows_for_scope(
                "paired_baseline_rankable",
                indexed=indexed,
                development_windows=development_windows,
                blocked_verdicts=blocked,
                job_metadata=job_metadata,
            )
            pessimistic_rows = _rows_for_scope(
                "paired_pessimistic_rankable",
                indexed=indexed,
                development_windows=development_windows,
                blocked_verdicts=blocked,
                job_metadata=job_metadata,
            )
            baseline_median = median_of_field(baseline_rows, "net_pnl_quote")
            pessimistic_median = median_of_field(pessimistic_rows, "net_pnl_quote")
            if baseline_median is None or pessimistic_median is None:
                passed = False
            elif baseline_median <= 0:
                passed = False
            else:
                passed = pessimistic_median > 0
            observed = {
                "baseline_median_net_pnl_quote": baseline_median,
                "pessimistic_median_net_pnl_quote": pessimistic_median,
            }
        elif field == "fee_adjusted_expectancy_r" and operator == "gt":
            if any(not metric_is_missing(row, field) for row in rows):
                observed = median_of_field(rows, field)
                passed = observed is not None and observed > float(threshold)
            else:
                observed = None
                passed = None
                if missing_semantics == "skip_with_flag":
                    skip_flag = str(
                        gate.get("skip_flag") or "fee_adjusted_expectancy_unavailable"
                    )
                    gate_results["gates"][gate_id] = gate_result(
                        gate_id,
                        passed=None,
                        observed=None,
                        threshold=threshold,
                        skipped=True,
                        skip_flag=skip_flag,
                    )
                    skip_flags.append(skip_flag)
                    continue
        elif field == "profit_factor" and operator == "gte":
            observed = median_of_field(rows, field)
            trade_sum = sum_of_field(rows, "closed_trades_total") or 0
            net_median = median_of_field(rows, "net_pnl_quote")
            passed = profit_factor_passes_gate(
                observed,
                threshold=float(threshold),
                net_pnl_positive=net_median is not None and net_median > 0,
                closed_trades_gte=trade_sum,
            )
        elif operator == "gt" and field:
            observed = median_of_field(rows, field)
            passed = observed is not None and observed > float(threshold)
        elif operator == "gte" and field == "closed_trades_total":
            observed = sum_of_field(rows, field)
            passed = observed is not None and observed >= int(threshold)
        elif operator == "lte" and field:
            observed = max_of_field(rows, field)
            passed = observed is not None and observed <= float(threshold)
        elif operator == "positive_share_gte" and field:
            observed = positive_share(rows, field)
            passed = observed is not None and observed >= float(threshold)
        else:
            raise BatchAGateError(f"unsupported gate {gate_id}: {operator}")

        if passed is None:
            if missing_semantics == "insufficient_evidence":
                insufficient = True
            else:
                required_fail = True
            passed = False

        gate_results["gates"][gate_id] = gate_result(
            gate_id,
            passed=passed,
            observed=observed,
            threshold=threshold,
        )
        if not passed and gate.get("required_for_survivor", True):
            required_fail = True

    if skip_flags:
        gate_results["skip_flags"] = skip_flags

    min_paired = float(
        contract["paired_evidence_rules"]["min_paired_evaluable_window_share"]
    )
    if coverage["paired_evaluable_share"] < min_paired:
        insufficient = True

    if insufficient:
        status = STATUS_INSUFFICIENT
    elif required_fail:
        status = STATUS_REJECTED
    else:
        status = STATUS_SURVIVOR

    return StageASurvivorResult(
        candidate_id=candidate_id,
        status=status,
        gate_results=gate_results,
        gate_contract_sha256=contract_sha,
        coverage=coverage,
    )


def score_stage_a_candidates(
    *,
    records: Sequence[Mapping[str, Any]],
    candidate_ids: Sequence[str],
    gate_contract: Mapping[str, Any] | None = None,
    job_metadata: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, StageASurvivorResult]:
    return {
        candidate_id: score_stage_a_candidate(
            candidate_id=candidate_id,
            records=records,
            gate_contract=gate_contract,
            job_metadata=job_metadata,
        )
        for candidate_id in candidate_ids
    }


def result_to_dict(result: StageASurvivorResult) -> dict[str, Any]:
    return {
        "candidate_id": result.candidate_id,
        "status": result.status,
        "gate_contract_sha256": result.gate_contract_sha256,
        "gate_results": result.gate_results,
        "coverage": result.coverage,
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Batch-A Stage-A survivor scorer")
    parser.add_argument("--metrics", required=True, help="arvp_strategy_metrics.v1 JSON")
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--output", help="Write JSON result to path")
    args = parser.parse_args(argv)

    payload = json.loads(Path(args.metrics).read_text(encoding="utf-8"))
    records = payload.get("records") or []
    result = score_stage_a_candidate(
        candidate_id=args.candidate_id,
        records=records,
    )
    output = result_to_dict(result)
    text = json.dumps(output, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
