"""Shared ARVP vacation metric contract helpers (#4014, #4015)."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

CANONICAL_JOB_COUNT = 318
SUPERSEDED_JOB_COUNT = 6
QUEUE_RECORD_COUNT = 324
CANONICAL_SELECTOR = "superseded_by_stress_v2_rerun != true"
OUTCOME_READY = "READY_FOR_METRIC_EXTRACTION"


class VacationMetricContractError(ValueError):
    """Fail-closed contract violation for vacation metric availability."""


def is_canonical_queue_job(job: Mapping[str, Any]) -> bool:
    """Return True for canonical jobs per superseded_by_stress_v2_rerun != true."""
    superseded = job.get("superseded_by_stress_v2_rerun")
    if superseded is True:
        return False
    if superseded is False or superseded is None:
        return True
    raise VacationMetricContractError(
        f"unknown superseded_by_stress_v2_rerun value: {superseded!r}"
    )


def select_canonical_jobs(jobs: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    canonical: list[dict[str, Any]] = []
    for job in jobs:
        if not isinstance(job, dict):
            raise VacationMetricContractError("queue job must be object")
        if is_canonical_queue_job(job):
            canonical.append(job)
    return canonical


def is_rankable_job_metrics(metrics: Mapping[str, Any]) -> bool:
    if "closed_trades_total" not in metrics:
        return False
    try:
        return int(metrics["closed_trades_total"]) > 0
    except (TypeError, ValueError) as exc:
        raise VacationMetricContractError(
            "closed_trades_total must be integer-like"
        ) from exc


def metric_is_missing(metrics: Mapping[str, Any], field: str) -> bool:
    if field not in metrics:
        return True
    return metrics[field] is None
