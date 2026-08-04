"""Reproduction / double-run contract for #4153.

Executed by the campaign runner: reproduction items are bound run replays of
existing primary run keys, compared in-place against the primary result. No new
run keys, no widening of the run count.

Comparison semantics:
- ``compare_reproduction_results`` compares only ``compared_fields`` after a
  fail-closed canonical normalization. Volatile fields (timestamps, host paths,
  attempt/process/log metadata, filesystem times, etc.) are never compared
  unless explicitly opted in via ``compared_fields``.
- Bindings (``run_key``, ``manifest_fingerprint``, ``run_plan_fingerprint``,
  ``authorization_fingerprint``) are asserted between primary and reproduction
  when provided; foreign primary results fail closed.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash

REPRODUCTION_CONTRACT_VERSION = "cdb.sensitivity_campaign_reproduction.v1"

# Fields that must never be compared implicitly, even if the primary result
# happens to persist them. Volatile / host-local by definition.
_VOLATILE_FIELDS = frozenset(
    {
        "attempt",
        "attempt_id",
        "process_id",
        "pid",
        "hostname",
        "host",
        "runtime_seconds",
        "runtime_ms",
        "wall_time_seconds",
        "wall_time_ms",
        "started_at_utc",
        "ended_at_utc",
        "completed_at_utc",
        "created_at_utc",
        "updated_at_utc",
        "timestamp",
        "log_path",
        "log_file",
        "log_filename",
        "output_dir",
        "output_directory",
        "artifact_path",
        "workspace",
        "cwd",
        "filesystem_mtime",
        "filesystem_ctime",
        "filesystem_atime",
    }
)

# Bindings that must be structurally identical between primary and reproduction
# when the caller opts into bindings validation.
_REQUIRED_BINDING_FIELDS = (
    "run_key",
    "manifest_fingerprint",
    "run_plan_fingerprint",
    "authorization_fingerprint",
)


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
    baseline_set = set(baseline_run_keys)
    for run_key in list(baseline_run_keys) + list(sample_run_keys):
        if run_key not in keys:
            raise SensitivityReproductionError(f"REPRO_UNKNOWN_RUN_KEY:{run_key}")
        for attempt in range(1, max_attempts + 1):
            items.append(
                {
                    "run_key": run_key,
                    "reproduction_attempt": attempt,
                    "creates_new_run_key": False,
                    "role": "baseline" if run_key in baseline_set else "sample",
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


def _project_compared(
    result: Mapping[str, Any], compared_fields: Sequence[str]
) -> dict[str, Any]:
    """Project the compared fields with canonical normalization."""
    projected: dict[str, Any] = {}
    for field in compared_fields:
        if field in _VOLATILE_FIELDS:
            raise SensitivityReproductionError(
                f"REPRO_COMPARED_FIELD_FORBIDDEN:{field}"
            )
        projected[field] = result.get(field)
    return projected


def _assert_bindings_match(
    *,
    primary: Mapping[str, Any],
    reproduction: Mapping[str, Any],
    required: Sequence[str],
) -> None:
    for field in required:
        p_val = primary.get(field)
        r_val = reproduction.get(field)
        # A binding key that is only present on one side (or is empty on both) is
        # only compared when at least one side provides a non-empty value.
        if p_val in (None, "") and r_val in (None, ""):
            continue
        if p_val != r_val:
            raise SensitivityReproductionError(
                f"REPRO_BINDING_MISMATCH:{field}:"
                f"primary={p_val!r} reproduction={r_val!r}"
            )


def compare_reproduction_results(
    *,
    primary: Mapping[str, Any],
    reproduction: Mapping[str, Any],
    compared_fields: Sequence[str],
    bindings: bool = False,
    required_bindings: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Compare primary vs reproduction result under exact-equality semantics.

    Returns a structured comparison dict. On mismatch: ``status="MISMATCH"``
    and ``reason_code="REPRODUCTION_RESULT_MISMATCH"``. Structural failures
    (missing bindings on both sides, forbidden compared fields) raise
    :class:`SensitivityReproductionError` fail-closed.
    """
    if not compared_fields:
        raise SensitivityReproductionError("REPRO_COMPARED_FIELDS_EMPTY")

    if bindings:
        required = tuple(required_bindings or _REQUIRED_BINDING_FIELDS)
        _assert_bindings_match(
            primary=primary,
            reproduction=reproduction,
            required=required,
        )

    primary_projected = _project_compared(primary, compared_fields)
    repro_projected = _project_compared(reproduction, compared_fields)

    primary_fp = canonical_hash(primary_projected)
    repro_fp = canonical_hash(repro_projected)

    mismatched: list[dict[str, Any]] = []
    for field in compared_fields:
        p_val = primary_projected.get(field)
        r_val = repro_projected.get(field)
        if p_val != r_val:
            mismatched.append(
                {
                    "field": field,
                    "primary": p_val,
                    "reproduction": r_val,
                    "reason_code": "REPRO_MISMATCH",
                }
            )

    body = {
        "schema_version": REPRODUCTION_CONTRACT_VERSION,
        "compared_fields": list(compared_fields),
        "primary_result_fingerprint": primary_fp,
        "reproduction_result_fingerprint": repro_fp,
        "mismatched_fields": mismatched,
    }
    if mismatched:
        body["status"] = "MISMATCH"
        body["reason_code"] = "REPRODUCTION_RESULT_MISMATCH"
    else:
        body["status"] = "PASS"
        body["reason_code"] = "REPRODUCTION_RESULT_PASS"

    body["comparison_fingerprint"] = canonical_hash(
        {
            "compared_fields": list(compared_fields),
            "primary_result_fingerprint": primary_fp,
            "reproduction_result_fingerprint": repro_fp,
            "mismatched_fields": mismatched,
            "status": body["status"],
        }
    )
    return body
