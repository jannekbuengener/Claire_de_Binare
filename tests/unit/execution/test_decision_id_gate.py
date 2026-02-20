"""
Unit-Tests für die decision_id Safety-Gate im Execution Service (refs #467).

Wenn TRACE_CONTRACT_V1_ENABLED=1, werden Orders ohne decision_id rejected.
Bei Toggle OFF (default) dürfen Legacy-/Bypass-Orders weiterhin durch.

Technik: Flask/Redis werden per MagicMock gestubbt, damit
services.execution.service importierbar ist ohne echte Dependencies.
"""

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest


def _stub_flask_and_redis():
    """Stub flask + redis in sys.modules, damit der Service importierbar ist."""
    # Flask stub
    flask_mod = types.ModuleType("flask")
    flask_mod.Flask = MagicMock(return_value=MagicMock())
    flask_mod.jsonify = MagicMock()
    flask_mod.Response = MagicMock()
    sys.modules["flask"] = flask_mod

    # Redis stub
    redis_mod = types.ModuleType("redis")
    redis_mod.Redis = MagicMock()
    redis_mod.ConnectionPool = MagicMock()
    sys.modules["redis"] = redis_mod


def _import_execution_service():
    """Import (oder re-import) des Execution-Service-Moduls."""
    mod_name = "services.execution.service"
    if mod_name in sys.modules:
        return importlib.reload(sys.modules[mod_name])
    return importlib.import_module(mod_name)


@pytest.mark.unit
class TestDecisionIdGate:
    """Verifiziert die decision_id-Guardrail in process_order()."""

    @pytest.fixture(autouse=True)
    def _setup_service(self, monkeypatch):
        """Importiert den Service mit gestubtem Flask/Redis und setzt Globals."""
        _stub_flask_and_redis()
        self.svc = _import_execution_service()

        # Mock _publish_result damit kein echtes Redis nötig ist
        monkeypatch.setattr(self.svc, "_publish_result", MagicMock())

        # Mock executor damit process_order() nicht an "Executor not initialised" scheitert
        from services.execution.models import ExecutionResult, OrderStatus

        mock_executor = MagicMock()
        mock_executor.execute_order.return_value = ExecutionResult(
            order_id="mock-order-id",
            symbol="BTC/USDT",
            side="BUY",
            quantity=999.0,
            filled_quantity=999.0,
            status=OrderStatus.FILLED.value,
            price=60000.0,
            timestamp="2026-01-01T00:00:00Z",
        )
        monkeypatch.setattr(self.svc, "executor", mock_executor)

        # Mock db (None = kein DB-Write)
        monkeypatch.setattr(self.svc, "db", None)

        # Sicherstellen dass bot_shutdown_active = False
        monkeypatch.setattr(self.svc, "bot_shutdown_active", False)

    def _order_payload(self, decision_id=None):
        payload = {
            "symbol": "BTC/USDT",
            "side": "BUY",
            "quantity": 999.0,
            "type": "order",
            "order_id": "test-gate-001",
        }
        if decision_id is not None:
            payload["decision_id"] = decision_id
        return payload

    # --- Toggle ON: Gate aktiv ---

    def test_rejects_without_decision_id_toggle_on(self, monkeypatch):
        """TRACE_CONTRACT_V1_ENABLED=1 + kein decision_id → REJECTED."""
        monkeypatch.setenv("TRACE_CONTRACT_V1_ENABLED", "1")

        result = self.svc.process_order(self._order_payload(decision_id=None))

        assert result is not None
        assert result.status == "REJECTED"
        assert "missing decision_id" in result.error_message

    def test_allows_with_decision_id_toggle_on(self, monkeypatch):
        """TRACE_CONTRACT_V1_ENABLED=1 + decision_id gesetzt → durchgelassen."""
        monkeypatch.setenv("TRACE_CONTRACT_V1_ENABLED", "1")

        result = self.svc.process_order(self._order_payload(decision_id="dec-abc-123"))

        assert result is not None
        assert result.status != "REJECTED" or "missing decision_id" not in (
            result.error_message or ""
        )

    # --- Toggle OFF: Gate inaktiv ---

    def test_allows_without_decision_id_toggle_off(self, monkeypatch):
        """TRACE_CONTRACT_V1_ENABLED=0 + kein decision_id → KEIN Reject (Legacy-Compat)."""
        monkeypatch.setenv("TRACE_CONTRACT_V1_ENABLED", "0")

        result = self.svc.process_order(self._order_payload(decision_id=None))

        assert result is not None
        # Darf nicht am decision_id-Gate abgelehnt werden
        if result.status == "REJECTED":
            assert "missing decision_id" not in (result.error_message or "")

    def test_allows_without_decision_id_toggle_unset(self, monkeypatch):
        """Default (kein Env) = Toggle OFF → Gate inaktiv."""
        monkeypatch.delenv("TRACE_CONTRACT_V1_ENABLED", raising=False)

        result = self.svc.process_order(self._order_payload(decision_id=None))

        assert result is not None
        if result.status == "REJECTED":
            assert "missing decision_id" not in (result.error_message or "")
