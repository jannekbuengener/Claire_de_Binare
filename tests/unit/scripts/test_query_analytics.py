"""Focused tests for infrastructure/scripts/query_analytics.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "infrastructure" / "scripts")
)

import query_analytics


def test_main_without_args_prints_help_without_initializing_db(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_init() -> None:
        raise AssertionError("AnalyticsQuery should not be initialized without CLI args")

    monkeypatch.setattr(query_analytics, "AnalyticsQuery", fail_init)
    monkeypatch.setattr(sys, "argv", ["query_analytics.py"])

    assert query_analytics.main() == 0

    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "query_analytics.py" in captured.out
    assert captured.err == ""


def test_main_reports_connection_errors(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_init() -> None:
        raise RuntimeError("synthetic connect failure")

    monkeypatch.setattr(query_analytics, "AnalyticsQuery", fail_init)
    monkeypatch.setattr(sys, "argv", ["query_analytics.py", "--last-signals", "5"])

    assert query_analytics.main() == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "ERROR: synthetic connect failure" in captured.err


def test_main_reports_missing_psycopg2_dependency(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(query_analytics, "psycopg2", None)
    monkeypatch.setattr(query_analytics, "RealDictCursor", None)
    monkeypatch.setattr(sys, "argv", ["query_analytics.py", "--last-signals", "1"])

    assert query_analytics.main() == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Missing dependency: psycopg2" in captured.err


def test_main_reports_query_errors_and_closes_connection(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    state = {"closed": False}
    query_error = (
        query_analytics.psycopg2.ProgrammingError("synthetic query failure")
        if query_analytics.psycopg2 is not None
        else RuntimeError("synthetic query failure")
    )

    class FailingQuery:
        def last_signals(self, limit: int) -> None:
            raise query_error

        def close(self) -> None:
            state["closed"] = True

    monkeypatch.setattr(query_analytics, "AnalyticsQuery", FailingQuery)
    monkeypatch.setattr(sys, "argv", ["query_analytics.py", "--last-signals", "5"])

    assert query_analytics.main() == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "synthetic query failure" in captured.err
    assert state["closed"] is True


def test_last_signals_handles_missing_tabulate(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class FakeCursor:
        def __enter__(self) -> "FakeCursor":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def execute(self, sql: str, params: tuple[int]) -> None:
            return None

        def fetchall(self) -> list[dict[str, object]]:
            return [{"id": 1, "symbol": "BTCUSDT"}]

    class FakeConnection:
        def cursor(self, cursor_factory=None) -> FakeCursor:
            return FakeCursor()

        def close(self) -> None:
            return None

    query = object.__new__(query_analytics.AnalyticsQuery)
    query.conn = FakeConnection()
    monkeypatch.setattr(query_analytics, "tabulate", None)

    query.last_signals(1)

    captured = capsys.readouterr()
    assert captured.err == ""
    assert "Missing dependency: tabulate." in captured.out


def test_daily_pnl_uses_interval_multiplication_parameterization(
    capsys: pytest.CaptureFixture[str]
) -> None:
    executed: dict[str, object] = {}

    class FakeCursor:
        def __enter__(self) -> "FakeCursor":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def execute(self, sql: str, params: tuple[int]) -> None:
            executed["sql"] = sql
            executed["params"] = params

        def fetchall(self) -> list[dict[str, object]]:
            return []

    class FakeConnection:
        def cursor(self, cursor_factory=None) -> FakeCursor:
            return FakeCursor()

        def close(self) -> None:
            return None

    query = object.__new__(query_analytics.AnalyticsQuery)
    query.conn = FakeConnection()

    query.daily_pnl(7)

    captured = capsys.readouterr()
    assert executed["params"] == (7,)
    assert "(%s * INTERVAL '1 day')" in str(executed["sql"])
    assert "INTERVAL '%s days'" not in str(executed["sql"])
    assert "No data for the last 7 days." in captured.out
