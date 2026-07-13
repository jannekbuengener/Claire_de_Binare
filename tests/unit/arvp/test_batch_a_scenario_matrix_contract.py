"""Fixture-based Batch-A scenario matrix scaffold tests (#4031 slice 2a)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.replay.batch_a_strategy_registry import (
    batch_a_strategy_ids,
    executable_batch_a_strategy_ids,
    pending_batch_a_strategy_ids,
)
from core.replay.scenario_packs import BUILTIN_SCENARIO_IDS

pytestmark = [pytest.mark.unit, pytest.mark.contract]

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures/arvp/batch_a_scenario_matrix_v1.json"
)


@pytest.fixture
def matrix() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_matrix_lists_ten_batch_a_strategies(matrix: dict) -> None:
    assert len(matrix["batch_a_strategy_ids"]) == 10
    assert set(matrix["batch_a_strategy_ids"]) == set(batch_a_strategy_ids())


def test_stage_a_uses_baseline_and_pessimistic_only(matrix: dict) -> None:
    stage_a = set(matrix["stage_a_scenario_ids"])
    assert stage_a == {"baseline", "pessimistic_execution"}
    assert stage_a.issubset(set(BUILTIN_SCENARIO_IDS))
    excluded = set(matrix["excluded_stage_a_scenario_ids"])
    assert "feed_gap" in excluded


def test_implemented_and_pending_partition(matrix: dict) -> None:
    implemented = set(matrix["implemented_strategy_ids"])
    pending = set(matrix["implementation_pending_strategy_ids"])
    assert implemented == set(executable_batch_a_strategy_ids())
    assert pending == set(pending_batch_a_strategy_ids())
    assert implemented.isdisjoint(pending)


def test_pending_adapters_are_null(matrix: dict) -> None:
    adapters = matrix["canonical_adapter_by_strategy"]
    for strategy_id in matrix["implementation_pending_strategy_ids"]:
        assert adapters[strategy_id] is None


def test_development_selection_sha256_present(matrix: dict) -> None:
    assert matrix["development_selection_sha256"] == (
        "3e9ed68736b51fecb299d228c856be80a597cb1dc72fcba595453b856b58bd52"
    )
