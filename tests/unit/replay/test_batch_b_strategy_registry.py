"""Registry tests for Batch-B (#4372)."""

from __future__ import annotations

import pytest

from core.replay.batch_a_strategy_registry import batch_a_strategy_ids
from core.replay.batch_b_strategy_registry import (
    BATCH_B_STRATEGY_REGISTRY,
    batch_b_strategy_ids,
    executable_batch_b_strategy_ids,
    get_batch_b_strategy,
)
from core.replay.hh_hl_continuation_common import HH_HL_CONTINUATION_STRATEGY_ID

pytestmark = pytest.mark.unit


def test_batch_b_registry_contains_only_implemented_hh_hl() -> None:
    assert batch_b_strategy_ids() == {HH_HL_CONTINUATION_STRATEGY_ID}
    assert executable_batch_b_strategy_ids() == {HH_HL_CONTINUATION_STRATEGY_ID}
    record = get_batch_b_strategy(HH_HL_CONTINUATION_STRATEGY_ID)
    assert record.implementation_status.value == "implemented"
    assert "hh_hl_continuation" in (record.runner_module or "")


def test_batch_a_and_batch_b_strategy_ids_are_disjoint() -> None:
    """G3 / HARDEN_PR_4373_BEFORE_MERGE — no shared strategy_id across funnels."""
    overlap = set(batch_a_strategy_ids()) & set(batch_b_strategy_ids())
    assert overlap == set()


def test_executable_registry_is_subset_of_manifest_and_field_aligned() -> None:
    """Guard against parallel-registry drift vs the Batch-B identity lock."""
    import json
    from pathlib import Path

    manifest = json.loads(
        (
            Path(__file__).resolve().parents[3]
            / "docs/contracts/batch_b_funnel_manifest.v1.json"
        ).read_text(encoding="utf-8")
    )
    by_id = {row["strategy_id"]: row for row in manifest["candidates"]}
    for strategy_id in executable_batch_b_strategy_ids():
        assert strategy_id in by_id
        row = by_id[strategy_id]
        record = get_batch_b_strategy(strategy_id)
        assert row["implementation_status"] == "implemented"
        assert row["runner_module"] == record.runner_module
        assert row.get("parameter_source") == record.parameter_source


def test_unknown_batch_b_strategy_raises() -> None:
    with pytest.raises(KeyError):
        get_batch_b_strategy("not_a_batch_b_strategy")
    assert HH_HL_CONTINUATION_STRATEGY_ID in BATCH_B_STRATEGY_REGISTRY
