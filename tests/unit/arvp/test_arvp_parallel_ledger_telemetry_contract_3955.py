"""Contract tests for parallel campaign ledger telemetry (#3955 / #3912)."""

from __future__ import annotations

import pytest

from tools.arvp_campaign_supervisor import _build_cycle_entry, _ledger_activity_count


_PB1_MANIFEST = {
    "campaign_id": "arvp_3912_np_parallel_pb1_20260709_1327",
    "bot_id": "np-pb1-parallel-01",
    "strategy_id": "primary_breakout_v1",
}

_DONCHIAN_MANIFEST = {
    "campaign_id": "arvp_3912_np_parallel_donchian_20260709_1327",
    "bot_id": "np-donchian-parallel-01",
    "strategy_id": "donchian_breakout_v1",
}


def _ledger_probe(
  *,
  global_count: int,
  bot_count: int,
  strategy_count: int,
  bot_id: str,
  strategy_id: str,
) -> dict:
    return {
        "probe": "correlation_ledger",
        "status": "ok",
        "limitations": [],
        "evidence": {
            "events_since_campaign_start": global_count,
            "events_since_campaign_start_global": global_count,
            "events_since_campaign_start_bot_id": bot_count,
            "events_since_campaign_start_strategy_id": strategy_count,
            "ledger_attribution": {
                "bot_id": bot_id,
                "strategy_id": strategy_id,
                "campaign_id_propagated_to_ledger": False,
            },
        },
    }


@pytest.mark.unit
@pytest.mark.contract
def test_lane_effective_count_prefers_bot_id_over_global_zero() -> None:
    evidence = _ledger_probe(
        global_count=0,
        bot_count=50,
        strategy_count=50,
        bot_id=_DONCHIAN_MANIFEST["bot_id"],
        strategy_id=_DONCHIAN_MANIFEST["strategy_id"],
    )["evidence"]
    assert _ledger_activity_count(evidence, _DONCHIAN_MANIFEST) == 50


@pytest.mark.unit
@pytest.mark.contract
def test_supervisor_cycle_entry_exposes_lane_count_for_donchian() -> None:
    probes = [
        _ledger_probe(
            global_count=0,
            bot_count=50,
            strategy_count=50,
            bot_id=_DONCHIAN_MANIFEST["bot_id"],
            strategy_id=_DONCHIAN_MANIFEST["strategy_id"],
        )
    ]
    entry = _build_cycle_entry(1, probes, "CAMPAIGN_RUNNING", _DONCHIAN_MANIFEST)
    assert entry["event_count_since_start"] == 0
    assert entry["event_count_since_start_lane"] == 50
    assert entry["ledger_counts"]["bot_id_since_start"] == 50


@pytest.mark.unit
@pytest.mark.contract
def test_supervisor_cycle_entry_lane_zero_for_pb1_when_no_signals() -> None:
    probes = [
        _ledger_probe(
            global_count=0,
            bot_count=0,
            strategy_count=0,
            bot_id=_PB1_MANIFEST["bot_id"],
            strategy_id=_PB1_MANIFEST["strategy_id"],
        )
    ]
    entry = _build_cycle_entry(1, probes, "CAMPAIGN_RUNNING", _PB1_MANIFEST)
    assert entry["event_count_since_start_lane"] == 0
