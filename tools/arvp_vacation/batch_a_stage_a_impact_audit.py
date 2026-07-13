"""Read-only Stage-A impact audit for #4065 (P1).

Quantifies candle/rankability and regime_stats impact on the Batch-A funnel verdict.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.replay.batch_a_strategy_registry import batch_a_strategy_ids
from core.replay.canonical_json import canonical_hash, canonical_json_dumps

from .candle_rankability import (
    FLAG_WARMUP_TRIM_APPLIED,
    legacy_resolve_candles_total,
    resolve_candle_rankability,
)
from .metric_contract import is_rankable_job_metrics, metric_is_missing
from .strategy_metric_extraction import ALLOWED_SCENARIOS, REQUIRED_METRIC_FIELDS

BATCH_A_QUEUE_REL = (
    "artifacts/arvp_vacation/batch_a_stage_a_d0a4e72d_20260713/queue_state.json"
)
EXPECTED_JOBS = 390
EXPECTED_SCENARIO_RECORDS = 780
EXPECTED_CANDIDATES = 10


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


def _legacy_rankable(metrics: Mapping[str, Any], data_quality_flags: Sequence[str]) -> bool:
    if "closed_trades_total" not in metrics:
        return False
    if not is_rankable_job_metrics(metrics):
        return False
    for field in REQUIRED_METRIC_FIELDS:
        if field == "closed_trades_total":
            continue
        if metric_is_missing(metrics, field):
            return False
    for flag in data_quality_flags:
        if flag.startswith("missing_") or flag.endswith("_mismatch"):
            return False
    return True


def _proposed_rankable(
    metrics: Mapping[str, Any],
    blocking_flags: Sequence[str],
) -> bool:
    if blocking_flags:
        return False
    if "closed_trades_total" not in metrics:
        return False
    if not is_rankable_job_metrics(metrics):
        return False
    for field in REQUIRED_METRIC_FIELDS:
        if field == "closed_trades_total":
            continue
        if metric_is_missing(metrics, field):
            return False
    return True


def run_impact_audit(
    *,
    queue_state_path: Path,
    repo_root: Path,
    metrics_bundle_path: Path | None = None,
) -> dict[str, Any]:
    queue_state = _load_json(queue_state_path)
    campaign_id = str(queue_state.get("campaign_id") or "")
    jobs = queue_state.get("jobs") or []
    if not isinstance(jobs, list):
        raise ValueError("queue_state.jobs must be a list")

    queue_sha = _file_sha256(queue_state_path)
    campaign_source_sha = queue_state.get("source_sha")

    per_candidate: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "legacy_mismatch": 0,
            "warmup_explained": 0,
            "unexplained_mismatch": 0,
            "zero_trade": 0,
            "legacy_rankable": 0,
            "proposed_rankable": 0,
            "regime_stats_present": 0,
            "regime_stats_missing": 0,
            "impact_classes": Counter(),
        }
    )

    totals: Counter[str] = Counter()
    scenario_ids = ("baseline", "pessimistic_execution")

    for job in jobs:
        if not isinstance(job, dict):
            continue
        strategy_id = str(job.get("strategy_id") or "")
        parameter_fingerprint = str(job.get("fingerprint") or "") or None
        scenario_metrics = job.get("scenario_metrics") or {}
        if not isinstance(scenario_metrics, dict):
            continue

        for scenario_id in scenario_ids:
            payload = scenario_metrics.get(scenario_id)
            if not isinstance(payload, dict):
                continue
            dataset_summary = payload.get("dataset_summary") or {}
            if not isinstance(dataset_summary, dict):
                dataset_summary = {}

            _, legacy_flags = legacy_resolve_candles_total(dataset_summary)
            if "candles_live_candles_total_mismatch" in legacy_flags:
                per_candidate[strategy_id]["legacy_mismatch"] += 1
                totals["legacy_mismatch"] += 1

            candle = resolve_candle_rankability(
                dataset_summary=dataset_summary,
                strategy_id=strategy_id,
                campaign_id=campaign_id,
                parameter_fingerprint=parameter_fingerprint,
                campaign_source_sha=str(campaign_source_sha)
                if campaign_source_sha
                else None,
                repo_root=repo_root,
            )
            if FLAG_WARMUP_TRIM_APPLIED in candle.data_quality_flags:
                per_candidate[strategy_id]["warmup_explained"] += 1
                totals["warmup_explained"] += 1
            if candle.rankability_blocking_flags:
                per_candidate[strategy_id]["unexplained_mismatch"] += 1
                totals["unexplained_mismatch"] += 1

            metrics = payload.get("metrics") or {}
            if isinstance(metrics, dict) and metrics.get("closed_trades_total") == 0:
                per_candidate[strategy_id]["zero_trade"] += 1
                totals["zero_trade"] += 1

            legacy_rankable = _legacy_rankable(metrics, legacy_flags) if isinstance(metrics, dict) else False
            proposed_rankable = (
                _proposed_rankable(metrics, candle.rankability_blocking_flags)
                if isinstance(metrics, dict)
                else False
            )

            if legacy_rankable:
                per_candidate[strategy_id]["legacy_rankable"] += 1
                totals["legacy_rankable"] += 1
            if proposed_rankable:
                per_candidate[strategy_id]["proposed_rankable"] += 1
                totals["proposed_rankable"] += 1

            has_regime = isinstance(payload.get("regime_stats"), dict)
            if has_regime:
                per_candidate[strategy_id]["regime_stats_present"] += 1
                totals["regime_stats_present"] += 1
            else:
                per_candidate[strategy_id]["regime_stats_missing"] += 1
                totals["regime_stats_missing"] += 1

            if legacy_rankable != proposed_rankable:
                impact = "verdict_affecting"
            elif has_regime:
                impact = "downstream_contract_blocking"
            elif candle.rankability_blocking_flags:
                impact = "data_quality_affecting"
            else:
                impact = "presentation_only"
            per_candidate[strategy_id]["impact_classes"][impact] += 1
            totals[f"impact_{impact}"] += 1

    metrics_hash_before: str | None = None
    if metrics_bundle_path and metrics_bundle_path.is_file():
        bundle = _load_json(metrics_bundle_path)
        metrics_hash_before = str(bundle.get("content_hash") or "")

    candidate_ids = sorted(batch_a_strategy_ids())
    jobs_per_candidate = Counter(
        str(j.get("strategy_id")) for j in jobs if isinstance(j, dict)
    )

    report = {
        "schema_version": "batch_a_stage_a_impact_audit.v1",
        "issue": "#4065",
        "campaign_id": campaign_id,
        "queue_state_path": queue_state_path.as_posix(),
        "queue_state_sha256": queue_sha,
        "campaign_source_sha": campaign_source_sha,
        "metrics_content_hash_before_fix": metrics_hash_before,
        "artifact_gate": {
            "passed": len(jobs) == EXPECTED_JOBS and len(candidate_ids) == EXPECTED_CANDIDATES,
            "job_count": len(jobs),
            "expected_jobs": EXPECTED_JOBS,
            "scenario_records_expected": EXPECTED_SCENARIO_RECORDS,
            "candidates": len(candidate_ids),
        },
        "totals": dict(totals),
        "legacy_mismatch_count": totals["legacy_mismatch"],
        "warmup_explained_count": totals["warmup_explained"],
        "unexplained_mismatch_count": totals["unexplained_mismatch"],
        "zero_trade_count": totals["zero_trade"],
        "legacy_rankable_count": totals["legacy_rankable"],
        "proposed_rankable_count": totals["proposed_rankable"],
        "regime_stats_present": totals["regime_stats_present"],
        "regime_stats_missing": totals["regime_stats_missing"],
        "per_candidate": {
            cid: {
                **{k: v for k, v in data.items() if k != "impact_classes"},
                "impact_classes": dict(data["impact_classes"]),
                "jobs": jobs_per_candidate.get(cid, 0),
            }
            for cid, data in sorted(per_candidate.items())
        },
        "impact_summary": {
            "verdict_affecting": totals.get("impact_verdict_affecting", 0),
            "downstream_contract_blocking": totals.get(
                "impact_downstream_contract_blocking", 0
            ),
            "data_quality_affecting": totals.get("impact_data_quality_affecting", 0),
            "presentation_only": totals.get("impact_presentation_only", 0),
        },
        "exit_gate": "IMPACT_CLASSIFIED",
    }
    report["content_hash"] = canonical_hash(
        {k: v for k, v in report.items() if k != "content_hash"}
    )
    return report


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch-A #4065 impact audit (P1)")
    parser.add_argument("--queue-state", default=BATCH_A_QUEUE_REL)
    parser.add_argument("--metrics-bundle", default=None)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", default=None)
    return parser.parse_args(argv)


def _render_md(report: Mapping[str, Any]) -> str:
    lines = [
        "# Batch-A Stage-A Impact Audit (#4065 P1)",
        "",
        f"- Campaign: `{report.get('campaign_id')}`",
        f"- Queue SHA256: `{report.get('queue_state_sha256')}`",
        f"- Legacy mismatch records: **{report.get('legacy_mismatch_count')}**",
        f"- Warmup-explained (proposed): **{report.get('warmup_explained_count')}**",
        f"- Unexplained blocking: **{report.get('unexplained_mismatch_count')}**",
        f"- Zero-trade records: **{report.get('zero_trade_count')}**",
        f"- Legacy rankable: **{report.get('legacy_rankable_count')}**",
        f"- Proposed rankable: **{report.get('proposed_rankable_count')}**",
        f"- regime_stats present: **{report.get('regime_stats_present')}**",
        "",
        "## Impact summary",
        "",
    ]
    summary = report.get("impact_summary") or {}
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append(f"Exit gate: `{report.get('exit_gate')}`")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    queue_path = Path(args.queue_state)
    if not queue_path.is_absolute():
        queue_path = repo_root / queue_path
    metrics_path = (
        Path(args.metrics_bundle).resolve()
        if args.metrics_bundle
        else repo_root
        / "artifacts/evidence/batch_a_stage_a_d0a4e72d_20260713/arvp_strategy_metrics.v1.json"
    )
    report = run_impact_audit(
        queue_state_path=queue_path,
        repo_root=repo_root,
        metrics_bundle_path=metrics_path if metrics_path.is_file() else None,
    )
    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(canonical_json_dumps(report) + "\n", encoding="utf-8")
    if args.output_md:
        Path(args.output_md).write_text(_render_md(report), encoding="utf-8")
    print(
        json.dumps(
            {"exit_gate": report["exit_gate"], "content_hash": report["content_hash"]},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
