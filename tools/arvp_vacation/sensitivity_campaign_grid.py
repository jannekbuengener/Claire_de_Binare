"""Owner-ratified #4153 sensitivity campaign grid + deterministic expansion.

SSOT: GitHub issue comment 5175526900 (Owner Grid Ratification).
Does not execute campaigns. Does not authorize paper/live/echtgeld.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash, canonical_json_dumps

OWNER_RATIFICATION_COMMENT_ID = 5175526900
OWNER_RATIFICATION_URL = (
    "https://github.com/jannekbuengener/Claire_de_Binare/issues/4153"
    "#issuecomment-5175526900"
)
EXPANSION_MODE = "BASELINE_PLUS_OFAT_WITH_BOUNDED_INTERACTIONS"
STRATEGY_ID = "primary_breakout_v1"
SCENARIO_ID = "baseline"
EXPECTED_UNIQUE_VARIANTS = 21
EXPECTED_RUN_COUNT = 819
MAX_RUN_COUNT = 819

# Dimension order is ratificated: entry → exit → buffer → cooldown
DIMENSION_SPECS: tuple[dict[str, Any], ...] = (
    {
        "family_id": "pb1_entry_lookback",
        "parameter_ids": ["CDB-002"],
        "field": "entry_lookback_minutes",
        "unit": "minutes",
        "value_type": "int",
        "baseline": 240,
        "values": (60, 120, 180, 240),
        "change_authority": "RESEARCH_ALLOWED",
    },
    {
        "family_id": "pb1_exit_lookback",
        "parameter_ids": ["CDB-002"],
        "field": "exit_lookback_minutes",
        "unit": "minutes",
        "value_type": "int",
        "baseline": 120,
        "values": (60, 120, 180),
        "change_authority": "RESEARCH_ALLOWED",
    },
    {
        "family_id": "pb1_breakout_buffer",
        "parameter_ids": ["CDB-003"],
        "field": "breakout_buffer",
        "unit": "ratio",
        "value_type": "float",
        "baseline": Decimal("0.0005"),
        "values": (
            Decimal("0.0"),
            Decimal("0.0005"),
            Decimal("0.001"),
            Decimal("0.0015"),
            Decimal("0.002"),
        ),
        "change_authority": "RESEARCH_ALLOWED",
    },
    {
        "family_id": "pb1_entry_cooldown",
        "parameter_ids": ["CDB-003"],
        "field": "min_minutes_between_entries",
        "unit": "minutes",
        "value_type": "int",
        "baseline": 60,
        "values": (30, 60, 90, 120),
        "change_authority": "RESEARCH_ALLOWED",
    },
)

INTERACTION_GROUPS: tuple[dict[str, Any], ...] = (
    {
        "group_id": "entry_lookback_x_buffer",
        "fields": ("entry_lookback_minutes", "breakout_buffer"),
        "family_ids": ("pb1_entry_lookback", "pb1_breakout_buffer"),
        "combos": (
            (60, Decimal("0.0")),
            (60, Decimal("0.002")),
            (240, Decimal("0.0")),
            (240, Decimal("0.002")),
        ),
    },
    {
        "group_id": "exit_lookback_x_cooldown",
        "fields": ("exit_lookback_minutes", "min_minutes_between_entries"),
        "family_ids": ("pb1_exit_lookback", "pb1_entry_cooldown"),
        "combos": (
            (60, 30),
            (60, 120),
            (180, 30),
            (180, 120),
        ),
    },
)

PHASE_BASELINE = "baseline"
PHASE_OFAT = "ofat"
PHASE_INTERACTION = "interaction"

FORBIDDEN_PARAMETER_IDS = frozenset({"CDB-021"})


class SensitivityGridError(ValueError):
    """Fail-closed grid / expansion violation."""


def _json_number(value: Any) -> int | float:
    if isinstance(value, Decimal):
        as_float = float(value)
        # Prefer ints when exact.
        if value == value.to_integral_value():
            return int(value)
        return as_float
    if isinstance(value, bool):
        raise SensitivityGridError(f"bool is not a numeric campaign value: {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    raise SensitivityGridError(f"unsupported numeric type: {type(value)!r}")


def baseline_param_set() -> dict[str, Any]:
    out: dict[str, Any] = {"scenario_id": SCENARIO_ID, "strategy_id": STRATEGY_ID}
    for spec in DIMENSION_SPECS:
        out[str(spec["field"])] = _json_number(spec["baseline"])
    return out


def _values_equal(a: Any, b: Any) -> bool:
    return Decimal(str(a)) == Decimal(str(b))


@dataclass(frozen=True, slots=True)
class VariantSpec:
    variant_id: str
    phase: str
    label: str
    param_set: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "phase": self.phase,
            "label": self.label,
            "param_set": dict(self.param_set),
        }


@dataclass(frozen=True, slots=True)
class RunSpec:
    run_key: str
    window_id: str
    strategy_id: str
    variant: VariantSpec

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_key": self.run_key,
            "window_id": self.window_id,
            "strategy_id": self.strategy_id,
            "variant": self.variant.as_dict(),
        }


def expand_variants() -> list[VariantSpec]:
    """Return the ratified 21 matrix-slot variants (phase-distinguished).

    Interaction combos are intentionally NOT deduplicated against OFAT
    (Owner comment 5175526900).
    """
    variants: list[VariantSpec] = []
    baseline = baseline_param_set()
    variants.append(
        VariantSpec(
            variant_id="baseline",
            phase=PHASE_BASELINE,
            label="baseline",
            param_set=dict(baseline),
        )
    )

    ofat_counts = {"entry": 0, "exit": 0, "buffer": 0, "cooldown": 0}
    for spec in DIMENSION_SPECS:
        field = str(spec["field"])
        baseline_value = spec["baseline"]
        family = str(spec["family_id"])
        for value in spec["values"]:
            if _values_equal(value, baseline_value):
                continue
            params = dict(baseline)
            params[field] = _json_number(value)
            label = f"ofat_{family}_{_label_token(value)}"
            variants.append(
                VariantSpec(
                    variant_id=label,
                    phase=PHASE_OFAT,
                    label=label,
                    param_set=params,
                )
            )
            if family == "pb1_entry_lookback":
                ofat_counts["entry"] += 1
            elif family == "pb1_exit_lookback":
                ofat_counts["exit"] += 1
            elif family == "pb1_breakout_buffer":
                ofat_counts["buffer"] += 1
            elif family == "pb1_entry_cooldown":
                ofat_counts["cooldown"] += 1

    expected_ofat = {
        "entry": 3,
        "exit": 2,
        "buffer": 4,
        "cooldown": 3,
    }
    if ofat_counts != expected_ofat:
        raise SensitivityGridError(
            f"HOLD_RATIFIED_GRID_COUNT_MISMATCH: OFAT counts {ofat_counts} "
            f"!= {expected_ofat}"
        )

    for group in INTERACTION_GROUPS:
        group_id = str(group["group_id"])
        fields = tuple(group["fields"])
        for combo in group["combos"]:
            params = dict(baseline)
            for field, value in zip(fields, combo, strict=True):
                params[field] = _json_number(value)
            label = f"ix_{group_id}_" + "_".join(_label_token(v) for v in combo)
            variants.append(
                VariantSpec(
                    variant_id=label,
                    phase=PHASE_INTERACTION,
                    label=label,
                    param_set=params,
                )
            )

    if len(variants) != EXPECTED_UNIQUE_VARIANTS:
        raise SensitivityGridError(
            "HOLD_RATIFIED_GRID_COUNT_MISMATCH: "
            f"unique variants {len(variants)} != {EXPECTED_UNIQUE_VARIANTS}"
        )
    return variants


def _label_token(value: Any) -> str:
    if isinstance(value, Decimal):
        text = format(value, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text.replace(".", "p")
    return str(value).replace(".", "p")


def variant_breakdown(variants: Sequence[VariantSpec] | None = None) -> dict[str, int]:
    items = list(variants) if variants is not None else expand_variants()
    return {
        "baseline": sum(1 for v in items if v.phase == PHASE_BASELINE),
        "ofat_entry": sum(
            1
            for v in items
            if v.phase == PHASE_OFAT and v.label.startswith("ofat_pb1_entry_lookback_")
        ),
        "ofat_exit": sum(
            1
            for v in items
            if v.phase == PHASE_OFAT and v.label.startswith("ofat_pb1_exit_lookback_")
        ),
        "ofat_buffer": sum(
            1
            for v in items
            if v.phase == PHASE_OFAT and v.label.startswith("ofat_pb1_breakout_buffer_")
        ),
        "ofat_cooldown": sum(
            1
            for v in items
            if v.phase == PHASE_OFAT and v.label.startswith("ofat_pb1_entry_cooldown_")
        ),
        "interaction_entry_lookback_x_buffer": sum(
            1
            for v in items
            if v.phase == PHASE_INTERACTION
            and v.label.startswith("ix_entry_lookback_x_buffer_")
        ),
        "interaction_exit_lookback_x_cooldown": sum(
            1
            for v in items
            if v.phase == PHASE_INTERACTION
            and v.label.startswith("ix_exit_lookback_x_cooldown_")
        ),
        "unique_total": len(items),
    }


def run_key(
    *,
    campaign_id: str,
    window_id: str,
    strategy_id: str,
    param_set: Mapping[str, Any],
    scenario_id: str,
    phase: str,
    label: str,
) -> str:
    """Deterministic run key per Owner ratification formula."""
    payload = "|".join(
        [
            campaign_id,
            window_id,
            strategy_id,
            canonical_json_dumps(dict(param_set)),
            scenario_id,
            phase,
            label,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def expand_runs(
    *,
    campaign_id: str,
    window_ids: Sequence[str],
    strategy_id: str = STRATEGY_ID,
    variants: Sequence[VariantSpec] | None = None,
) -> list[RunSpec]:
    resolved_variants = list(variants) if variants is not None else expand_variants()
    if len(resolved_variants) != EXPECTED_UNIQUE_VARIANTS:
        raise SensitivityGridError(
            "HOLD_RATIFIED_GRID_COUNT_MISMATCH: "
            f"variants {len(resolved_variants)} != {EXPECTED_UNIQUE_VARIANTS}"
        )
    runs: list[RunSpec] = []
    for window_id in window_ids:
        for variant in resolved_variants:
            key = run_key(
                campaign_id=campaign_id,
                window_id=window_id,
                strategy_id=strategy_id,
                param_set=variant.param_set,
                scenario_id=str(variant.param_set.get("scenario_id") or SCENARIO_ID),
                phase=variant.phase,
                label=variant.label,
            )
            runs.append(
                RunSpec(
                    run_key=key,
                    window_id=window_id,
                    strategy_id=strategy_id,
                    variant=variant,
                )
            )
    if len(runs) != EXPECTED_RUN_COUNT:
        raise SensitivityGridError(
            "HOLD_RATIFIED_GRID_COUNT_MISMATCH: "
            f"runs {len(runs)} != {EXPECTED_RUN_COUNT}"
        )
    keys = [r.run_key for r in runs]
    if len(keys) != len(set(keys)):
        raise SensitivityGridError("duplicate run keys in expansion")
    return runs


def assert_manifest_matches_ratified_grid(manifest: Mapping[str, Any]) -> None:
    """Fail closed if an executable manifest drifts from Owner ratification."""
    expansion = manifest.get("expansion") or {}
    if expansion.get("mode") != EXPANSION_MODE:
        raise SensitivityGridError(f"expansion.mode must be {EXPANSION_MODE}")
    if expansion.get("expected_run_count") != EXPECTED_RUN_COUNT:
        raise SensitivityGridError("expected_run_count must be 819")
    if expansion.get("max_run_count") != MAX_RUN_COUNT:
        raise SensitivityGridError("max_run_count must be 819")
    if expansion.get("unique_variant_count") != EXPECTED_UNIQUE_VARIANTS:
        raise SensitivityGridError("unique_variant_count must be 21")

    strategies = list(manifest.get("strategies") or [])
    if strategies != [STRATEGY_ID]:
        raise SensitivityGridError("strategies must be exactly [primary_breakout_v1]")

    # CDB-021 must be absent from parameter families / grid.
    for family in manifest.get("parameter_families") or []:
        for pid in family.get("parameter_ids") or []:
            if pid in FORBIDDEN_PARAMETER_IDS:
                raise SensitivityGridError("CDB-021 must be OUT")
        if "021" in str(family.get("family_id") or ""):
            raise SensitivityGridError("CDB-021 family must be OUT")

    grid = manifest.get("parameter_grid") or {}
    dims = list(grid.get("dimensions") or [])
    if len(dims) != 4:
        raise SensitivityGridError("parameter_grid must have exactly 4 dimensions")

    expected_fields = [str(s["field"]) for s in DIMENSION_SPECS]
    actual_fields = [str(d.get("field")) for d in dims]
    if actual_fields != expected_fields:
        raise SensitivityGridError(
            f"parameter_grid field order/identity mismatch: {actual_fields}"
        )

    for spec, dim in zip(DIMENSION_SPECS, dims, strict=True):
        if dim.get("family_id") != spec["family_id"]:
            raise SensitivityGridError(f"family_id mismatch for {spec['field']}")
        if list(dim.get("parameter_ids") or []) != list(spec["parameter_ids"]):
            raise SensitivityGridError(f"parameter_ids mismatch for {spec['field']}")
        if not _values_equal(dim.get("baseline"), spec["baseline"]):
            raise SensitivityGridError(f"baseline mismatch for {spec['field']}")
        declared_values = list(dim.get("values") or [])
        expected_values = [_json_number(v) for v in spec["values"]]
        if len(declared_values) != len(expected_values):
            raise SensitivityGridError(f"values length mismatch for {spec['field']}")
        for got, exp in zip(declared_values, expected_values, strict=True):
            if not _values_equal(got, exp):
                raise SensitivityGridError(
                    f"values mismatch for {spec['field']}: {got} != {exp}"
                )

    groups = list((manifest.get("design") or {}).get("interaction_groups") or [])
    if len(groups) != 2:
        raise SensitivityGridError("exactly two interaction groups required")
    for expected, got in zip(INTERACTION_GROUPS, groups, strict=True):
        if got.get("group_id") != expected["group_id"]:
            raise SensitivityGridError("interaction group_id mismatch")
        if tuple(got.get("family_ids") or ()) != tuple(expected["family_ids"]):
            raise SensitivityGridError("interaction family_ids mismatch")
        combos = got.get("combos") or []
        if len(combos) != len(expected["combos"]):
            raise SensitivityGridError("interaction combo count mismatch")
        for exp_combo, got_combo in zip(expected["combos"], combos, strict=True):
            if len(got_combo) != len(exp_combo):
                raise SensitivityGridError("interaction combo arity mismatch")
            for ev, gv in zip(exp_combo, got_combo, strict=True):
                if not _values_equal(ev, gv):
                    raise SensitivityGridError(
                        f"interaction combo mismatch in {expected['group_id']}"
                    )

    ratification = manifest.get("owner_ratification") or {}
    if ratification.get("issue_comment_id") != OWNER_RATIFICATION_COMMENT_ID:
        raise SensitivityGridError("owner_ratification.issue_comment_id mismatch")


def parameter_families_for_manifest() -> list[dict[str, Any]]:
    """Legacy-compatible parameter_families view for schema/preflight authority checks."""
    families: list[dict[str, Any]] = []
    for spec in DIMENSION_SPECS:
        values = [_json_number(v) for v in spec["values"]]
        families.append(
            {
                "family_id": spec["family_id"],
                "parameter_ids": list(spec["parameter_ids"]),
                "value_range": {
                    "min": values[0],
                    "max": values[-1],
                    "unit": spec["unit"],
                },
                "step": (
                    _json_number(values[1] - values[0])
                    if len(values) > 1
                    else _json_number(1)
                ),
                "change_authority": spec["change_authority"],
                "notes": (
                    f"Owner-ratified discrete values for {spec['field']}; "
                    f"comment {OWNER_RATIFICATION_COMMENT_ID}"
                ),
            }
        )
    return families


def parameter_grid_for_manifest() -> dict[str, Any]:
    dimensions = []
    for spec in DIMENSION_SPECS:
        dimensions.append(
            {
                "family_id": spec["family_id"],
                "parameter_ids": list(spec["parameter_ids"]),
                "field": spec["field"],
                "unit": spec["unit"],
                "value_type": spec["value_type"],
                "baseline": _json_number(spec["baseline"]),
                "values": [_json_number(v) for v in spec["values"]],
                "change_authority": spec["change_authority"],
                "ofat": True,
            }
        )
    return {
        "cdb_021": "OUT",
        "dimensions": dimensions,
        "owner_ratification_comment_id": OWNER_RATIFICATION_COMMENT_ID,
    }


def interaction_groups_for_manifest() -> list[dict[str, Any]]:
    out = []
    for group in INTERACTION_GROUPS:
        out.append(
            {
                "group_id": group["group_id"],
                "family_ids": list(group["family_ids"]),
                "fields": list(group["fields"]),
                "combos": [
                    [_json_number(v) for v in combo] for combo in group["combos"]
                ],
            }
        )
    return out


def expansion_fingerprint_body() -> str:
    """Stable hash over ratified expansion semantics (debug/evidence helper)."""
    return canonical_hash(
        {
            "mode": EXPANSION_MODE,
            "dimensions": parameter_grid_for_manifest(),
            "interaction_groups": interaction_groups_for_manifest(),
            "unique_variant_count": EXPECTED_UNIQUE_VARIANTS,
            "expected_run_count": EXPECTED_RUN_COUNT,
        }
    )
