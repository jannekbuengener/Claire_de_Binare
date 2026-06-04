import pytest

from core.replay.paper_reference_window_export import (
    ExportRequest,
    PaperReferenceExportError,
    export_paper_reference_window,
)
from services.execution.models import ExecutionResult, OrderStatus
from services.execution import service


class _FakeDb:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def persist_correlation_event(self, **kwargs) -> bool:  # type: ignore[no-untyped-def]
        self.calls.append(dict(kwargs))
        return True


class _FakeExecutor:
    def __init__(self, *, exchange_order_id: str) -> None:
        self.exchange_order_id = exchange_order_id

    def execute_order(self, order):  # type: ignore[no-untyped-def]
        return ExecutionResult(
            order_id=self.exchange_order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            filled_quantity=order.quantity,
            status=OrderStatus.FILLED.value,
            price=50000.0,
            client_id=order.client_id,
            fill_id=self.exchange_order_id,
            strategy_id=order.strategy_id,
            bot_id=order.bot_id,
        )


def _disable_kill_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    import core.safety.kill_switch as kill_switch

    monkeypatch.setattr(
        kill_switch,
        "get_kill_switch_details",
        lambda create_if_missing=False: (False, "inactive", None, None),
    )


def _ledger_rows_for_export(
    calls: list[dict],
    *,
    ledger_order_id: str,
) -> list[dict]:
    """Build minimal correlation_ledger rows for export_paper_reference_window."""
    first = calls[0]
    ts_ms = int(first["timestamp_ms"])
    signal_id = str(first["signal_id"])
    decision_id = str(first["decision_id"])
    symbol = str(first["symbol"])
    strategy_id = str(first["payload"]["strategy_id"])
    correlation_id = "corr-unit-1"
    rows: list[dict] = [
        {
            "event_pk": "sig-1",
            "correlation_id": correlation_id,
            "event_type": "SIGNAL",
            "symbol": symbol,
            "timestamp_ms": ts_ms,
            "payload": {
                "strategy_id": strategy_id,
                "bot_id": "bot-unit-1",
                "metadata": {"config_hash": "cfg-unit-1"},
            },
            "signal_id": signal_id,
        },
    ]
    for idx, call in enumerate(calls):
        payload = dict(call["payload"])
        payload["order_id"] = ledger_order_id
        if payload.get("exchange_order_id") == ledger_order_id:
            payload.pop("exchange_order_id", None)
        rows.append(
            {
                "event_pk": f"ev-{idx}",
                "correlation_id": correlation_id,
                "event_type": str(call["event_type"]),
                "symbol": symbol,
                "timestamp_ms": ts_ms,
                "payload": payload,
                "signal_id": signal_id,
                "decision_id": decision_id,
                "order_id": ledger_order_id,
                "fill_id": call.get("fill_id"),
            }
        )
    return rows


@pytest.mark.unit
def test_execution_service_persists_canonical_order_id_for_paper_orders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    correlation_ledger must preserve canonical internal order_id (paper_...) for paper runs,
    otherwise #1901 paper_reference_window export fails closed (Refs #2943).
    """
    _disable_kill_switch(monkeypatch)

    fake_db = _FakeDb()
    fake_executor = _FakeExecutor(exchange_order_id="MOCK_123")
    monkeypatch.setattr(service, "db", fake_db)
    monkeypatch.setattr(service, "executor", fake_executor)
    monkeypatch.setattr(service, "_publish_result", lambda _result: None)
    monkeypatch.setattr(service, "bot_shutdown_active", False)
    monkeypatch.setattr(service, "blocked_strategy_ids", set())
    monkeypatch.setattr(service, "blocked_bot_ids", set())

    result = service.process_order(
        {
            "type": "order",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.01,
            "strategy_id": "primary_breakout_v1",
            "signal_id": "sig-unit-1",
            "decision_id": "dec-unit-1",
            "order_id": "paper_1700000000000",
        }
    )
    assert result is not None

    assert [c["event_type"] for c in fake_db.calls] == ["ORDER", "FILL"]
    for call in fake_db.calls:
        assert call["order_id"] == "paper_1700000000000"
        assert call["payload"]["order_id"] == "paper_1700000000000"
        assert call["payload"]["exchange_order_id"] == "MOCK_123"

    ts_ms = int(fake_db.calls[0]["timestamp_ms"])
    request = ExportRequest(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        start_ts_ms_utc=ts_ms,
        end_ts_ms_utc=ts_ms + 1,
        extracted_by="tests",
        source_query_intent="unit-test",
        extracted_at_utc="2026-04-24T00:00:00Z",
    )

    with pytest.raises(PaperReferenceExportError, match="paper qualification failed"):
        export_paper_reference_window(
            request=request,
            rows=_ledger_rows_for_export(fake_db.calls, ledger_order_id="MOCK_123"),
        )

    exported = export_paper_reference_window(
        request=request,
        rows=_ledger_rows_for_export(
            fake_db.calls, ledger_order_id="paper_1700000000000"
        ),
    )
    assert exported["contract_version"] == "arvp_paper_reference_window.v1"
    order_ids = {
        ev["order_id"]
        for ev in exported["events"]
        if ev["event_type"] in {"ORDER", "FILL"}
    }
    assert order_ids == {"paper_1700000000000"}


@pytest.mark.unit
def test_execution_service_derives_paper_prefixed_ledger_id_for_mock_exchange_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mock path without incoming order_id still writes ARVP-qualifying paper_* ids."""
    _disable_kill_switch(monkeypatch)

    fake_db = _FakeDb()
    fake_executor = _FakeExecutor(exchange_order_id="MOCK_456")
    monkeypatch.setattr(service, "db", fake_db)
    monkeypatch.setattr(service, "executor", fake_executor)
    monkeypatch.setattr(service, "_publish_result", lambda _result: None)
    monkeypatch.setattr(service, "bot_shutdown_active", False)
    monkeypatch.setattr(service, "blocked_strategy_ids", set())
    monkeypatch.setattr(service, "blocked_bot_ids", set())
    monkeypatch.setattr(service.config, "MOCK_TRADING", True)

    result = service.process_order(
        {
            "type": "order",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.01,
            "strategy_id": "primary_breakout_v1",
            "signal_id": "sig-unit-2",
            "decision_id": "dec-unit-2",
        }
    )
    assert result is not None

    assert [c["event_type"] for c in fake_db.calls] == ["ORDER", "FILL"]
    for call in fake_db.calls:
        assert call["order_id"] == "paper_MOCK_456"
        assert call["payload"]["order_id"] == "paper_MOCK_456"
        assert call["payload"]["exchange_order_id"] == "MOCK_456"


@pytest.mark.unit
def test_execution_service_derives_paper_prefixed_ledger_id_from_risk_uuid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Risk -> mock path: UUID internal id becomes paper_<uuid> for ARVP export."""
    _disable_kill_switch(monkeypatch)

    risk_uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    ledger_order_id = f"paper_{risk_uuid}"

    fake_db = _FakeDb()
    fake_executor = _FakeExecutor(exchange_order_id="MOCK_RISK_1")
    monkeypatch.setattr(service, "db", fake_db)
    monkeypatch.setattr(service, "executor", fake_executor)
    monkeypatch.setattr(service, "_publish_result", lambda _result: None)
    monkeypatch.setattr(service, "bot_shutdown_active", False)
    monkeypatch.setattr(service, "blocked_strategy_ids", set())
    monkeypatch.setattr(service, "blocked_bot_ids", set())
    monkeypatch.setattr(service.config, "MOCK_TRADING", True)

    result = service.process_order(
        {
            "type": "order",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.01,
            "strategy_id": "primary_breakout_v1",
            "signal_id": "sig-unit-3",
            "decision_id": "dec-unit-3",
            "order_id": risk_uuid,
        }
    )
    assert result is not None

    assert [c["event_type"] for c in fake_db.calls] == ["ORDER", "FILL"]
    for call in fake_db.calls:
        assert call["order_id"] == ledger_order_id
        assert call["payload"]["order_id"] == ledger_order_id
        assert call["payload"]["exchange_order_id"] == "MOCK_RISK_1"

    ts_ms = int(fake_db.calls[0]["timestamp_ms"])
    request = ExportRequest(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        start_ts_ms_utc=ts_ms,
        end_ts_ms_utc=ts_ms + 1,
        extracted_by="tests",
        source_query_intent="unit-test",
        extracted_at_utc="2026-04-24T00:00:00Z",
    )
    exported = export_paper_reference_window(
        request=request,
        rows=_ledger_rows_for_export(fake_db.calls, ledger_order_id=ledger_order_id),
    )
    assert exported["contract_version"] == "arvp_paper_reference_window.v1"
