"""Unit tests for correlation ledger campaign/lane attribution (#3960)."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock

import pytest

from core.replay.correlation_ledger_attribution import (
    NO_CHAIN_REASON_NO_SIGNALS,
    NO_CHAIN_REASON_RISK_BLOCKED,
    aggregate_lane_campaign_evidence,
    build_decision_ledger_payload,
    build_signal_ledger_payload,
    resolve_campaign_id,
)


def _donchian_blocked_rows(count: int = 50) -> list[dict]:
    rows: list[dict] = []
    for idx in range(count):
        signal_id = f"sig-don-{idx:03d}"
        rows.append(
            {
                "event_type": "SIGNAL",
                "payload": {
                    "signal_id": signal_id,
                    "strategy_id": "donchian_breakout_v1",
                    "bot_id": "np-donchian-parallel-01",
                    "campaign_id": "arvp_3912_np_parallel_donchian_20260709_1327",
                    "metadata": {"config_hash": "cfg-donchian-parallel-v1"},
                },
            }
        )
        rows.append(
            {
                "event_type": "DECISION",
                "payload": {
                    "signal_id": signal_id,
                    "strategy_id": "donchian_breakout_v1",
                    "bot_id": "np-donchian-parallel-01",
                    "campaign_id": "arvp_3912_np_parallel_donchian_20260709_1327",
                    "decision": "BLOCK",
                    "reason_code": "RC_001",
                    "metadata": {"config_hash": "cfg-donchian-parallel-v1"},
                },
            }
        )
    return rows


@pytest.mark.unit
def test_build_signal_ledger_payload_includes_campaign_id(monkeypatch) -> None:
    monkeypatch.setenv("CDB_CAMPAIGN_ID", "arvp_test_campaign")
    payload = build_signal_ledger_payload(
        {
            "signal_id": "sig-1",
            "strategy_id": "donchian_breakout_v1",
            "bot_id": "np-donchian-parallel-01",
            "metadata": {"config_hash": "cfg-1"},
        }
    )
    assert payload["campaign_id"] == "arvp_test_campaign"
    assert payload["strategy_id"] == "donchian_breakout_v1"


@pytest.mark.unit
def test_build_decision_ledger_payload_includes_block_reason(monkeypatch) -> None:
    monkeypatch.setenv("CDB_CAMPAIGN_ID", "arvp_test_campaign")
    signal = MagicMock()
    signal.strategy_id = "donchian_breakout_v1"
    signal.bot_id = "np-donchian-parallel-01"
    signal.metadata = {"config_hash": "cfg-1"}
    payload = build_decision_ledger_payload(
        {"signal_id": "sig-1", "decision_id": "dec-1"},
        signal=signal,
        decision="BLOCK",
        reason_code="RC_001",
    )
    assert payload["decision"] == "BLOCK"
    assert payload["reason_code"] == "RC_001"
    assert payload["campaign_id"] == "arvp_test_campaign"
    assert payload["metadata"]["config_hash"] == "cfg-1"


@pytest.mark.unit
def test_donchian_fixture_blocks_by_reason_rc_001() -> None:
    summary = aggregate_lane_campaign_evidence(
        _donchian_blocked_rows(50),
        bot_id="np-donchian-parallel-01",
        strategy_id="donchian_breakout_v1",
        campaign_id="arvp_3912_np_parallel_donchian_20260709_1327",
    )
    assert summary["signals_emitted"] == 50
    assert summary["decisions_total"] == 50
    assert summary["blocks_total"] == 50
    assert summary["blocks_by_reason"]["RC_001"] == 50
    assert summary["no_chain_reason"] == NO_CHAIN_REASON_RISK_BLOCKED


@pytest.mark.unit
def test_pb1_zero_signals_reports_idle_reason() -> None:
    summary = aggregate_lane_campaign_evidence(
        [],
        bot_id="np-pb1-parallel-01",
        strategy_id="primary_breakout_v1",
        campaign_id="arvp_3912_np_parallel_pb1_20260709_1327",
    )
    assert summary["signals_emitted"] == 0
    assert summary["no_chain_reason"] == NO_CHAIN_REASON_NO_SIGNALS


@pytest.mark.unit
def test_resolve_campaign_id_empty_when_unset(monkeypatch) -> None:
    monkeypatch.delenv("CDB_CAMPAIGN_ID", raising=False)
    assert resolve_campaign_id() is None


@pytest.mark.unit
def test_signal_service_persist_payload_json_includes_campaign_id(monkeypatch) -> None:
    monkeypatch.setenv("CDB_CAMPAIGN_ID", "arvp_signal_campaign")
    from services.signal.models import Signal

    payload = build_signal_ledger_payload(
        Signal(
            signal_id="sig-test",
            strategy_id="donchian_breakout_v1",
            bot_id="np-donchian-parallel-01",
            symbol="BTCUSDT",
            side="BUY",
            ts_ms=1_783_603_620_000,
            metadata={"config_hash": "cfg-1"},
        ).to_dict()
    )
    decoded = json.loads(json.dumps(payload))
    assert decoded["campaign_id"] == "arvp_signal_campaign"
