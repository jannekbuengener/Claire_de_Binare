from unittest.mock import MagicMock

import pytest

from services.reports.daily_orders_summary import fetch_summary, format_email_body


@pytest.mark.unit
def test_fetch_summary_maps_positive_trade_metrics():
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = (12, 9, 1, 1, 1, 1234.5, 4, 3, 75.0, 2.5)
    cursor.fetchall.return_value = [("risk_limit", 1)]

    summary = fetch_summary(conn, hours=24)

    assert summary["total_trades"] == 4
    assert summary["positive_trades"] == 3
    assert summary["positive_trade_rate"] == 75.0
    assert summary["total_fees"] == 2.5


@pytest.mark.unit
def test_format_email_body_includes_positive_trade_metrics():
    html = format_email_body(
        {
            "total_orders": 12,
            "filled": 9,
            "rejected": 1,
            "cancelled": 1,
            "pending": 1,
            "notional": 1234.5,
            "total_trades": 4,
            "positive_trades": 3,
            "positive_trade_rate": 75.0,
            "total_fees": 2.5,
            "rejections": [],
        },
        __import__("datetime").datetime(2026, 4, 8, 0, 0),
        __import__("datetime").datetime(2026, 4, 9, 0, 0),
    )

    assert "Trades Made:</strong> 4" in html
    assert "Positive Trades:</strong> 3" in html
    assert "Positive Trade Rate:</strong> 75.0%" in html
