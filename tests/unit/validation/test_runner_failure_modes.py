"""Failure-mode tests for validation runner."""

from __future__ import annotations

import sqlite3

import pytest

from services.validation import runner


class DummyConn:
    def close(self) -> None:
        pass


class DummyFetcher:
    def __init__(self) -> None:
        self.updated = False
        self.completed = False

    def start_72h_validation(self, start_time: str | None = None) -> int:
        return 1

    def update_validation_progress(self, *args, **kwargs) -> None:
        self.updated = True

    def complete_validation(self, *args, **kwargs) -> None:
        self.completed = True


class LockedFetcher(DummyFetcher):
    def update_validation_progress(self, *args, **kwargs) -> None:
        raise sqlite3.OperationalError("database is locked")

    def complete_validation(self, *args, **kwargs) -> None:
        raise sqlite3.OperationalError("database is locked")


@pytest.mark.unit
def test_runner_db_unreachable(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    def raise_connect(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(runner, "_connect_with_retries", raise_connect)
    monkeypatch.setattr(runner, "RealValidationFetcher", DummyFetcher)
    monkeypatch.setenv("VALIDATION_EVIDENCE_DIR", str(tmp_path))

    report = runner.run("2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z")

    assert report["pass"] is False
    assert any(reason.startswith("db_unreachable") for reason in report["reasons"])
    assert report["schema_version"] == "1"
    assert (tmp_path / "1" / "report.json").exists()


@pytest.mark.unit
def test_runner_sqlite_locked(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    def dummy_connect(*args, **kwargs):
        return DummyConn()

    def fake_window(*args, **kwargs):
        return {
            "summary": {
                "orders_total": 1,
                "filled_total": 1,
                "not_filled_total": 0,
                "symbols": 1,
                "qty_sum": 1.0,
                "avg_price": 100.0,
            }
        }

    monkeypatch.setattr(runner, "_connect_with_retries", dummy_connect)
    monkeypatch.setattr(runner, "run_validation_window", fake_window)
    monkeypatch.setattr(runner, "RealValidationFetcher", LockedFetcher)
    monkeypatch.setenv("VALIDATION_EVIDENCE_DIR", str(tmp_path))

    report = runner.run("2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z")

    assert report["pass"] is False
    assert "sqlite_locked" in report["reasons"]
    assert (tmp_path / "1" / "report.json").exists()


@pytest.mark.unit
def test_runner_invalid_thresholds(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    def dummy_connect(*args, **kwargs):
        return DummyConn()

    def fake_window(*args, **kwargs):
        return {
            "summary": {
                "orders_total": 10,
                "filled_total": 10,
                "not_filled_total": 0,
                "symbols": 1,
                "qty_sum": 20.0,
                "avg_price": 100.0,
            }
        }

    monkeypatch.setattr(runner, "_connect_with_retries", dummy_connect)
    monkeypatch.setattr(runner, "run_validation_window", fake_window)
    monkeypatch.setattr(runner, "RealValidationFetcher", DummyFetcher)
    monkeypatch.setenv("VALIDATION_MIN_FILL_RATE", "not-a-number")
    monkeypatch.setenv("VALIDATION_EVIDENCE_DIR", str(tmp_path))

    report = runner.run("2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z")

    assert report["pass"] is False
    assert any(reason.startswith("invalid_thresholds") for reason in report["reasons"])
    assert report["criteria_used"] == {}
    assert any(path.name == "report.json" for path in tmp_path.rglob("report.json"))
