"""Analyzer contract for #4153: 21 matrix slots vs 19 physical parameter sets."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash
from tools.arvp_vacation.sensitivity_campaign_grid import (
    EXPECTED_UNIQUE_VARIANTS,
    PHASE_BASELINE,
    PHASE_INTERACTION,
    PHASE_OFAT,
    VariantSpec,
    expand_variants,
)

ANALYZER_CONTRACT_VERSION = "cdb.sensitivity_campaign_analyzer.v1"
EXPECTED_PHYSICAL_PARAMETER_SETS = 19
EXPECTED_OVERLAPS = 2

# Trading parameters that define the physical configuration (excludes identity labels).
PHYSICAL_PARAM_KEYS = (
    "entry_lookback_minutes",
    "exit_lookback_minutes",
    "breakout_buffer",
    "min_minutes_between_entries",
)

ALLOWED_RESULT_FIELDS = (
    "gate_reason",
    "regime_distribution",
    "trade_count",
    "turnover",
    "fees",
    "spread",
    "slippage",
    "gross_pnl",
    "net_pnl",
    "profit_factor",
    "expectancy",
    "drawdown",
    "main_effect",
    "interaction_effect",
    "overfitting_risk_flag",
)


class SensitivityAnalyzerContractError(ValueError):
    """Fail-closed analyzer-contract violation."""


def physical_parameter_set_fingerprint(param_set: Mapping[str, Any]) -> str:
    body = {k: param_set[k] for k in PHYSICAL_PARAM_KEYS if k in param_set}
    if len(body) != len(PHYSICAL_PARAM_KEYS):
        missing = [k for k in PHYSICAL_PARAM_KEYS if k not in param_set]
        raise SensitivityAnalyzerContractError(
            f"physical param set missing keys: {missing}"
        )
    return canonical_hash(body)


def slot_metadata_for_variant(variant: VariantSpec) -> dict[str, Any]:
    scenario_id = str(variant.param_set.get("scenario_id") or "baseline")
    return {
        "slot_id": variant.variant_id,
        "phase": variant.phase,
        "label": variant.label,
        "scenario_id": scenario_id,
        "physical_parameter_set_fingerprint": physical_parameter_set_fingerprint(
            variant.param_set
        ),
    }


def classify_overlap_slots(
    variants: Sequence[VariantSpec] | None = None,
) -> dict[str, Any]:
    items = list(variants) if variants is not None else expand_variants()
    if len(items) != EXPECTED_UNIQUE_VARIANTS:
        raise SensitivityAnalyzerContractError(
            f"expected {EXPECTED_UNIQUE_VARIANTS} slots, got {len(items)}"
        )

    by_fp: dict[str, list[dict[str, Any]]] = {}
    slots = []
    for v in items:
        meta = slot_metadata_for_variant(v)
        slots.append(meta)
        by_fp.setdefault(meta["physical_parameter_set_fingerprint"], []).append(meta)

    overlaps = {fp: metas for fp, metas in by_fp.items() if len(metas) > 1}
    if len(by_fp) != EXPECTED_PHYSICAL_PARAMETER_SETS:
        raise SensitivityAnalyzerContractError(
            f"physical sets {len(by_fp)} != {EXPECTED_PHYSICAL_PARAMETER_SETS}"
        )
    if len(overlaps) != EXPECTED_OVERLAPS:
        raise SensitivityAnalyzerContractError(
            f"overlaps {len(overlaps)} != {EXPECTED_OVERLAPS}"
        )

    return {
        "analyzer_contract_version": ANALYZER_CONTRACT_VERSION,
        "matrix_slots": EXPECTED_UNIQUE_VARIANTS,
        "physical_parameter_sets": EXPECTED_PHYSICAL_PARAMETER_SETS,
        "overlaps": EXPECTED_OVERLAPS,
        "slots": slots,
        "overlap_groups": [
            {
                "physical_parameter_set_fingerprint": fp,
                "slots": metas,
            }
            for fp, metas in sorted(overlaps.items())
        ],
        "rules": {
            "main_effects_phases": [PHASE_BASELINE, PHASE_OFAT],
            "interaction_effects_phases": [PHASE_INTERACTION],
            "no_double_weight_global_ranking": True,
            "report_must_state_21_slots_19_sets_2_overlaps": True,
            "determinism_separate_from_effect_aggregation": True,
        },
        "allowed_result_fields": list(ALLOWED_RESULT_FIELDS),
    }


def assert_results_bindings(
    *,
    results: Sequence[Mapping[str, Any]],
    manifest_fingerprint: str,
    run_plan_fingerprint: str,
    authorization_fingerprint: str,
    expected_run_keys: Sequence[str],
) -> None:
    """Fail-closed gate before analysis: bindings + no stale/foreign results."""
    if not results:
        raise SensitivityAnalyzerContractError("ANALYZER_NO_RESULTS")

    seen: set[str] = set()
    for row in results:
        for key, expected in (
            ("manifest_fingerprint", manifest_fingerprint),
            ("run_plan_fingerprint", run_plan_fingerprint),
            ("authorization_fingerprint", authorization_fingerprint),
        ):
            if row.get(key) != expected:
                raise SensitivityAnalyzerContractError(
                    f"ANALYZER_STALE_OR_FOREIGN_RESULT:{key}"
                )
        run_key = str(row.get("run_key") or "")
        if not run_key:
            raise SensitivityAnalyzerContractError("ANALYZER_RESULT_MISSING_RUN_KEY")
        if run_key in seen:
            raise SensitivityAnalyzerContractError(
                f"ANALYZER_DUPLICATE_RUN_KEY:{run_key}"
            )
        seen.add(run_key)

    expected = set(expected_run_keys)
    if seen != expected:
        missing = sorted(expected - seen)
        extra = sorted(seen - expected)
        raise SensitivityAnalyzerContractError(
            f"ANALYZER_RUN_KEY_SET_MISMATCH missing={missing[:5]} extra={extra[:5]}"
        )


def effect_partition(slots: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    main_ids = [
        str(s["slot_id"])
        for s in slots
        if s.get("phase") in (PHASE_BASELINE, PHASE_OFAT)
    ]
    ix_ids = [str(s["slot_id"]) for s in slots if s.get("phase") == PHASE_INTERACTION]
    return {"main_effect_slot_ids": main_ids, "interaction_effect_slot_ids": ix_ids}


def ranking_weights_for_slots(
    slots: Sequence[Mapping[str, Any]],
) -> dict[str, float]:
    """Physical-set-aware weights: overlapping slots share weight 1.0 total."""
    by_fp: dict[str, list[str]] = {}
    for s in slots:
        fp = str(s["physical_parameter_set_fingerprint"])
        by_fp.setdefault(fp, []).append(str(s["slot_id"]))
    weights: dict[str, float] = {}
    for _fp, slot_ids in by_fp.items():
        share = 1.0 / float(len(slot_ids))
        for sid in slot_ids:
            weights[sid] = share
    return weights
