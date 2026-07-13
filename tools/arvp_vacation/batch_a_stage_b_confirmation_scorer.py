"""Batch-A Stage-B historical confirmation scorer (#4032 / WP4).

Evaluates ``HISTORICALLY_CONFIRMED_CANDIDATE`` tier using monthly primary slices
only. Quarterly/yearly windows are corroborative diagnostics and never enter
primary combined medians or sample-size sums (GO amendment A2).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from tools.arvp_vacation.batch_a_gate_common import (
    STAGE_B_CONFIRMATION_CONTRACT_PATH,
    BatchAGateError,
    compute_gate_contract_sha256,
    gate_result,
    load_json_contract,
    median_of_field,
    positive_share,
    record_is_rankable,
)
from tools.market_data.stage_b_window_selector import (
    EXPECTED_MONTHLY_OOS,
    EXPECTED_MONTHLY_VALIDATION,
    EXPECTED_STRESS,
)

STATUS_CONFIRMED = "HISTORICALLY_CONFIRMED_CANDIDATE"
STATUS_REJECTED = "REJECTED"
STATUS_PARTIAL = "PARTIAL_EVIDENCE"

PRIMARY_SLICES = (
    "validation_monthly",
    "out_of_sample_monthly",
    "stress",
)
CORROBORATIVE_SLICES = (
    "corroborative_quarterly",
    "corroborative_yearly",
)


@dataclass(frozen=True, slots=True)
class StageBConfirmationResult:
    candidate_id: str
    status: str
    gate_results: dict[str, Any]
    gate_contract_sha256: str
    slice_coverage: dict[str, Any]
    corroborative_summary: dict[str, Any]


def load_stage_b_confirmation_contract(
    path: Path | None = None,
) -> dict[str, Any]:
    return load_json_contract(path or STAGE_B_CONFIRMATION_CONTRACT_PATH)


def _slice_for_record(record: Mapping[str, Any]) -> str:
    stored = record.get("stage_b_slice")
    if isinstance(stored, str) and stored.strip():
        return stored.strip()
    purpose = str(record.get("purpose") or "")
    overlap = str(record.get("window_class") or record.get("overlap_class") or "")
    if purpose == "validation" and overlap == "monthly":
        return "validation_monthly"
    if purpose == "out_of_sample" and overlap == "monthly":
        return "out_of_sample_monthly"
    if purpose == "stress" and overlap == "stress":
        return "stress"
    if overlap == "quarterly":
        return "corroborative_quarterly"
    if overlap == "yearly":
        return "corroborative_yearly"
    return f"{purpose}_{overlap}"


def _records_for_candidate(
    records: Sequence[Mapping[str, Any]],
    *,
    candidate_id: str,
) -> list[Mapping[str, Any]]:
    matched: list[Mapping[str, Any]] = []
    for record in records:
        record_candidate = str(record.get("strategy_id") or record.get("candidate_id") or "")
        if record_candidate == candidate_id:
            matched.append(record)
    return matched


def _slice_records(
    records: Sequence[Mapping[str, Any]],
    slice_name: str,
) -> list[Mapping[str, Any]]:
    return [record for record in records if _slice_for_record(record) == slice_name]


def _expected_count_for_slice(slice_name: str) -> int:
    if slice_name == "validation_monthly":
        return EXPECTED_MONTHLY_VALIDATION
    if slice_name == "out_of_sample_monthly":
        return EXPECTED_MONTHLY_OOS
    if slice_name == "stress":
        return EXPECTED_STRESS
    return 0


def _slice_coverage(
    records: Sequence[Mapping[str, Any]],
    slice_name: str,
) -> dict[str, Any]:
    rows = _slice_records(records, slice_name)
    rankable = [row for row in rows if record_is_rankable(row)]
    expected = _expected_count_for_slice(slice_name)
    return {
        "slice": slice_name,
        "record_count": len(rows),
        "rankable_count": len(rankable),
        "expected_window_count": expected,
        "rankable_share": (len(rankable) / expected) if expected else None,
    }


def _corroborative_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for slice_name in CORROBORATIVE_SLICES:
        rows = _slice_records(records, slice_name)
        rankable = [row for row in rows if record_is_rankable(row)]
        summary[slice_name] = {
            "record_count": len(rows),
            "rankable_count": len(rankable),
            "median_net_pnl_quote": median_of_field(rankable, "net_pnl_quote"),
            "included_in_primary_confirmation": False,
        }
    return summary


def _evaluate_gate(
    gate: Mapping[str, Any],
    *,
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    gate_id = str(gate["gate_id"])
    slice_name = str(gate["slice"])
    operator = str(gate["operator"])
    threshold = gate.get("value")
    field = str(gate.get("field") or "")

    rows = _slice_records(records, slice_name)
    rankable = [row for row in rows if record_is_rankable(row)]
    expected = _expected_count_for_slice(slice_name)

    if operator == "rankable_share_gte":
        observed = (len(rankable) / expected) if expected else None
        passed = observed is not None and observed >= float(threshold)
        return gate_result(
            gate_id,
            passed=passed,
            observed=observed,
            threshold=threshold,
            detail=f"slice={slice_name}",
        )

    if operator == "median_gt" and field:
        observed = median_of_field(rankable, field)
        passed = observed is not None and observed > float(threshold)
        return gate_result(
            gate_id,
            passed=passed,
            observed=observed,
            threshold=threshold,
            detail=f"slice={slice_name}",
        )

    if operator == "positive_share_gte" and field:
        observed = positive_share(rankable, field)
        passed = observed is not None and observed >= float(threshold)
        return gate_result(
            gate_id,
            passed=passed,
            observed=observed,
            threshold=threshold,
            detail=f"slice={slice_name}",
        )

    raise BatchAGateError(f"unsupported Stage-B gate {gate_id}: {operator}")


def score_stage_b_candidate(
    *,
    candidate_id: str,
    records: Sequence[Mapping[str, Any]],
    gate_contract: Mapping[str, Any] | None = None,
) -> StageBConfirmationResult:
    contract = dict(gate_contract or load_stage_b_confirmation_contract())
    contract_sha = compute_gate_contract_sha256(contract)
    candidate_records = _records_for_candidate(records, candidate_id=candidate_id)

    slice_coverage = {
        slice_name: _slice_coverage(candidate_records, slice_name)
        for slice_name in PRIMARY_SLICES
    }
    corroborative = _corroborative_summary(candidate_records)

    gate_results: dict[str, Any] = {
        "coverage": slice_coverage,
        "corroborative": corroborative,
        "gates": {},
    }

    required_gate_ids = list(
        contract.get("verdict_logic", {}).get("historically_confirmed_requires") or []
    )
    partial = False
    required_fail = False
    pass_count = 0

    for gate in contract.get("gates") or []:
        if not isinstance(gate, Mapping):
            raise BatchAGateError("gate entry must be mapping")
        gate_id = str(gate["gate_id"])
        result = _evaluate_gate(gate, records=candidate_records)
        gate_results["gates"][gate_id] = result
        passed = result.get("passed")
        if passed is True:
            pass_count += 1
        elif passed is False:
            missing_semantics = str(gate.get("missing_semantics", "fail"))
            if missing_semantics == "partial_evidence":
                partial = True
            if gate_id in required_gate_ids:
                required_fail = True

    # A2: quarterly/yearly must not influence primary combined median
    primary_rows = []
    for slice_name in PRIMARY_SLICES:
        primary_rows.extend(
            row
            for row in _slice_records(candidate_records, slice_name)
            if record_is_rankable(row)
        )
    combined_primary_median = median_of_field(primary_rows, "net_pnl_quote")
    corroborative_rows = []
    for slice_name in CORROBORATIVE_SLICES:
        corroborative_rows.extend(
            row
            for row in _slice_records(candidate_records, slice_name)
            if record_is_rankable(row)
        )
    corroborative_median = median_of_field(corroborative_rows, "net_pnl_quote")
    gate_results["primary_aggregation"] = {
        "primary_monthly_stress_rankable_count": len(primary_rows),
        "primary_combined_median_net_pnl_quote": combined_primary_median,
        "corroborative_rankable_count": len(corroborative_rows),
        "corroborative_median_net_pnl_quote": corroborative_median,
        "quarterly_yearly_in_primary_median": False,
    }

    if pass_count == len(required_gate_ids) and not required_fail:
        status = STATUS_CONFIRMED
    elif partial or (0 < pass_count < len(required_gate_ids)):
        status = STATUS_PARTIAL
    else:
        status = STATUS_REJECTED

    return StageBConfirmationResult(
        candidate_id=candidate_id,
        status=status,
        gate_results=gate_results,
        gate_contract_sha256=contract_sha,
        slice_coverage=slice_coverage,
        corroborative_summary=corroborative,
    )


def result_to_dict(result: StageBConfirmationResult) -> dict[str, Any]:
    return {
        "candidate_id": result.candidate_id,
        "status": result.status,
        "gate_contract_sha256": result.gate_contract_sha256,
        "gate_results": result.gate_results,
        "slice_coverage": result.slice_coverage,
        "corroborative_summary": result.corroborative_summary,
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Batch-A Stage-B confirmation scorer")
    parser.add_argument("--metrics", required=True, help="arvp_strategy_metrics.v1 JSON")
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--output", help="Write JSON result to path")
    args = parser.parse_args(argv)

    payload = json.loads(Path(args.metrics).read_text(encoding="utf-8"))
    records = payload.get("records") or []
    result = score_stage_b_candidate(
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
