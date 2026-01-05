"""Integration test: runner writes report even on failure."""

from __future__ import annotations

import pytest

from services.validation import runner


class SharedConn:
    def __init__(self, conn) -> None:
        self._conn = conn

    def cursor(self, *args, **kwargs):
        return self._conn.cursor(*args, **kwargs)

    def close(self) -> None:
        pass


@pytest.mark.integration
def test_runner_writes_report_on_fail(monkeypatch: pytest.MonkeyPatch, tmp_path, reset_db) -> None:
    monkeypatch.setenv("VALIDATION_MIN_ORDERS", "bad")
    monkeypatch.setenv("VALIDATION_EVIDENCE_DIR", str(tmp_path))
    monkeypatch.setenv("VALIDATION_DB_PATH", str(tmp_path / "validation_results.db"))
    monkeypatch.setattr(
        runner,
        "_connect_with_retries",
        lambda *args, **kwargs: SharedConn(reset_db),
    )

    report = runner.run("2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z")

    assert report["pass"] is False
    assert any(reason.startswith("invalid_thresholds") for reason in report["reasons"])
    assert (tmp_path / "1" / "report.json").exists()
