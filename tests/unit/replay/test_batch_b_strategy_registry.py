"""Registry tests for Batch-B (#4372)."""

from __future__ import annotations

import pytest

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


def test_unknown_batch_b_strategy_raises() -> None:
    with pytest.raises(KeyError):
        get_batch_b_strategy("not_a_batch_b_strategy")
    assert HH_HL_CONTINUATION_STRATEGY_ID in BATCH_B_STRATEGY_REGISTRY
