"""P1 campaign attribution + block-reason evidence contract tests (#3960)."""

from __future__ import annotations

import pytest

from tools.arvp_campaign_supervisor import _build_cycle_entry

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
    lane_campaign_evidence: dict | None = None,
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
                "campaign_id_propagated_to_ledger": True,
            },
            "lane_campaign_evidence": lane_campaign_evidence,
        },
    }


@pytest.mark.unit
@pytest.mark.contract
def test_mixed_lane_supervisor_keeps_global_lane_and_block_reason_separate() -> None:
    donchian_lane_evidence = {
        "signals_emitted": 50,
        "decisions_total": 50,
        "approvals": 0,
        "blocks_total": 50,
        "blocks_by_reason": {"RC_001": 50},
        "orders": 0,
        "fills": 0,
        "no_chain_reason": "RISK_BLOCKED_NO_PROMOTABLE_CHAIN",
    }
    pb1_lane_evidence = {
        "signals_emitted": 0,
        "decisions_total": 0,
        "approvals": 0,
        "blocks_total": 0,
        "blocks_by_reason": {},
        "orders": 0,
        "fills": 0,
        "no_chain_reason": "NO_SIGNALS_OR_GATE_IDLE",
    }

    donchian_entry = _build_cycle_entry(
        1,
        [
            _ledger_probe(
                global_count=0,
                bot_count=50,
                strategy_count=50,
                lane_campaign_evidence=donchian_lane_evidence,
                bot_id=_DONCHIAN_MANIFEST["bot_id"],
                strategy_id=_DONCHIAN_MANIFEST["strategy_id"],
            )
        ],
        "TIMEOUT_NO_CHAIN",
        _DONCHIAN_MANIFEST,
    )
    pb1_entry = _build_cycle_entry(
        1,
        [
            _ledger_probe(
                global_count=0,
                bot_count=0,
                strategy_count=0,
                lane_campaign_evidence=pb1_lane_evidence,
                bot_id=_PB1_MANIFEST["bot_id"],
                strategy_id=_PB1_MANIFEST["strategy_id"],
            )
        ],
        "TIMEOUT_NO_CHAIN",
        _PB1_MANIFEST,
    )

    assert donchian_entry["event_count_since_start"] == 0
    assert donchian_entry["event_count_since_start_lane"] == 50
    assert donchian_entry["lane_campaign_evidence"]["blocks_by_reason"]["RC_001"] == 50
    assert donchian_entry["no_chain_reason"] == "RISK_BLOCKED_NO_PROMOTABLE_CHAIN"

    assert pb1_entry["event_count_since_start_lane"] == 0
    assert pb1_entry["lane_campaign_evidence"]["signals_emitted"] == 0
    assert pb1_entry["no_chain_reason"] == "NO_SIGNALS_OR_GATE_IDLE"


@pytest.mark.unit
@pytest.mark.contract
def test_supervisor_exposes_lane_campaign_evidence_shape() -> None:
    lane_evidence = {
        "campaign_id": _DONCHIAN_MANIFEST["campaign_id"],
        "bot_id": _DONCHIAN_MANIFEST["bot_id"],
        "strategy_id": _DONCHIAN_MANIFEST["strategy_id"],
        "signals_emitted": 50,
        "decisions_total": 50,
        "approvals": 0,
        "blocks_total": 50,
        "blocks_by_reason": {"RC_001": 50},
        "orders": 0,
        "fills": 0,
        "no_chain_reason": "RISK_BLOCKED_NO_PROMOTABLE_CHAIN",
    }
    entry = _build_cycle_entry(
        1,
        [
            _ledger_probe(
                global_count=0,
                bot_count=50,
                strategy_count=50,
                lane_campaign_evidence=lane_evidence,
                bot_id=_DONCHIAN_MANIFEST["bot_id"],
                strategy_id=_DONCHIAN_MANIFEST["strategy_id"],
            )
        ],
        "TIMEOUT_NO_CHAIN",
        _DONCHIAN_MANIFEST,
    )
    assert entry["lane_campaign_evidence"]["signals_emitted"] == 50
    assert entry["ledger_counts"]["lane_effective_since_start"] == 50
