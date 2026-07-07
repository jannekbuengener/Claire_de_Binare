"""Fixture-based ARVP scenario-pack matrix contract tests (#3826).

Strategy x scenario-pack coverage without live data, backtests, or ranking claims.
"""

from __future__ import annotations

import itertools

import pytest

from core.replay.scenario_packs import BUILTIN_SCENARIO_IDS, ScenarioPackError, get_scenario_pack
from services.validation.strategy_replay_runner import (
    ARVPReplayConfig,
    ReplayRunnerError,
    _apply_scenario_overrides,
)

from tests.unit.arvp._arvp_scenario_pack_matrix_helpers import (
    assert_matrix_fixture_covers_builtin_packs,
    classify_scenario_pack_cell,
    load_scenario_pack_matrix_fixture,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_matrix_fixture_lists_all_five_builtin_packs() -> None:
    fixture = load_scenario_pack_matrix_fixture()
    assert set(fixture["builtin_scenario_ids"]) == set(BUILTIN_SCENARIO_IDS)
    assert_matrix_fixture_covers_builtin_packs()


@pytest.mark.parametrize("scenario_id", BUILTIN_SCENARIO_IDS)
def test_each_builtin_pack_resolves_with_provenance(scenario_id: str) -> None:
    spec = get_scenario_pack(scenario_id)
    assert spec.scenario_id == scenario_id
    assert spec.config_overrides["pack_id"] == scenario_id
    assert spec.config_overrides["pack_version"] == "1"


def test_unknown_scenario_pack_fails_closed() -> None:
    with pytest.raises(ScenarioPackError, match="Unknown scenario pack"):
        get_scenario_pack("synthetic_random_stress")


@pytest.mark.parametrize("entry", load_scenario_pack_matrix_fixture()["supported_examples"])
def test_supported_matrix_examples_classify_supported(entry: dict) -> None:
    status, reason = classify_scenario_pack_cell(
        strategy_id=entry["strategy_id"],
        adapter_id=entry["adapter_id"],
        scenario_id=entry["scenario_id"],
    )
    assert status == "supported", reason


@pytest.mark.parametrize(
    "entry", load_scenario_pack_matrix_fixture()["unsupported_examples"]
)
def test_unsupported_matrix_examples_fail_closed(entry: dict) -> None:
    status, _reason = classify_scenario_pack_cell(
        strategy_id=entry["strategy_id"],
        adapter_id=entry["adapter_id"],
        scenario_id=entry["scenario_id"],
    )
    assert status == "unsupported"


@pytest.mark.parametrize("entry", load_scenario_pack_matrix_fixture()["blocked_examples"])
def test_blocked_matrix_examples_fail_closed(entry: dict) -> None:
    status, _reason = classify_scenario_pack_cell(
        strategy_id=entry["strategy_id"],
        adapter_id=entry["adapter_id"],
        scenario_id=entry["scenario_id"],
    )
    assert status == "blocked"


def test_full_canonical_strategy_x_pack_grid_is_supported() -> None:
    fixture = load_scenario_pack_matrix_fixture()
    canonical = fixture["canonical_adapter_by_strategy"]
    unsupported: list[str] = []
    for strategy_id, adapter_id in canonical.items():
        for scenario_id in BUILTIN_SCENARIO_IDS:
            status, reason = classify_scenario_pack_cell(
                strategy_id=strategy_id,
                adapter_id=adapter_id,
                scenario_id=scenario_id,
                canonical_adapter_by_strategy=canonical,
            )
            if status != "supported":
                unsupported.append(f"{strategy_id}/{adapter_id}/{scenario_id}: {reason}")
    assert unsupported == []


def test_adapter_id_validation_rejects_unknown_adapter() -> None:
    cfg = ARVPReplayConfig(
        input_candles_file="x.json",
        strategy_id="primary_breakout_v1",
        adapter_id="not_registered_adapter",
    )
    with pytest.raises(ValueError, match="unsupported adapter_id"):
        cfg.validate()


def test_unsupported_scenario_override_semantics_fail_closed() -> None:
    cfg = ARVPReplayConfig(input_candles_file="x.json")
    with pytest.raises(ReplayRunnerError, match="not currently supported"):
        _apply_scenario_overrides(cfg, {"feed_gap_seconds": 30})


def test_cross_adapter_pairs_are_not_silent_supported() -> None:
    fixture = load_scenario_pack_matrix_fixture()
    canonical = fixture["canonical_adapter_by_strategy"]
    adapters = sorted({v for v in canonical.values()})
    mismatches = 0
    for strategy_id, expected in canonical.items():
        for adapter_id in adapters:
            if adapter_id == expected:
                continue
            status, _ = classify_scenario_pack_cell(
                strategy_id=strategy_id,
                adapter_id=adapter_id,
                scenario_id="baseline",
                canonical_adapter_by_strategy=canonical,
            )
            if status == "supported":
                pytest.fail(f"unexpected supported mismatch: {strategy_id}/{adapter_id}")
            mismatches += 1
    assert mismatches == len(canonical) * (len(adapters) - 1)


def test_matrix_has_no_duplicate_cells() -> None:
    fixture = load_scenario_pack_matrix_fixture()
    cells = {
        (entry["strategy_id"], entry["adapter_id"], entry["scenario_id"])
        for entry in itertools.chain(
            fixture["supported_examples"],
            fixture["unsupported_examples"],
            fixture["blocked_examples"],
        )
    }
    total = (
        len(fixture["supported_examples"])
        + len(fixture["unsupported_examples"])
        + len(fixture["blocked_examples"])
    )
    assert len(cells) == total
