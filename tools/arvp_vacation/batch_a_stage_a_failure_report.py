"""Stage-A gate failure attribution report (#4065 P4)."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.replay.batch_a_strategy_registry import batch_a_strategy_ids
from core.replay.canonical_json import canonical_hash, canonical_json_dumps

from .batch_a_stage_a_survivor_scorer import (
    BASELINE_SCENARIO,
    PESSIMISTIC_SCENARIO,
    score_stage_a_candidates,
)
from .batch_a_gate_common import median_of_field, positive_share, profit_factor_gate_value

SCHEMA_VERSION = "batch_a_stage_a_failure_report.v1"


def _median_net_pnl(records: Sequence[Mapping[str, Any]]) -> float | None:
    return median_of_field(records, "net_pnl_quote")


def _failure_class(
    *,
    status: str,
    gate_results: Mapping[str, Any],
    coverage: Mapping[str, Any],
) -> str:
    if status == "INSUFFICIENT_EVIDENCE":
        if coverage.get("paired_evaluable_count", 0) == 0:
            return "technical"
        return "sample_size"
    gates = gate_results.get("gates") or {}
    failed = [gid for gid, row in gates.items() if not row.get("passed")]
    economic_gates = {"G-E01", "G-E02", "G-E03", "G-E04", "G-E05", "G-E06", "G-R02"}
    technical_gates = {"G-T01", "G-T02", "G-R01"}
    has_econ = any(g in failed for g in economic_gates)
    has_tech = any(g in failed for g in technical_gates)
    if has_econ and has_tech:
        return "mixed"
    if has_econ:
        return "economic"
    if has_tech:
        return "technical"
    return "economic"


def _regime_evidence_status(records: Sequence[Mapping[str, Any]]) -> str:
    if not records:
        return "missing"
    if any(isinstance(r.get("regime_stats"), dict) for r in records):
        return "present"
    return "missing"


def _data_quality_status(records: Sequence[Mapping[str, Any]]) -> str:
    flags: Counter[str] = Counter()
    for record in records:
        for flag in record.get("data_quality_flags") or []:
            flags[str(flag)] += 1
    if flags.get("warmup_provenance_missing") or flags.get("candles_evaluated_mismatch"):
        return "blocked"
    if flags.get("warmup_trim_applied"):
        return "warmup_trim_ok"
    return "ok"


def _candidate_report(
    *,
    candidate_id: str,
    records: Sequence[Mapping[str, Any]],
    scorer_result: Mapping[str, Any],
    before_status: str | None,
) -> dict[str, Any]:
    indexed: dict[str, dict[str, Mapping[str, Any]]] = {}
    for record in records:
        if str(record.get("strategy_id")) != candidate_id:
            continue
        window_id = str(record.get("window_id") or "")
        scenario = str(record.get("scenario") or "")
        indexed.setdefault(window_id, {})[scenario] = record

    valid_pairs = 0
    missing_pairs = 0
    duplicate_pairs = 0
    for window_id, pair in indexed.items():
        if BASELINE_SCENARIO in pair and PESSIMISTIC_SCENARIO in pair:
            valid_pairs += 1
        else:
            missing_pairs += 1
        if len(pair) > 2:
            duplicate_pairs += 1

    baseline_rows = [
        pair[BASELINE_SCENARIO]
        for pair in indexed.values()
        if BASELINE_SCENARIO in pair
    ]
    pessimistic_rows = [
        pair[PESSIMISTIC_SCENARIO]
        for pair in indexed.values()
        if PESSIMISTIC_SCENARIO in pair
    ]
    rankable_baseline = sum(1 for r in baseline_rows if r.get("rankable"))
    rankable_pessimistic = sum(1 for r in pessimistic_rows if r.get("rankable"))

    coverage = scorer_result.get("coverage") or {}
    gate_results = scorer_result.get("gate_results") or {}
    gates = gate_results.get("gates") or {}
    passed_gates = sorted(gid for gid, row in gates.items() if row.get("passed"))
    failed_gates = sorted(gid for gid, row in gates.items() if not row.get("passed"))

    status = str(scorer_result.get("status") or "")
    return {
        "candidate_id": candidate_id,
        "parameter_fingerprint": next(
            (
                (r.get("warmup_provenance") or {}).get("parameter_fingerprint")
                for r in records
                if str(r.get("strategy_id")) == candidate_id
                and isinstance(r.get("warmup_provenance"), dict)
            ),
            None,
        ),
        "final_status": status,
        "expected_windows": 39,
        "expected_scenario_pairs": 39,
        "valid_pairs": valid_pairs,
        "missing_pairs": missing_pairs,
        "duplicate_pairs": duplicate_pairs,
        "baseline_rankable_share": coverage.get("baseline_rankable_share"),
        "pessimistic_rankable_share": coverage.get("pessimistic_rankable_share"),
        "rankable_baseline_windows": rankable_baseline,
        "rankable_pessimistic_windows": rankable_pessimistic,
        "trade_count_total": sum(int(r.get("closed_trades_total") or 0) for r in baseline_rows),
        "median_net_pnl_baseline": _median_net_pnl(baseline_rows),
        "median_net_pnl_pessimistic": _median_net_pnl(pessimistic_rows),
        "positive_window_share_baseline": positive_share(baseline_rows, "net_pnl_quote"),
        "positive_window_share_pessimistic": positive_share(
            pessimistic_rows, "net_pnl_quote"
        ),
        "profit_factor_baseline": profit_factor_gate_value(baseline_rows),
        "profit_factor_pessimistic": profit_factor_gate_value(pessimistic_rows),
        "expectancy_baseline": median_of_field(baseline_rows, "expectancy_r"),
        "max_drawdown_baseline": median_of_field(baseline_rows, "max_drawdown_r"),
        "data_quality_status": _data_quality_status(baseline_rows + pessimistic_rows),
        "regime_evidence_status": _regime_evidence_status(baseline_rows),
        "gates_passed": passed_gates,
        "gates_failed": failed_gates,
        "failure_class": _failure_class(
            status=status,
            gate_results=gate_results,
            coverage=coverage,
        ),
        "status_before_4065_fix": before_status,
        "status_changed_by_4065": before_status is not None and before_status != status,
    }


def build_failure_report(
    *,
    metrics_bundle: Mapping[str, Any],
    before_survivor_summary: Mapping[str, Any] | None = None,
    metrics_content_hash_before: str | None = None,
) -> dict[str, Any]:
    records = metrics_bundle.get("records") or []
    if not isinstance(records, list):
        raise ValueError("metrics bundle records must be a list")

    before_by_candidate: dict[str, str] = {}
    if before_survivor_summary:
        candidates = before_survivor_summary.get("candidates") or {}
        if isinstance(candidates, dict):
            for cid, row in candidates.items():
                if isinstance(row, dict):
                    before_by_candidate[str(cid)] = str(row.get("status") or "")

    scorer = score_stage_a_candidates(
        records=records,
        candidate_ids=batch_a_strategy_ids(),
    )
    candidate_reports = [
        _candidate_report(
            candidate_id=cid,
            records=records,
            scorer_result={
                "status": result.status,
                "coverage": result.coverage,
                "gate_results": result.gate_results,
            },
            before_status=before_by_candidate.get(cid),
        )
        for cid, result in sorted(scorer.items())
    ]

    survivors = sum(1 for row in candidate_reports if row["final_status"] == "STAGE_A_SURVIVOR")
    gate_fail_freq: Counter[str] = Counter()
    multi_cause = 0
    for row in candidate_reports:
        for gate_id in row["gates_failed"]:
            gate_fail_freq[gate_id] += 1
        if len(row["gates_failed"]) > 1:
            multi_cause += 1

    report = {
        "schema_version": SCHEMA_VERSION,
        "issue": "#4065",
        "campaign_id": metrics_bundle.get("campaign_id"),
        "metrics_content_hash_after_fix": metrics_bundle.get("content_hash"),
        "metrics_content_hash_before_fix": metrics_content_hash_before,
        "survivor_count_after_fix": survivors,
        "survivor_count_before_fix": int(
            (before_survivor_summary or {}).get("survivor_count") or 0
        ),
        "candidates": candidate_reports,
        "aggregate": {
            "gate_failure_frequency": dict(sorted(gate_fail_freq.items())),
            "multi_cause_candidates": multi_cause,
            "status_changed_by_4065_count": sum(
                1 for row in candidate_reports if row["status_changed_by_4065"]
            ),
            "technical_failure_share": sum(
                1
                for row in candidate_reports
                if row["failure_class"] in {"technical", "mixed"}
            )
            / max(len(candidate_reports), 1),
            "economic_failure_share": sum(
                1
                for row in candidate_reports
                if row["failure_class"] in {"economic", "sample_size"}
            )
            / max(len(candidate_reports), 1),
        },
        "exit_gate": "FAILURE_REPORT_COMPLETE",
    }
    report["content_hash"] = canonical_hash(
        {k: v for k, v in report.items() if k != "content_hash"}
    )
    return report


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch-A Stage-A failure report (#4065)")
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--before-summary", default=None)
    parser.add_argument("--before-hash", default=None)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", default=None)
    return parser.parse_args(argv)


def _render_md(report: Mapping[str, Any]) -> str:
    lines = [
        "# Batch-A Stage-A Failure Report (#4065 P4)",
        "",
        f"- Campaign: `{report.get('campaign_id')}`",
        f"- Survivors after fix: **{report.get('survivor_count_after_fix')}**",
        f"- Survivors before fix: **{report.get('survivor_count_before_fix')}**",
        f"- Metrics hash after: `{report.get('metrics_content_hash_after_fix')}`",
        "",
        "| candidate | status | failure_class | changed_by_4065 |",
        "|---|---|---|---|",
    ]
    for row in report.get("candidates") or []:
        lines.append(
            f"| {row['candidate_id']} | {row['final_status']} | "
            f"{row['failure_class']} | {row['status_changed_by_4065']} |"
        )
    lines.append("")
    lines.append(f"Exit gate: `{report.get('exit_gate')}`")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    bundle = json.loads(Path(args.metrics).read_text(encoding="utf-8"))
    before = None
    if args.before_summary:
        before = json.loads(Path(args.before_summary).read_text(encoding="utf-8"))
    report = build_failure_report(
        metrics_bundle=bundle,
        before_survivor_summary=before,
        metrics_content_hash_before=args.before_hash,
    )
    Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_json).write_text(canonical_json_dumps(report) + "\n", encoding="utf-8")
    if args.output_md:
        Path(args.output_md).write_text(_render_md(report), encoding="utf-8")
    print(json.dumps({"exit_gate": report["exit_gate"], "content_hash": report["content_hash"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
