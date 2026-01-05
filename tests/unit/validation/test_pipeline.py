"\"\"\"Unit tests for validation pipeline orchestration.\"\"\""

from __future__ import annotations

import pytest

from services.validation.pipeline import run_validation_window


class DummyDB:
    pass


@pytest.mark.unit
def test_run_validation_window_wires_collect_to_aggregate(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, object]] = []

    def fake_collect(window_start: str, window_end: str, db_client: object) -> list[dict]:
        calls.append((window_start, window_end, db_client))
        return [
            {"status": "FILLED", "symbol": "BTCUSDT", "qty": 0.5, "price": 42000},
            {"status": "REJECTED", "symbol": "ETHUSDT", "qty": 0.2, "price": 2500},
            {"status": "FILLED", "symbol": "BTCUSDT", "qty": 0.1, "price": 42500},
        ]

    monkeypatch.setattr("services.validation.pipeline.collect_execution_orders", fake_collect)
    window_start = "2026-01-01T00:00:00Z"
    window_end = "2026-01-03T00:00:00Z"
    dummy_db = DummyDB()

    result = run_validation_window(window_start, window_end, dummy_db)

    assert calls == [(window_start, window_end, dummy_db)]
    assert result["window_start"] == window_start
    assert result["window_end"] == window_end
    summary = result["summary"]
    assert summary["orders_total"] == 3
    assert summary["filled_total"] == 2
    assert summary["not_filled_total"] == 1
    assert summary["symbols"] == 2
    assert summary["qty_sum"] == pytest.approx(0.8)
    assert summary["avg_price"] == pytest.approx((42000 + 2500 + 42500) / 3)
