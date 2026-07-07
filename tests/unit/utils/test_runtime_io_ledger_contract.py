"""Redis/Postgres/Ledger IO contract tests (#3836).

Fixture-backed — no live Redis, Postgres, or runtime services.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from core.utils.postgres_client import get_postgres_dsn
from core.utils.redis_payload import sanitize_market_data, sanitize_payload
from core.utils.trace_toggle import allow_evidence_debt
from services.execution.database import Database

pytestmark = [pytest.mark.unit, pytest.mark.contract]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PRIVILEGE_FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "postgres_privileges" / "table_privileges.csv"


@pytest.fixture
def mock_db_config():
    with patch("services.execution.database.config") as mock_config:
        mock_config.DATABASE_URL = "postgresql://user:pass@host:5432/db"
        mock_config.SERVICE_NAME = "execution_service"
        yield mock_config


def _ledger_db(mock_connect, mock_db_config) -> Database:
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value
    return Database(), mock_cur


def test_sanitize_payload_fixture_shape_filters_none_and_preserves_strings() -> None:
    raw = {"symbol": "BTCUSDT", "price": "50000", "qty": None, "reason": ""}
    result = sanitize_payload(raw)
    assert result == {"symbol": "BTCUSDT", "price": "50000", "reason": ""}
    assert "qty" not in result


def test_sanitize_market_data_rejects_missing_required_field() -> None:
    with pytest.raises((ValueError, TypeError, KeyError)):
        sanitize_market_data(
            {
                "source": "mexc",
                "symbol": "BTCUSDT",
                "ts_ms": 1_700_000_000_000,
                "trade_qty": "0.001",
                "side": "BUY",
            }
        )


def test_get_postgres_dsn_includes_sslmode_without_logging_password(caplog) -> None:
    with patch.dict(
        "os.environ",
        {
            "POSTGRES_HOST": "pg.internal",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "claire_de_binare",
            "POSTGRES_USER": "cdb_writer",
            "POSTGRES_PASSWORD": "super-secret-value",
            "POSTGRES_SSLMODE": "prefer",
        },
        clear=False,
    ):
        dsn = get_postgres_dsn()
    assert "sslmode=prefer" in dsn
    assert "pg.internal" in dsn
    assert "super-secret-value" in dsn
    assert "super-secret-value" not in caplog.text


@patch("psycopg2.connect")
def test_correlation_ledger_rejects_invalid_event_type_fail_closed(
    mock_connect, mock_db_config, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ALLOW_EVIDENCE_DEBT", raising=False)
    db, _mock_cur = _ledger_db(mock_connect, mock_db_config)
    with pytest.raises(ValueError, match="Invalid event_type"):
        db.persist_correlation_event(
            signal_id="sig-1",
            decision_id="dec-1",
            event_type="BLOCK",
            symbol="BTCUSDT",
            timestamp_ms=1_700_000_000_000,
        )


@patch("psycopg2.connect")
def test_correlation_ledger_skips_invalid_event_type_when_evidence_debt_on(
    mock_connect, mock_db_config, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ALLOW_EVIDENCE_DEBT", "1")
    db, mock_cur = _ledger_db(mock_connect, mock_db_config)
    assert allow_evidence_debt() is True
    ok = db.persist_correlation_event(
        signal_id="sig-1",
        decision_id="dec-1",
        event_type="BLOCK",
        symbol="BTCUSDT",
        timestamp_ms=1_700_000_000_000,
    )
    assert ok is False
    insert_calls = [
        call
        for call in mock_cur.execute.call_args_list
        if call.args and "INSERT INTO correlation_ledger" in str(call.args[0])
    ]
    assert insert_calls == []


@patch("psycopg2.connect")
def test_correlation_ledger_missing_ids_fail_closed_without_silent_write(
    mock_connect, mock_db_config, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ALLOW_EVIDENCE_DEBT", raising=False)
    db, mock_cur = _ledger_db(mock_connect, mock_db_config)
    with pytest.raises(ValueError, match="signal_id and decision_id required"):
        db.persist_correlation_event(
            signal_id="",
            decision_id="dec-1",
            event_type="ORDER",
            symbol="BTCUSDT",
            timestamp_ms=1_700_000_000_000,
            order_id="ord-1",
        )
    insert_calls = [
        call
        for call in mock_cur.execute.call_args_list
        if call.args and "INSERT INTO correlation_ledger" in str(call.args[0])
    ]
    assert insert_calls == []


@patch("psycopg2.connect")
def test_correlation_ledger_order_requires_order_id_fail_closed(
    mock_connect, mock_db_config, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ALLOW_EVIDENCE_DEBT", raising=False)
    db, mock_cur = _ledger_db(mock_connect, mock_db_config)
    with pytest.raises(ValueError, match="order_id required"):
        db.persist_correlation_event(
            signal_id="sig-1",
            decision_id="dec-1",
            event_type="ORDER",
            symbol="BTCUSDT",
            timestamp_ms=1_700_000_000_000,
            order_id=None,
        )
    insert_calls = [
        call
        for call in mock_cur.execute.call_args_list
        if call.args and "INSERT INTO correlation_ledger" in str(call.args[0])
    ]
    assert insert_calls == []


@patch("psycopg2.connect")
def test_correlation_ledger_happy_path_writes_insert_with_payload_json(
    mock_connect, mock_db_config, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ALLOW_EVIDENCE_DEBT", raising=False)
    db, mock_cur = _ledger_db(mock_connect, mock_db_config)
    payload = {"strategy_id": "primary_breakout_v1", "bot_id": "bot-1"}
    ok = db.persist_correlation_event(
        signal_id="sig-ledger-1",
        decision_id="dec-ledger-1",
        event_type="ORDER",
        symbol="BTCUSDT",
        timestamp_ms=1_700_000_000_000,
        order_id="ord-ledger-1",
        payload=payload,
    )
    assert ok is True
    insert_call = [
        call
        for call in mock_cur.execute.call_args_list
        if "INSERT INTO correlation_ledger" in str(call.args[0])
    ]
    assert insert_call, "expected correlation_ledger INSERT"
    params = insert_call[0].args[1]
    assert json.loads(params[-1]) == payload


def test_blocked_decisions_requires_signal_id_fail_closed() -> None:
    from services.risk.service import RiskManager

    manager = RiskManager.__new__(RiskManager)
    with pytest.raises(ValueError, match="signal_id is required"):
        manager._persist_blocked_decision(
            signal_id="",
            decision_id="dec-1",
            symbol="BTCUSDT",
            reason_code="RC_001",
            timestamp_ms=1_700_000_000_000,
            evidence={"regime_id": 2},
        )


def test_blocked_decisions_skips_write_without_db_connection() -> None:
    from services.risk.service import RiskManager

    manager = RiskManager.__new__(RiskManager)
    manager._get_postgres_conn = lambda: None  # type: ignore[method-assign]
    ok = manager._persist_blocked_decision(
        signal_id="sig-block-1",
        decision_id="dec-block-1",
        symbol="BTCUSDT",
        reason_code="RC_001",
        timestamp_ms=1_700_000_000_000,
        evidence={"regime_id": 2},
    )
    assert ok is False


def test_postgres_least_privilege_fixture_blocks_runtime_delete_on_ledger_tables() -> None:
    rows = list(csv.DictReader(_PRIVILEGE_FIXTURE.open(encoding="utf-8")))
    ledger_tables = {"correlation_ledger", "blocked_decisions"}
    for table in ledger_tables:
        delete_grants = [
            row
            for row in rows
            if row["table_name"] == table and row["privilege_type"] == "DELETE"
        ]
        assert delete_grants == [], f"{table} must not grant DELETE in fixture baseline"


def test_cdb_reader_is_readonly_on_ledger_tables() -> None:
    rows = list(csv.DictReader(_PRIVILEGE_FIXTURE.open(encoding="utf-8")))
    for table in ("correlation_ledger", "blocked_decisions"):
        reader_privs = {
            row["privilege_type"]
            for row in rows
            if row["grantee"] == "cdb_reader" and row["table_name"] == table
        }
        assert reader_privs == {"SELECT"}, f"cdb_reader on {table} must be SELECT-only"
