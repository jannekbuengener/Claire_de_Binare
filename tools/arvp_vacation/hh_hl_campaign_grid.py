"""hh_hl_continuation_v1 campaign grid draft — baseline-only (#4374).

Spec freezes swing/cooldown/direction parameters. No OFAT, no interactions,
no #4153 21-slot copy. Owner Design-GO must ratify before executable freeze.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.replay.canonical_json import canonical_hash
from core.replay.hh_hl_continuation_common import (
    HH_HL_CONTINUATION_STRATEGY_ID,
    MIN_MINUTES_BETWEEN_ENTRIES,
    SWING_LEFT_BARS,
    SWING_RIGHT_BARS,
    frozen_hh_hl_parameters,
)

GRID_PROVIDER_ID = "hh_hl_baseline_only_grid_v1"
DESIGN_GO_NAME = "GO_HH_HL_CAMPAIGN_DESIGN"
GRID_STATUS = "HOLD_CAMPAIGN_GRID_OWNER_RATIFICATION_REQUIRED"
SCENARIO_ID = "baseline"

FORBIDDEN_VARIANTS: tuple[str, ...] = (
    "ofat_sweep",
    "interaction_combos",
    "copy_4153_21_slot_grid",
    "result_driven_parameter_selection",
    "optimization",
)


@dataclass(frozen=True, slots=True)
class HhHlVariantSpec:
    slot_id: str
    phase: str
    label: str
    scenario_id: str
    param_set: Mapping[str, Any]
    rationale: str
    physical_parameter_set_fingerprint: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "phase": self.phase,
            "label": self.label,
            "scenario_id": self.scenario_id,
            "param_set": dict(self.param_set),
            "rationale": self.rationale,
            "physical_parameter_set_fingerprint": (
                self.physical_parameter_set_fingerprint
            ),
        }


def _physical_fingerprint(param_set: Mapping[str, Any]) -> str:
    body = {
        "strategy_id": HH_HL_CONTINUATION_STRATEGY_ID,
        "param_set": dict(param_set),
    }
    return canonical_hash(body)


def expand_hh_hl_variants() -> tuple[HhHlVariantSpec, ...]:
    """Return the only canon-supported pilot variant: frozen baseline."""
    params = frozen_hh_hl_parameters()
    # Spec uses min_minutes_between_entries; prompt alias cooldown_minutes maps 1:1.
    assert int(params["swing_left_bars"]) == SWING_LEFT_BARS
    assert int(params["swing_right_bars"]) == SWING_RIGHT_BARS
    assert int(params["min_minutes_between_entries"]) == MIN_MINUTES_BETWEEN_ENTRIES
    assert params["trade_side_mode"] == "long_only"
    fp = _physical_fingerprint(params)
    return (
        HhHlVariantSpec(
            slot_id="hh_hl_baseline_001",
            phase="BASELINE",
            label="spec_frozen_baseline",
            scenario_id=SCENARIO_ID,
            param_set=params,
            rationale=(
                "Spec (#4372) freezes all parameters; first pilot admits only "
                "the baseline physical set. No OFAT/interactions without "
                f"{DESIGN_GO_NAME}."
            ),
            physical_parameter_set_fingerprint=fp,
        ),
    )


def grid_draft_report() -> dict[str, Any]:
    variants = expand_hh_hl_variants()
    return {
        "grid_provider_id": GRID_PROVIDER_ID,
        "strategy_id": HH_HL_CONTINUATION_STRATEGY_ID,
        "status": GRID_STATUS,
        "design_go_template_name": DESIGN_GO_NAME,
        "variant_count": len(variants),
        "variants": [v.as_dict() for v in variants],
        "forbidden_variants": list(FORBIDDEN_VARIANTS),
        "design_risks": [
            "Spec parameters are fixed; expanding the grid without Owner Design-GO "
            "would invent non-canon freedom.",
            "39-window Batch-A bank eligibility for hh_hl still requires Design-GO "
            "and local dataset proof.",
            "Baseline-only yields low statistical power; Analyzer may return "
            "INCONCLUSIVE by design.",
        ],
        "executable_manifest_allowed": False,
        "notes": (
            "Draft only. Ratify via GO_HH_HL_CAMPAIGN_DESIGN before freeze. "
            "Does not authorize Campaign Execute."
        ),
    }
