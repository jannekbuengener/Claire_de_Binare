"""Runtime integration contract for fail-closed stop-loss requirements (#4182)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from core.domain.models import Signal
from core.safety.stop_loss_protection import STOP_LOSS_PROTECTION_BLOCK_REASON
from services.risk.config import RiskConfig
from services.risk.service import RiskManager
import services.risk.service as risk_service

pytestmark = [pytest.mark.integration, pytest.mark.contract]


def test_transport_payload_blocks_before_order_submission(
    mock_redis, mock_postgres
) -> None:
    """A protection-required transport payload never reaches order submission."""
    test_config = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=0.30,
        max_daily_drawdown_pct=0.05,
        stop_loss_pct=0.02,
    )
    with patch.object(risk_service, "config", test_config):
        manager = RiskManager()

    payload = {
        "type": "signal",
        "signal_id": "sig-stop-loss-runtime",
        "strategy_id": "test-strat",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "direction": "BUY",
        "strength": 0.8,
        "timestamp": 1700000000.0,
        "metadata": {
            "requires_stop_loss_protection": True,
            "stop_loss_pct": 0.02,
        },
    }
    signal = Signal.from_dict(payload)

    with (
        patch.object(manager, "_kill_switch_gate") as kill_switch_gate,
        patch.object(manager, "send_order") as send_order,
        patch.object(manager, "send_alert") as send_alert,
    ):
        order = manager.process_signal(signal, raw_payload=payload)
        if order is not None:
            manager.send_order(order)

    assert order is None
    kill_switch_gate.assert_not_called()
    send_order.assert_not_called()
    send_alert.assert_called_once()
    assert send_alert.call_args.args[1] == STOP_LOSS_PROTECTION_BLOCK_REASON
