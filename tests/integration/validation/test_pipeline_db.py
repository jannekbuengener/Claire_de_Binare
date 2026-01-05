"\"\"\"Integration test for validation pipeline using the Postgres fixture.\"\"\""

from __future__ import annotations

import pytest

from services.validation.pipeline import run_validation_window


INSERT_ORDER_SQL = """
INSERT INTO orders (
    symbol, side, order_type,
    price, size, approved,
    status, filled_size, avg_fill_price,
    created_at, submitted_at, metadata
) VALUES (
    %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s
)
"""


def _insert_order(cursor, **kwargs) -> None:
    cursor.execute(
        INSERT_ORDER_SQL,
        (
            kwargs["symbol"],
            kwargs["side"],
            kwargs.get("order_type", "market"),
            kwargs["price"],
            kwargs["size"],
            kwargs.get("approved", True),
            kwargs["status"],
            kwargs.get("filled_size", 0.0),
            kwargs.get("avg_fill_price"),
            kwargs["created_at"],
            kwargs["submitted_at"],
            kwargs.get("metadata", "{}"),
        ),
    )


@pytest.mark.integration
def test_pipeline_window_queries_db_window(reset_db) -> None:
    window_start = "2026-01-01T00:00:00+00"
    window_end = "2026-01-02T00:00:00+00"

    with reset_db.cursor() as cursor:
        _insert_order(
            cursor,
            symbol="BTCUSDT",
            side="buy",
            price=42000.0,
            size=0.5,
            status="filled",
            filled_size=0.5,
            avg_fill_price=42000.0,
            created_at="2026-01-01 00:10:00+00",
            submitted_at="2026-01-01 00:10:00+00",
        )
        _insert_order(
            cursor,
            symbol="ETHUSDT",
            side="sell",
            price=2500.0,
            size=1.0,
            status="filled",
            filled_size=1.0,
            avg_fill_price=2500.0,
            created_at="2026-01-01 05:00:00+00",
            submitted_at="2026-01-01 05:00:00+00",
        )
        _insert_order(
            cursor,
            symbol="BNBUSDT",
            side="buy",
            price=310.0,
            size=0.2,
            status="pending",
            filled_size=0.0,
            avg_fill_price=None,
            created_at="2025-12-31 23:00:00+00",
            submitted_at="2025-12-31 23:00:00+00",
        )
    reset_db.commit()

    result = run_validation_window(window_start, window_end, reset_db)
    summary = result["summary"]

    assert summary["orders_total"] == 2
    assert summary["filled_total"] == 2
    assert summary["not_filled_total"] == 0
    assert summary["symbols"] == 2
    assert summary["qty_sum"] == pytest.approx(1.5)
    assert summary["avg_price"] == pytest.approx((42000.0 + 2500.0) / 2)
    assert result["window_start"] == window_start
    assert result["window_end"] == window_end
