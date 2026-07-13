from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .contract import (
    EVIDENCE_CLASS_CONTROLLED,
    JOB_FAIL,
    JOB_INSUFFICIENT_DATA,
    JOB_PASS,
    STRATEGY_PARKED,
    VacationManifest,
    campaign_artifact_dir,
)
from .queue_store import QUEUE_STATE_FILENAME, atomic_write_json

VERDICT_NEXT = "NEXT_VALIDATION_CANDIDATE"
VERDICT_HOLD = "HOLD_MORE_DATA"
VERDICT_REJECT_ECON = "REJECT_ECONOMICS"
VERDICT_INSUFFICIENT = "INSUFFICIENT_DATA"
VERDICT_TECH_INVALID = "TECHNICALLY_INVALID"

_SUMMARY_METRIC_ALIASES: dict[str, tuple[str, ...]] = {
    "trade_count": ("closed_trades_total", "trade_count"),
    "net_pnl": ("net_pnl_quote", "net_pnl", "total_return"),
    "profit_factor": ("profit_factor",),
    "expectancy": ("expectancy_r", "expectancy"),
    "max_drawdown": ("max_drawdown_r", "max_drawdown"),
    "win_rate": ("win_rate",),
    "total_return": ("total_return", "net_pnl_quote", "net_pnl"),
}


def _resolve_scenario_metric(payload: Mapping[str, Any], *field_names: str) -> Any:
    metrics = payload.get("metrics")
    if isinstance(metrics, dict):
        for field in field_names:
            if field in metrics and metrics[field] is not None:
                return metrics[field]
    for field in field_names:
        if field in payload and payload[field] is not None:
            return payload[field]
    return None


def _resolve_trade_count(payload: Mapping[str, Any]) -> int | None:
    value = _resolve_scenario_metric(payload, "closed_trades_total", "trade_count")
    if value is None:
        return None
    return int(value)


def _job_verdict(job: Mapping[str, Any]) -> str:
    status = job.get("status")
    if status == JOB_INSUFFICIENT_DATA:
        return VERDICT_INSUFFICIENT
    if status != JOB_PASS:
        return VERDICT_TECH_INVALID
    if not job.get("artifacts_complete"):
        return VERDICT_TECH_INVALID
    if job.get("strategy_role") == STRATEGY_PARKED:
        return VERDICT_HOLD
    metrics = job.get("scenario_metrics") or {}
    group = metrics.get("_group_manifest") if isinstance(metrics, dict) else None
    if isinstance(group, dict):
        failed = int(group.get("failed_count") or 0)
        if failed > 0:
            return VERDICT_TECH_INVALID
    baseline = metrics.get("baseline") if isinstance(metrics, dict) else None
    if isinstance(baseline, dict):
        trade_count = _resolve_trade_count(baseline)
        if trade_count == 0:
            return VERDICT_HOLD
        if trade_count is None:
            return VERDICT_HOLD
        net = _resolve_scenario_metric(baseline, "net_pnl_quote", "net_pnl", "total_return")
        if net is not None and float(net) < 0:
            pessimistic = metrics.get("pessimistic_execution")
            if isinstance(pessimistic, dict):
                p_net = _resolve_scenario_metric(
                    pessimistic,
                    "net_pnl_quote",
                    "net_pnl",
                    "total_return",
                )
                if p_net is not None and float(p_net) < 0:
                    return VERDICT_REJECT_ECON
            return VERDICT_HOLD
    return VERDICT_NEXT


def build_summary_payload(
    manifest: VacationManifest,
    state: Mapping[str, Any],
) -> dict[str, Any]:
    jobs = [j for j in state.get("jobs") or [] if isinstance(j, dict)]
    rows: list[dict[str, Any]] = []
    for job in jobs:
        rows.append(
            {
                "job_id": job.get("job_id"),
                "strategy_id": job.get("strategy_id"),
                "strategy_role": job.get("strategy_role"),
                "dataset_id": job.get("dataset_id"),
                "status": job.get("status"),
                "scenarios": job.get("scenarios"),
                "artifacts_complete": bool(job.get("artifacts_complete")),
                "artifacts_present": job.get("artifacts_present") or [],
                "artifacts_missing": job.get("artifacts_missing") or [],
                "exit_code": job.get("exit_code"),
                "error_classification": job.get("error_classification"),
                "fingerprint": job.get("fingerprint"),
                "verdict": _job_verdict(job),
                "evidence_class": EVIDENCE_CLASS_CONTROLLED,
                "ranking_ready": False,
                "scenario_metrics_summary": _metrics_summary(job),
            }
        )
    return {
        "schema_version": "1.0",
        "campaign_id": manifest.campaign_id,
        "source_sha": manifest.source_sha,
        "evidence_class": EVIDENCE_CLASS_CONTROLLED,
        "ranking_ready": False,
        "lr_status": "NO-GO",
        "campaign_status": state.get("campaign_status"),
        "job_count": len(rows),
        "pass_count": sum(1 for r in rows if r["status"] == JOB_PASS),
        "fail_count": sum(1 for r in rows if r["status"] == JOB_FAIL),
        "jobs": rows,
        "limitations": [
            "MVP summary only; no full Strategy League Table integration.",
            "NEXT_VALIDATION_CANDIDATE is not promotion, paper-go, or live-go.",
            "controlled_lab_evidence only.",
        ],
    }


def _metrics_summary(job: Mapping[str, Any]) -> dict[str, Any]:
    metrics = job.get("scenario_metrics")
    if not isinstance(metrics, dict):
        return {}
    summary: dict[str, Any] = {}
    for scenario_id, payload in metrics.items():
        if scenario_id.startswith("_") or not isinstance(payload, dict):
            continue
        summary[scenario_id] = {
            summary_key: _resolve_scenario_metric(payload, *aliases)
            for summary_key, aliases in _SUMMARY_METRIC_ALIASES.items()
            if _resolve_scenario_metric(payload, *aliases) is not None
        }
    return summary


def render_summary_markdown(summary: Mapping[str, Any]) -> str:
    lines = [
        f"# ARVP Vacation Summary — {summary.get('campaign_id')}",
        "",
        f"- **Campaign status:** {summary.get('campaign_status')}",
        f"- **Evidence class:** {summary.get('evidence_class')}",
        f"- **ranking_ready:** {summary.get('ranking_ready')}",
        f"- **LR:** {summary.get('lr_status')}",
        f"- **Jobs:** {summary.get('job_count')} "
        f"(pass={summary.get('pass_count')}, fail={summary.get('fail_count')})",
        "",
        "## Jobs",
        "",
        "| Job | Strategy | Dataset | Status | Verdict | Artifacts |",
        "|-----|----------|---------|--------|---------|-----------|",
    ]
    for row in summary.get("jobs") or []:
        if not isinstance(row, dict):
            continue
        artifacts = "complete" if row.get("artifacts_complete") else "incomplete"
        lines.append(
            f"| {row.get('job_id')} | {row.get('strategy_id')} | "
            f"{row.get('dataset_id')} | {row.get('status')} | "
            f"{row.get('verdict')} | {artifacts} |"
        )
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- Offline controlled_lab_evidence only.",
            "- No paper runtime, no live-go, no LR upgrade.",
            "- NEXT_VALIDATION_CANDIDATE is advisory only.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_summary(
    manifest: VacationManifest,
    state: Mapping[str, Any],
    repo_root: Path,
) -> tuple[Path, Path]:
    campaign_dir = campaign_artifact_dir(manifest, repo_root)
    summary = build_summary_payload(manifest, state)
    json_path = campaign_dir / "vacation_summary.json"
    md_path = campaign_dir / "vacation_summary.md"
    atomic_write_json(json_path, summary, pretty=True)
    md_path.write_text(render_summary_markdown(summary), encoding="utf-8")
    return json_path, md_path
