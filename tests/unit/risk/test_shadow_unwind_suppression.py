"""LR-030: Shadow-mode unwind suppression tests.

Tests verify that:
- _trigger_proactive_unwind() is suppressed in shadow mode with log
- _maybe_auto_unwind() is suppressed in shadow mode with log
- Both still work in paper mode (regression guard via send_order seam)
"""

from __future__ import annotations

import copy
import logging
from unittest.mock import MagicMock

import pytest

from services.risk.service import RiskManager, risk_state, stats


@pytest.fixture
def _snapshot_risk_globals():
    """Snapshot and restore shared module-level state to prevent test leaks."""
    positions_backup = copy.copy(risk_state.positions)
    last_prices_backup = copy.copy(risk_state.last_prices)
    pending_orders_backup = risk_state.pending_orders
    stats_backup = copy.copy(stats)

    yield

    risk_state.positions = positions_backup
    risk_state.last_prices = last_prices_backup
    risk_state.pending_orders = pending_orders_backup
    stats.clear()
    stats.update(stats_backup)


@pytest.fixture
def risk_manager(_snapshot_risk_globals):
    """Create a minimal RiskManager with mocked dependencies."""
    rm = RiskManager.__new__(RiskManager)
    rm.config = MagicMock()
    rm.config.paper_auto_unwind = True
    rm.config.stop_loss_pct = 0.02
    rm.redis_client = MagicMock()
    rm._circuit_shutdown_emitted = False
    # Patch send_order as the business seam for order emission
    rm.send_order = MagicMock()
    return rm


@pytest.fixture
def _shadow_env(monkeypatch: pytest.MonkeyPatch):
    """Set RUN_MODE=shadow so _resolve_contract_run_mode() returns 'shadow'."""
    monkeypatch.setenv("RUN_MODE", "shadow")
    monkeypatch.delenv("TRADING_MODE", raising=False)


@pytest.fixture
def _paper_env(monkeypatch: pytest.MonkeyPatch):
    """Set RUN_MODE=paper so _resolve_contract_run_mode() returns 'paper'."""
    monkeypatch.setenv("RUN_MODE", "paper")
    monkeypatch.delenv("TRADING_MODE", raising=False)


# --- Proactive unwind ---


@pytest.mark.unit
@pytest.mark.usefixtures("_shadow_env")
def test_proactive_unwind_suppressed_in_shadow(
    risk_manager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Proactive unwind must be suppressed in shadow mode, with log."""
    risk_state.positions = {"BTCUSDT": 0.01}
    risk_state.last_prices = {"BTCUSDT": 50000.0}
    caplog.set_level(logging.INFO)

    risk_manager._trigger_proactive_unwind()

    risk_manager.send_order.assert_not_called()
    assert "Proactive unwind suppressed" in caplog.text
    assert "shadow" in caplog.text


@pytest.mark.unit
@pytest.mark.usefixtures("_paper_env")
def test_proactive_unwind_works_in_paper(
    risk_manager,
) -> None:
    """Proactive unwind must still work in paper mode (regression guard)."""
    risk_state.positions = {"BTCUSDT": 0.01}
    risk_state.last_prices = {"BTCUSDT": 50000.0}
    risk_state.pending_orders = 0
    stats["orders_approved"] = 0

    risk_manager._trigger_proactive_unwind()

    risk_manager.send_order.assert_called_once()


# --- Reactive unwind ---


@pytest.mark.unit
@pytest.mark.usefixtures("_shadow_env")
def test_reactive_unwind_suppressed_in_shadow(
    risk_manager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Reactive unwind must be suppressed in shadow mode, with log."""
    caplog.set_level(logging.INFO)
    mock_result = MagicMock()
    mock_result.status = "FILLED"
    mock_result.side = "BUY"
    mock_result.strategy_id = "paper"
    mock_result.filled_quantity = 0.01
    mock_result.symbol = "BTCUSDT"

    risk_manager._maybe_auto_unwind(mock_result)

    risk_manager.send_order.assert_not_called()
    assert "Reactive unwind suppressed" in caplog.text
    assert "shadow" in caplog.text


@pytest.mark.unit
@pytest.mark.usefixtures("_paper_env")
def test_reactive_unwind_works_in_paper(
    risk_manager,
) -> None:
    """Reactive unwind must still work in paper mode (regression guard)."""
    risk_state.last_prices = {"BTCUSDT": 50000.0}
    risk_state.pending_orders = 0
    stats["orders_approved"] = 0

    mock_result = MagicMock()
    mock_result.status = "FILLED"
    mock_result.side = "BUY"
    mock_result.strategy_id = "paper"
    mock_result.filled_quantity = 0.01
    mock_result.symbol = "BTCUSDT"
    mock_result.price = 50000.0

    risk_manager._maybe_auto_unwind(mock_result)

    risk_manager.send_order.assert_called_once()
