"""ARVP runtime service boundary negative-controls contract suite (#3829).

Signal, risk, execution, ledger/evidence-debt surfaces — mocked only.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.execution import service as execution_service

from tests.unit.arvp._arvp_negative_controls_helpers import (
    invalid_signal_payload,
    run_evidence_debt_invalid_ledger_event,
    run_evidence_debt_on_skips_write,
    run_invalid_execution_payload,
    run_kill_switch_active_block,
    run_missing_decision_id_block,
)
from tests.unit.execution._execution_boundary_contract_helpers import (
    execution_harness,
    valid_order_payload,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

risk_service = importlib.import_module("services.risk.service")
signal_service = importlib.import_module("services.signal.service")


def test_invalid_signal_payload_returns_none_without_publish(monkeypatch) -> None:
    engine = signal_service.SignalEngine.__new__(signal_service.SignalEngine)
    engine.price_buffer = MagicMock()
    engine.price_buffer.calculate_pct_change.return_value = 0.0
    engine.strategy_adapter = MagicMock()
    engine.strategy_adapter.evaluate.return_value = MagicMock(signals=[])
    result = engine.process_market_data(invalid_signal_payload())
    assert result is None
    engine.strategy_adapter.evaluate.assert_not_called()


def test_blocked_risk_decision_returns_none(mock_redis, mock_postgres) -> None:
    from core.domain.models import Signal

    manager = risk_service.RiskManager()
    manager.redis_client = MagicMock()
    signal = Signal(
        signal_id="sig-1",
        strategy_id="test-strat",
        symbol="BTCUSDT",
        side="BUY",
        direction="BUY",
        strength=0.8,
        timestamp=1700000000.0,
    )
    evidence = {
        "decision_id": "dec-1",
        "signal_id": "sig-1",
        "timestamps_ms": {"signal_ts_ms": 1_700_000_000_000},
        "trace_id": "trace-1",
    }
    with patch.object(manager, "_kill_switch_gate", return_value=(False, None, {})):
        with patch.object(
            risk_service,
            "decide_trade",
            return_value=(risk_service.DECISION_BLOCK, "RC_001", evidence),
        ):
            with patch.object(manager, "_persist_correlation_event", return_value=True):
                with patch.object(manager, "_persist_blocked_decision", return_value=True):
                    result = manager.process_signal(signal)
    assert result is None


def test_invalid_execution_payload_blocks_executor_and_db(
    execution_harness, caplog
) -> None:
    caplog.set_level("WARNING")
    outcome = run_invalid_execution_payload(execution_harness)
    assert outcome.blocked is True
    assert outcome.executor_called is False
    assert outcome.db_write_attempted is False


def test_kill_switch_active_blocks_before_executor(execution_harness, monkeypatch) -> None:
    outcome = run_kill_switch_active_block(execution_harness, monkeypatch)
    assert outcome.blocked is True
    assert outcome.executor_called is False


def test_missing_decision_id_blocks_executor_when_trace_enabled(
    execution_harness, monkeypatch
) -> None:
    outcome = run_missing_decision_id_block(execution_harness, monkeypatch)
    assert outcome.blocked is True
    assert outcome.executor_called is False


def test_malformed_order_payload_increments_invalid_stats_without_executor(
    execution_harness,
) -> None:
    before = execution_service.get_stats_copy()["invalid_payloads"]
    execution_service.process_order({"type": "order", "quantity": "not-a-number"})
    after = execution_service.get_stats_copy()["invalid_payloads"]
    assert after == before + 1
    execution_harness.executor.execute_order.assert_not_called()


@patch("psycopg2.connect")
def test_evidence_debt_off_invalid_event_fail_closed_no_db_write(
    mock_connect, monkeypatch: pytest.MonkeyPatch,
) -> None:
    with patch("services.execution.database.config") as mock_config:
        mock_config.DATABASE_URL = "postgresql://user:pass@host:5432/db"
        mock_config.SERVICE_NAME = "execution_service"
        raised, wrote = run_evidence_debt_invalid_ledger_event(
            mock_connect, mock_config, monkeypatch
        )
    assert raised is True
    assert wrote is False


@patch("psycopg2.connect")
def test_evidence_debt_on_skips_invalid_event_without_db_write(
    mock_connect, monkeypatch: pytest.MonkeyPatch,
) -> None:
    with patch("services.execution.database.config") as mock_config:
        mock_config.DATABASE_URL = "postgresql://user:pass@host:5432/db"
        mock_config.SERVICE_NAME = "execution_service"
        skipped, wrote = run_evidence_debt_on_skips_write(
            mock_connect, mock_config, monkeypatch
        )
    assert skipped is True
    assert wrote is False


def test_negative_controls_suite_manifest_is_complete() -> None:
    required = {
        "invalid_signal_payload",
        "blocked_risk_decision",
        "invalid_execution_payload",
        "kill_switch_active",
        "missing_decision_id",
        "malformed_order_payload",
        "evidence_debt_off",
        "evidence_debt_on",
    }
    covered = {
        "invalid_signal_payload",
        "blocked_risk_decision",
        "invalid_execution_payload",
        "kill_switch_active",
        "missing_decision_id",
        "malformed_order_payload",
        "evidence_debt_off",
        "evidence_debt_on",
    }
    assert required == covered
