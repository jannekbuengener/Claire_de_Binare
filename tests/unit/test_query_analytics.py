import sys

import pytest

from infrastructure.scripts import query_analytics as qa


@pytest.mark.unit
def test_main_missing_psycopg2_exits_with_error(monkeypatch, capsys):
    monkeypatch.setattr(qa, "psycopg2", None)
    monkeypatch.setattr(qa, "RealDictCursor", None)
    monkeypatch.setattr(sys, "argv", ["query_analytics.py", "--last-signals", "1"])

    exit_code = qa.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Missing dependency: psycopg2" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.unit
def test_main_query_error_returns_nonzero(monkeypatch, capsys):
    class DummyPsycopg2:
        class Error(Exception):
            def __init__(self, message="boom"):
                super().__init__(message)
                self.pgerror = "bad query"

    class DummyConn:
        def close(self):
            return None

    def _init(self):
        self.conn = DummyConn()

    def _raise(self, _limit):
        raise DummyPsycopg2.Error("boom")

    monkeypatch.setattr(qa, "psycopg2", DummyPsycopg2)
    monkeypatch.setattr(qa.AnalyticsQuery, "__init__", _init)
    monkeypatch.setattr(qa.AnalyticsQuery, "last_signals", _raise)
    monkeypatch.setattr(sys, "argv", ["query_analytics.py", "--last-signals", "1"])

    exit_code = qa.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Database query failed: bad query" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.unit
def test_last_signals_no_rows_prints_message(capsys):
    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, _query, _params):
            return None

        def fetchall(self):
            return []

    class FakeConn:
        def cursor(self, *args, **kwargs):
            return FakeCursor()

        def close(self):
            return None

    query = qa.AnalyticsQuery.__new__(qa.AnalyticsQuery)
    query.conn = FakeConn()

    query.last_signals(5)
    captured = capsys.readouterr()

    assert "No signals found." in captured.out
