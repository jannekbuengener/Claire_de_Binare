"""Tests for Owner-ratified #4153 sensitivity campaign grid expansion.

test_id: tc_sensitivity_campaign_grid_001
test_type: schutz|bauteil
cdb_area: arvp/validation-research
issue_ref: #4153
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import copy

import pytest

from tools.arvp_vacation.sensitivity_campaign_grid import (
    EXPECTED_RUN_COUNT,
    EXPECTED_UNIQUE_VARIANTS,
    EXPANSION_MODE,
    FORBIDDEN_PARAMETER_IDS,
    MAX_RUN_COUNT,
    OWNER_RATIFICATION_COMMENT_ID,
    STRATEGY_ID,
    SensitivityGridError,
    assert_manifest_matches_ratified_grid,
    expand_runs,
    expand_variants,
    parameter_grid_for_manifest,
    run_key,
    variant_breakdown,
)
from tools.market_data.development_window_selector import (
    LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
)


def test_expand_variants_exact_21_breakdown() -> None:
    variants = expand_variants()
    breakdown = variant_breakdown(variants)
    assert breakdown == {
        "baseline": 1,
        "ofat_entry": 3,
        "ofat_exit": 2,
        "ofat_buffer": 4,
        "ofat_cooldown": 3,
        "interaction_entry_lookback_x_buffer": 4,
        "interaction_exit_lookback_x_cooldown": 4,
        "unique_total": 21,
    }
    assert len(variants) == EXPECTED_UNIQUE_VARIANTS
    assert variants[0].phase == "baseline"
    assert variants[0].param_set["entry_lookback_minutes"] == 240
    assert variants[0].param_set["breakout_buffer"] == 0.0005


def test_ofat_skips_baseline_equivalents() -> None:
    variants = expand_variants()
    ofat = [v for v in variants if v.phase == "ofat"]
    for variant in ofat:
        baseline = {
            "entry_lookback_minutes": 240,
            "exit_lookback_minutes": 120,
            "breakout_buffer": 0.0005,
            "min_minutes_between_entries": 60,
        }
        changed = {
            k: variant.param_set[k]
            for k in baseline
            if variant.param_set[k] != baseline[k]
        }
        assert len(changed) == 1


def test_interaction_not_deduped_against_ofat_slots() -> None:
    variants = expand_variants()
    assert sum(1 for v in variants if v.phase == "interaction") == 8
    # Matrix slots remain 21 even if some param sets could overlap OFAT endpoints.
    assert len(variants) == 21


def test_expand_runs_819_unique_keys() -> None:
    runs = expand_runs(
        campaign_id="arvp-sensitivity-4153-v1",
        window_ids=LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
    )
    assert len(runs) == EXPECTED_RUN_COUNT == MAX_RUN_COUNT
    keys = [r.run_key for r in runs]
    assert len(keys) == len(set(keys))
    # Window-major order: first window, baseline first.
    assert runs[0].window_id == LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS[0]
    assert runs[0].variant.phase == "baseline"
    assert runs[20].window_id == LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS[0]
    assert runs[21].window_id == LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS[1]


def test_run_key_changes_with_parameter_semantics() -> None:
    base = {
        "entry_lookback_minutes": 240,
        "exit_lookback_minutes": 120,
        "breakout_buffer": 0.0005,
        "min_minutes_between_entries": 60,
        "scenario_id": "baseline",
        "strategy_id": STRATEGY_ID,
    }
    a = run_key(
        campaign_id="c",
        window_id="w",
        strategy_id=STRATEGY_ID,
        param_set=base,
        scenario_id="baseline",
        phase="baseline",
        label="baseline",
    )
    changed = dict(base)
    changed["entry_lookback_minutes"] = 60
    b = run_key(
        campaign_id="c",
        window_id="w",
        strategy_id=STRATEGY_ID,
        param_set=changed,
        scenario_id="baseline",
        phase="ofat",
        label="ofat_pb1_entry_lookback_60",
    )
    assert a != b
    # Phase/label distinguish otherwise-identical param sets.
    c = run_key(
        campaign_id="c",
        window_id="w",
        strategy_id=STRATEGY_ID,
        param_set=changed,
        scenario_id="baseline",
        phase="interaction",
        label="ix_other",
    )
    assert b != c


def test_assert_manifest_rejects_cdb021_and_extra_dimension() -> None:
    grid = parameter_grid_for_manifest()
    manifest = {
        "expansion": {
            "mode": EXPANSION_MODE,
            "expected_run_count": 819,
            "max_run_count": 819,
            "unique_variant_count": 21,
        },
        "strategies": [STRATEGY_ID],
        "parameter_families": [
            {
                "family_id": "execution_scenario_pack",
                "parameter_ids": ["CDB-021"],
                "change_authority": "RESEARCH_ALLOWED",
            }
        ],
        "parameter_grid": grid,
        "design": {"interaction_groups": []},
        "owner_ratification": {
            "issue_comment_id": OWNER_RATIFICATION_COMMENT_ID,
        },
    }
    with pytest.raises(SensitivityGridError, match="CDB-021"):
        assert_manifest_matches_ratified_grid(manifest)

    bad = copy.deepcopy(manifest)
    bad["parameter_families"] = []
    bad["parameter_grid"] = copy.deepcopy(grid)
    bad["parameter_grid"]["dimensions"].append(
        copy.deepcopy(bad["parameter_grid"]["dimensions"][0])
    )
    with pytest.raises(SensitivityGridError, match="4 dimensions"):
        assert_manifest_matches_ratified_grid(bad)


def test_forbidden_parameter_ids_include_cdb021() -> None:
    assert "CDB-021" in FORBIDDEN_PARAMETER_IDS
