"""Explicit filled_quantity=0 must not fall back to requested quantity (#4261).

Residual FILLED_QUANTITY_ZERO_FALLBACK — falsy ``or`` chains treated numeric 0
as missing and persisted/requested positive quantities (phantom fills).
"""

from __future__ import annotations

import importlib
import json
import sys
import types
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from services.execution.reduce_only import (
    REDUCE_ONLY_REJECTED,
    is_retryable_reduce_only_terminal,
)

pytestmark = [pytest.mark.unit]


def _build_prometheus_client_stub() -> types.ModuleType:
    prometheus_client = types.ModuleType("prometheus_client")

    class _MetricStub:
        def labels(self, **kwargs):
            return self

        def inc(self):
            return None

        def set(self, value):
            return None

        def set_function(self, func):
            return None

    prometheus_client.Counter = lambda *args, **kwargs: _MetricStub()
    prometheus_client.Gauge = lambda *args, **kwargs: _MetricStub()
    prometheus_client.start_http_server = lambda *args, **kwargs: None
    return prometheus_client


@pytest.fixture
def database_writer_cls(monkeypatch):
    monkeypatch.delitem(sys.modules, "services.db_writer.db_writer", raising=False)
    monkeypatch.setitem(
        sys.modules, "prometheus_client", _build_prometheus_client_stub()
    )
    module = importlib.import_module("services.db_writer.db_writer")
    return module.DatabaseWriter


@pytest.fixture
def db_writer_module(monkeypatch):
    monkeypatch.delitem(sys.modules, "services.db_writer.db_writer", raising=False)
    monkeypatch.setitem(
        sys.modules, "prometheus_client", _build_prometheus_client_stub()
    )
    return importlib.import_module("services.db_writer.db_writer")


def _filled_payload(**overrides):
    payload = {
        "symbol": "BTCUSDT",
        "side": "SELL",
        "status": "filled",
        "price": 50000.0,
        "filled_quantity": 0,
        "quantity": 0.01,
        "timestamp": 1700000000,
        "metadata": {},
    }
    payload.update(overrides)
    return payload


def test_legacy_falsy_or_chain_would_select_requested_quantity(db_writer_module):
    """Root-cause reproduction: Python ``or`` treats 0 as missing."""
    data = _filled_payload(filled_quantity=0, quantity=0.01)
    legacy = (
        data.get("filled_quantity")
        or data.get("filled_size")
        or data.get("quantity")
        or data.get("size")
    )
    assert legacy == 0.01
    resolved = db_writer_module.DatabaseWriter.resolve_fill_quantity(data)
    assert resolved["state"] == db_writer_module.FIELD_ZERO
    assert resolved["value"] == Decimal("0")
    assert resolved["source"] == "filled_quantity"


def test_t1_explicit_zero_preserved_over_requested_quantity(database_writer_cls):
    resolved = database_writer_cls.resolve_fill_quantity(
        _filled_payload(filled_quantity=0, quantity=1.5)
    )
    assert resolved["state"] == "FIELD_ZERO"
    assert resolved["value"] == Decimal("0")


def test_t2_decimal_zero_preserved(database_writer_cls):
    resolved = database_writer_cls.resolve_fill_quantity(
        _filled_payload(filled_quantity=Decimal("0"), quantity=Decimal("2"))
    )
    assert resolved["state"] == "FIELD_ZERO"
    assert resolved["value"] == Decimal("0")


def test_t3_missing_filled_quantity_uses_legacy_quantity(database_writer_cls):
    payload = {
        "symbol": "BTCUSDT",
        "quantity": 0.25,
        "status": "filled",
        "price": 1,
    }
    resolved = database_writer_cls.resolve_fill_quantity(payload)
    assert resolved["state"] == "FIELD_MISSING_LEGACY_FALLBACK"
    assert resolved["source"] == "quantity"
    assert resolved["value"] == Decimal("0.25")


def test_t4_explicit_null_filled_quantity_is_not_legacy_fallback(database_writer_cls):
    payload = {
        "filled_quantity": None,
        "quantity": 0.5,
        "symbol": "BTCUSDT",
    }
    resolved = database_writer_cls.resolve_fill_quantity(payload)
    assert resolved["state"] == "FIELD_NULL"
    assert resolved["value"] is None


def test_t5_positive_filled_quantity_happy_path(database_writer_cls):
    resolved = database_writer_cls.resolve_fill_quantity(
        _filled_payload(filled_quantity=0.01, quantity=0.02)
    )
    assert resolved["state"] == "FIELD_POSITIVE"
    assert resolved["value"] == Decimal("0.01")


def test_t6_negative_filled_quantity_invalid(database_writer_cls):
    resolved = database_writer_cls.resolve_fill_quantity(
        _filled_payload(filled_quantity=-0.01)
    )
    assert resolved["state"] == "FIELD_INVALID"


def test_t7_nan_and_non_numeric_invalid(database_writer_cls):
    assert (
        database_writer_cls.resolve_fill_quantity(
            _filled_payload(filled_quantity="not-a-number")
        )["state"]
        == "FIELD_INVALID"
    )
    assert (
        database_writer_cls.resolve_fill_quantity(
            _filled_payload(filled_quantity="NaN")
        )["state"]
        == "FIELD_INVALID"
    )


def test_t1_process_trade_event_skips_zero_fill_no_insert(
    database_writer_cls, caplog: pytest.LogCaptureFixture
):
    import logging

    caplog.set_level(logging.INFO)
    writer = database_writer_cls()
    writer.db_conn = MagicMock()
    cursor = writer.db_conn.cursor.return_value
    writer.update_position_from_trade = MagicMock()

    writer.process_trade_event(_filled_payload(filled_quantity=0, quantity=0.01))

    cursor.execute.assert_not_called()
    writer.update_position_from_trade.assert_not_called()
    assert "zero-fill" in caplog.text.lower()


def test_t11_update_position_skips_zero_fill(database_writer_cls):
    writer = database_writer_cls()
    writer.db_conn = MagicMock()
    cursor = writer.db_conn.cursor.return_value

    writer.update_position_from_trade(
        _filled_payload(filled_quantity=0, quantity=0.01, side="BUY")
    )

    cursor.execute.assert_not_called()


def test_t5_process_trade_event_positive_fill_still_persists(database_writer_cls):
    writer = database_writer_cls()
    writer.db_conn = MagicMock()
    cursor = writer.db_conn.cursor.return_value
    cursor.fetchone.side_effect = [None, (99,)]
    writer.update_position_from_trade = MagicMock()

    writer.process_trade_event(
        _filled_payload(filled_quantity=0.01, quantity=0.02, side="BUY")
    )

    assert cursor.execute.called
    insert_params = cursor.execute.call_args[0][1]
    # size column is execution_qty
    assert insert_params[3] == Decimal("0.01")
    writer.update_position_from_trade.assert_called_once()


def test_t10_duplicate_zero_fill_is_idempotent(database_writer_cls):
    writer = database_writer_cls()
    writer.db_conn = MagicMock()
    cursor = writer.db_conn.cursor.return_value
    writer.update_position_from_trade = MagicMock()
    payload = _filled_payload(filled_quantity=0, quantity=0.01)
    writer.process_trade_event(payload)
    writer.process_trade_event(payload)
    cursor.execute.assert_not_called()
    writer.update_position_from_trade.assert_not_called()


def test_t8_rejected_zero_fill_skipped_and_retryable_contract():
    """REJECTED + filled_quantity=0 stays non-execution and retryable."""
    assert is_retryable_reduce_only_terminal(
        status="REJECTED",
        reason_code=REDUCE_ONLY_REJECTED,
        filled_quantity=Decimal("0"),
    )


def test_t8_process_trade_event_rejected_skips_even_with_quantity(
    database_writer_cls,
):
    writer = database_writer_cls()
    writer.db_conn = MagicMock()
    cursor = writer.db_conn.cursor.return_value
    writer.update_position_from_trade = MagicMock()
    writer.process_trade_event(
        _filled_payload(status="rejected", filled_quantity=0, quantity=0.01)
    )
    cursor.execute.assert_not_called()
    writer.update_position_from_trade.assert_not_called()


def test_t12_legacy_quantity_only_payload_still_works(database_writer_cls):
    writer = database_writer_cls()
    writer.db_conn = MagicMock()
    cursor = writer.db_conn.cursor.return_value
    cursor.fetchone.side_effect = [None, (5,)]
    writer.update_position_from_trade = MagicMock()
    writer.process_trade_event(
        {
            "symbol": "ETHUSDT",
            "side": "BUY",
            "status": "filled",
            "price": 3000.0,
            "quantity": 0.5,
            "timestamp": 1700000000,
            "metadata": {},
        }
    )
    insert_params = cursor.execute.call_args[0][1]
    assert insert_params[3] == Decimal("0.5")


def test_t9_zero_fill_does_not_block_retryable_rejected_semantics(
    database_writer_cls,
):
    """Wiring: zero fill resolution + attempt retry policy remain consistent."""
    resolved = database_writer_cls.resolve_fill_quantity(
        {
            "filled_quantity": Decimal("0"),
            "quantity": Decimal("1"),
            "status": "rejected",
        }
    )
    assert resolved["state"] == "FIELD_ZERO"
    assert is_retryable_reduce_only_terminal(
        status="REJECTED",
        reason_code=REDUCE_ONLY_REJECTED,
        filled_quantity=resolved["value"],
    )


def test_filled_size_zero_also_preserved(database_writer_cls):
    resolved = database_writer_cls.resolve_fill_quantity(
        {"filled_size": 0, "quantity": 3}
    )
    assert resolved["state"] == "FIELD_ZERO"
    assert resolved["source"] == "filled_size"


def test_no_falsy_or_chain_remains_in_db_writer_source(db_writer_module):
    source = open(db_writer_module.__file__, encoding="utf-8").read()
    assert "resolve_fill_quantity" in source
    assert 'or data.get("filled_size")' not in source
    assert 'filled_quantity") or' not in source
