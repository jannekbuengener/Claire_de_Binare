from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services.validation import paper_reference_window_runner as runner


@pytest.mark.unit
def test_get_required_readonly_dsn_rejects_missing_env(monkeypatch):
    monkeypatch.delenv("POSTGRES_READONLY_PASSWORD_DSN", raising=False)

    with pytest.raises(
        RuntimeError, match="POSTGRES_READONLY_PASSWORD_DSN is required"
    ):
        runner._get_required_readonly_dsn()


@pytest.mark.unit
def test_verify_readonly_identity_rejects_runtime_login():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = ("claire_de_binare", "claire_user", "claire_user")
    conn.cursor.return_value.__enter__.return_value = cursor

    with pytest.raises(RuntimeError, match="Readonly identity probe failed"):
        runner._verify_readonly_identity(conn)


@pytest.mark.unit
def test_verify_readonly_privileges_rejects_write_access():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (True, False, True, False)
    conn.cursor.return_value.__enter__.return_value = cursor

    with pytest.raises(
        RuntimeError, match="Readonly privilege probe failed: write privileges detected"
    ):
        runner._verify_readonly_privileges(conn)


@pytest.mark.unit
def test_verify_readonly_privileges_requires_select():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (False, False, False, False)
    conn.cursor.return_value.__enter__.return_value = cursor

    with pytest.raises(
        RuntimeError, match="Readonly privilege probe failed: missing SELECT"
    ):
        runner._verify_readonly_privileges(conn)


@pytest.mark.unit
def test_create_readonly_connection_uses_required_dsn(monkeypatch):
    connect_mock = MagicMock(return_value=MagicMock())
    monkeypatch.setenv(
        "POSTGRES_READONLY_PASSWORD_DSN",
        "postgresql://cdb_readonly:masked@localhost:5432/claire_de_binare",
    )
    monkeypatch.setattr(runner.psycopg2, "connect", connect_mock)

    runner._create_readonly_connection()

    connect_mock.assert_called_once_with(
        "postgresql://cdb_readonly:masked@localhost:5432/claire_de_binare",
        connect_timeout=10,
    )


@pytest.mark.unit
def test_main_exports_with_verified_readonly_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    output_path = tmp_path / "paper_reference_window.json"
    request = SimpleNamespace(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        start_ts_ms_utc=1000,
        end_ts_ms_utc=2000,
        bot_id=None,
        config_hash=None,
    )
    mock_conn = MagicMock()

    monkeypatch.setattr(runner, "build_export_request", lambda **_: request)
    monkeypatch.setattr(
        runner,
        "_create_readonly_connection",
        lambda: mock_conn,
    )
    monkeypatch.setattr(
        runner,
        "_verify_readonly_identity",
        lambda conn: ("claire_de_binare", "cdb_readonly", "cdb_readonly"),
    )
    monkeypatch.setattr(runner, "_verify_readonly_privileges", lambda conn: None)
    monkeypatch.setattr(
        runner,
        "export_paper_reference_window",
        lambda request, rows, causal_context_rows=None: {
            "schema_version": "arvp_paper_reference_window.v1"
        },
    )
    monkeypatch.setattr(
        runner,
        "canonical_json_dumps",
        lambda payload: '{"schema_version":"arvp_paper_reference_window.v1"}',
    )

    query_cursor = MagicMock()
    query_cursor.description = [SimpleNamespace(name="event_pk")]
    query_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value.__enter__.return_value = query_cursor

    exit_code = runner.main(
        [
            "--strategy-id",
            "primary_breakout_v1",
            "--symbol",
            "BTCUSDT",
            "--start-ts-ms",
            "1000",
            "--end-ts-ms",
            "2000",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.read_text(encoding="utf-8") == (
        '{"schema_version":"arvp_paper_reference_window.v1"}'
    )
    captured = capsys.readouterr()
    assert "current_user=cdb_readonly" in captured.out
    assert "session_user=cdb_readonly" in captured.out
