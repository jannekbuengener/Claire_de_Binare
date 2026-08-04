"""Resource budget validation for #4153 sensitivity campaign execution."""

from __future__ import annotations

from typing import Any, Mapping

HARD_MAX_PARALLELISM = 8
HARD_MAX_IN_FLIGHT = 8
HARD_MAX_ATTEMPTS = 3

REQUIRED_BUDGET_FIELDS = (
    "max_parallelism",
    "max_in_flight_runs",
    "max_attempts_per_run",
    "max_run_wall_time_seconds",
    "max_campaign_wall_time_seconds",
    "max_artifact_bytes",
    "minimum_free_disk_bytes",
    "max_consecutive_failures",
    "max_total_failures",
    "log_retention_days",
)


class SensitivityBudgetError(ValueError):
    """Fail-closed budget / resource-limit error."""


def validate_resource_budget(budget: Mapping[str, Any] | None) -> dict[str, Any]:
    if not budget:
        raise SensitivityBudgetError("BUDGET_MISSING")
    body = dict(budget)
    for field in REQUIRED_BUDGET_FIELDS:
        if field not in body:
            raise SensitivityBudgetError(f"BUDGET_FIELD_MISSING:{field}")
        value = body[field]
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise SensitivityBudgetError(f"BUDGET_FIELD_INVALID:{field}")

    if body["max_parallelism"] > HARD_MAX_PARALLELISM:
        raise SensitivityBudgetError("BUDGET_PARALLELISM_ABOVE_HARD_CAP")
    if body["max_in_flight_runs"] > HARD_MAX_IN_FLIGHT:
        raise SensitivityBudgetError("BUDGET_IN_FLIGHT_ABOVE_HARD_CAP")
    if body["max_attempts_per_run"] > HARD_MAX_ATTEMPTS:
        raise SensitivityBudgetError("BUDGET_ATTEMPTS_ABOVE_HARD_CAP")
    if body["max_in_flight_runs"] < body["max_parallelism"]:
        raise SensitivityBudgetError("BUDGET_IN_FLIGHT_LT_PARALLELISM")

    ram = body.get("ram_high_water_mark_bytes")
    if ram is not None and (
        not isinstance(ram, int) or isinstance(ram, bool) or ram < 1
    ):
        raise SensitivityBudgetError("BUDGET_RAM_INVALID")
    return body


def assert_disk_budget(
    *,
    budget: Mapping[str, Any],
    free_disk_bytes: int,
    projected_artifact_bytes: int,
) -> None:
    if free_disk_bytes < int(budget["minimum_free_disk_bytes"]):
        raise SensitivityBudgetError("BUDGET_FREE_DISK_INSUFFICIENT")
    if projected_artifact_bytes > int(budget["max_artifact_bytes"]):
        raise SensitivityBudgetError("BUDGET_ARTIFACT_QUOTA_EXCEEDED")


def assert_failure_thresholds(
    *,
    budget: Mapping[str, Any],
    consecutive_failures: int,
    total_failures: int,
) -> None:
    if consecutive_failures >= int(budget["max_consecutive_failures"]):
        raise SensitivityBudgetError("BUDGET_CONSECUTIVE_FAILURES_EXCEEDED")
    if total_failures >= int(budget["max_total_failures"]):
        raise SensitivityBudgetError("BUDGET_TOTAL_FAILURES_EXCEEDED")
