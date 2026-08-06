"""hh_hl reproduction plan — planning-only (#4374).

Does not create primary run keys. Selection is deterministic from sorted keys.
Compared fields derive from Pack-A / hh_hl result contract names.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash

REPRODUCTION_POLICY_ID = "hh_hl_reproduction_prep_v1"

# Actual hh_hl / Pack-A metrics field names (not #4153 analyzer allowlist).
COMPARED_RESULT_FIELDS: tuple[str, ...] = (
    "gate_result.status",
    "closed_trades_total",
    "fees_total_quote",
    "net_pnl_quote",
    "expectancy_r",
    "max_drawdown_r",
)

# turnover is absent from hh_hl Pack-A metrics — do not invent it.
VOLATILE_FIELDS_REJECTED: tuple[str, ...] = (
    "started_at_utc",
    "finished_at_utc",
    "pid",
    "tmp_path",
    "absolute_path",
)

DEFAULT_POLICY: dict[str, Any] = {
    "reproduction_policy_id": REPRODUCTION_POLICY_ID,
    "enabled": True,
    "max_reproduction_attempts_per_key": 1,
    "comparison_mode": "exact_equality",
    "baseline_run_key_count": 1,
    "sample_run_key_count": 5,
    "compared_result_fields": list(COMPARED_RESULT_FIELDS),
    "bindings_must_match": True,
    "volatile_fields_rejected": list(VOLATILE_FIELDS_REJECTED),
    "on_mismatch": "block_campaign_completion",
    "creates_new_primary_run_keys": False,
}


class HhHlReproductionPlanError(ValueError):
    """Fail-closed reproduction plan violation."""


def build_hh_hl_reproduction_plan(
    run_keys: Sequence[str],
    *,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    pol = dict(policy or DEFAULT_POLICY)
    if pol.get("creates_new_primary_run_keys"):
        raise HhHlReproductionPlanError("REPRODUCTION_MUST_NOT_CREATE_PRIMARY_KEYS")
    if pol.get("comparison_mode") != "exact_equality":
        raise HhHlReproductionPlanError("REPRODUCTION_COMPARISON_MODE_INVALID")
    if int(pol.get("max_reproduction_attempts_per_key") or 0) != 1:
        raise HhHlReproductionPlanError("REPRODUCTION_MAX_ATTEMPTS_MUST_BE_1")

    sorted_keys = sorted(run_keys)
    if not sorted_keys:
        raise HhHlReproductionPlanError("REPRODUCTION_EMPTY_RUN_KEYS")

    baseline_n = int(pol["baseline_run_key_count"])
    sample_n = int(pol["sample_run_key_count"])
    if baseline_n < 1:
        raise HhHlReproductionPlanError("REPRODUCTION_BASELINE_REQUIRED")

    baseline_keys = sorted_keys[:baseline_n]
    # Deterministic sample from remaining sorted keys (no randomness).
    remaining = sorted_keys[baseline_n:]
    sample_keys = remaining[: max(0, sample_n)]
    selected = tuple(dict.fromkeys([*baseline_keys, *sample_keys]))

    for field in VOLATILE_FIELDS_REJECTED:
        if field in (pol.get("compared_result_fields") or []):
            raise HhHlReproductionPlanError(f"VOLATILE_FIELD_COMPARE_FORBIDDEN:{field}")

    body = {
        "policy": pol,
        "selected_reproduction_keys": list(selected),
        "baseline_keys": baseline_keys,
        "sample_keys": sample_keys,
    }
    return {
        **body,
        "reproduction_plan_fingerprint": canonical_hash(body),
        "status": "PLANNING_ONLY",
    }
