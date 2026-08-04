"""Reproduction / double-run contract for #4153 (plan only; not executed here)."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash

REPRODUCTION_CONTRACT_VERSION = "cdb.sensitivity_campaign_reproduction.v1"


class SensitivityReproductionError(ValueError):
    """Fail-closed reproduction-contract error."""


def build_reproduction_plan(
    *,
    run_keys: Sequence[str],
    policy: Mapping[str, Any],
    baseline_run_keys: Sequence[str] | None = None,
    sample_run_keys: Sequence[str] | None = None,
) -> dict[str, Any]:
    if not policy.get("enabled"):
        return {
            "schema_version": REPRODUCTION_CONTRACT_VERSION,
            "enabled": False,
            "reproduction_items": [],
            "adds_run_keys": False,
            "max_run_count_unchanged": True,
        }

    keys = list(run_keys)
    if not keys:
        raise SensitivityReproductionError("REPRO_NO_RUN_KEYS")

    baseline_n = int(policy.get("baseline_run_key_count") or 0)
    sample_n = int(policy.get("sample_run_key_count") or 0)
    max_attempts = int(policy.get("max_reproduction_attempts_per_key") or 1)
    if max_attempts < 1:
        raise SensitivityReproductionError("REPRO_MAX_ATTEMPTS_INVALID")

    if baseline_run_keys is None:
        baseline_run_keys = keys[:baseline_n]
    if sample_run_keys is None:
        # Deterministic sample: evenly spaced keys excluding baseline set.
        remaining = [k for k in keys if k not in set(baseline_run_keys)]
        if sample_n == 0 or not remaining:
            sample_run_keys = []
        else:
            step = max(1, len(remaining) // sample_n)
            sample_run_keys = remaining[::step][:sample_n]

    comparison_mode = policy.get("comparison_mode")
    if comparison_mode != "exact_equality":
        raise SensitivityReproductionError(
            f"REPRO_COMPARISON_MODE_UNSUPPORTED:{comparison_mode!r}"
        )
    on_mismatch = policy.get("on_mismatch")
    if on_mismatch != "block_campaign_completion":
        raise SensitivityReproductionError(
            f"REPRO_ON_MISMATCH_UNSUPPORTED:{on_mismatch!r}"
        )

    items = []
    for run_key in list(baseline_run_keys) + list(sample_run_keys):
        if run_key not in keys:
            raise SensitivityReproductionError(f"REPRO_UNKNOWN_RUN_KEY:{run_key}")
        for attempt in range(1, max_attempts + 1):
            items.append(
                {
                    "run_key": run_key,
                    "reproduction_attempt": attempt,
                    "creates_new_run_key": False,
                    "role": "baseline" if run_key in baseline_run_keys else "sample",
                }
            )

    plan = {
        "schema_version": REPRODUCTION_CONTRACT_VERSION,
        "enabled": True,
        "comparison_mode": comparison_mode,
        "on_mismatch": on_mismatch,
        "compared_result_fields": list(policy.get("compared_result_fields") or []),
        "baseline_run_keys": list(baseline_run_keys),
        "sample_run_keys": list(sample_run_keys),
        "reproduction_items": items,
        "adds_run_keys": False,
        "max_run_count_unchanged": True,
        "unique_run_key_count": len(keys),
    }
    plan["reproduction_plan_fingerprint"] = canonical_hash(plan)
    return plan


def compare_reproduction_results(
    *,
    primary: Mapping[str, Any],
    reproduction: Mapping[str, Any],
    compared_fields: Sequence[str],
) -> None:
    for field in compared_fields:
        if primary.get(field) != reproduction.get(field):
            raise SensitivityReproductionError(
                f"REPRO_MISMATCH:{field}:"
                f"{primary.get(field)!r}!={reproduction.get(field)!r}"
            )
