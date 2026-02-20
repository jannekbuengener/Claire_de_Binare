"""
Unit-Tests für die decision_id Safety-Gate im Execution Service (refs #467).

Wenn TRACE_CONTRACT_V1_ENABLED=1, werden Orders ohne decision_id rejected.
Bei Toggle OFF (default) dürfen Legacy-/Bypass-Orders weiterhin durch.

Technik: Flask/Redis werden nur gestubbt wenn sie nicht installiert sind.
Stubs + das importierte Service-Modul werden im Fixture-Teardown aus
sys.modules entfernt, damit nachfolgende Tests (z.B. test_service.py)
nicht mit Stub-Artefakten kollidieren.
"""

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest

# Module keys that we may need to clean up after stubbing
_SERVICE_MOD = "services.execution.service"
_STUB_KEYS = ("flask", "redis")


def _needs_stub():
    """True wenn flask oder redis nicht installiert sind."""
    for mod in _STUB_KEYS:
        try:
            importlib.import_module(mod)
        except ModuleNotFoundError:
            return True
    return False


@pytest.mark.unit
class TestDecisionIdGate:
    """Verifiziert die decision_id-Guardrail in process_order()."""

    @pytest.fixture(autouse=True)
    def _setup_service(self, monkeypatch):
        """Importiert den Service (mit Stub falls nötig) und setzt Globals."""
        self._stubbed = _needs_stub()

        if self._stubbed:
            # Flask stub
            flask_mod = types.ModuleType("flask")
            flask_mod.Flask = MagicMock(return_value=MagicMock())
            flask_mod.jsonify = MagicMock()
            flask_mod.Response = MagicMock()
            monkeypatch.setitem(sys.modules, "flask", flask_mod)

            # Redis stub
            redis_mod = types.ModuleType("redis")
            redis_mod.Redis = MagicMock()
            redis_mod.ConnectionPool = MagicMock()
            monkeypatch.setitem(sys.modules, "redis", redis_mod)

        # Import (oder re-import) des Service-Moduls
        if _SERVICE_MOD in sys.modules:
            self.svc = importlib.reload(sys.modules[_SERVICE_MOD])
        else:
            self.svc = importlib.import_module(_SERVICE_MOD)

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

        yield

        # Teardown: Service-Modul aus Cache entfernen wenn gestubbt,
        # damit nachfolgende Tests (test_service.py) frisch mit echtem Flask importieren.
        if self._stubbed:
            sys.modules.pop(_SERVICE_MOD, None)

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
