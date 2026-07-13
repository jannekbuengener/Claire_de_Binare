"""Tests for Batch-A strategy registry metadata (#4031 slice 2a)."""

from __future__ import annotations

import pytest

from core.replay.batch_a_strategy_registry import (
    ImplementationMode,
    assert_batch_a_executable,
    batch_a_strategy_ids,
    executable_batch_a_strategy_ids,
    get_batch_a_strategy,
    pending_batch_a_strategy_ids,
)

pytestmark = pytest.mark.unit


def test_registry_lists_all_ten_locked_candidates() -> None:
    assert len(batch_a_strategy_ids()) == 10


def test_only_implemented_runners_are_executable() -> None:
    executable = executable_batch_a_strategy_ids()
    pending = pending_batch_a_strategy_ids()
    assert len(executable) == 10
    assert len(pending) == 0
    assert executable.isdisjoint(pending)


@pytest.mark.parametrize(
    "strategy_id",
    sorted(executable_batch_a_strategy_ids()),
)
def test_implemented_candidates_are_executable(strategy_id: str) -> None:
    record = get_batch_a_strategy(strategy_id)
    assert record.executable
    assert record.runner_module is not None
    if record.implementation_mode in {
        ImplementationMode.REUSE_RESCREEN_CROSS_VENUE_WITH_PRIOR_NEGATIVE_EVIDENCE,
    }:
        assert record.adapter_id is not None


@pytest.mark.parametrize(
    "strategy_id",
    sorted(pending_batch_a_strategy_ids()),
)
def test_pending_candidates_cannot_be_executed(strategy_id: str) -> None:
    record = get_batch_a_strategy(strategy_id)
    assert not record.executable
    with pytest.raises(ValueError, match="implementation_pending"):
        assert_batch_a_executable(strategy_id)


def test_no_pending_candidates_remain() -> None:
    assert pending_batch_a_strategy_ids() == frozenset()


def test_unknown_strategy_raises_key_error() -> None:
    with pytest.raises(KeyError, match="Unknown Batch-A"):
        get_batch_a_strategy("not_a_batch_a_strategy")
