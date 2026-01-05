"\"\"\"Pure-order aggregator used by the 72h validation pipeline.\"\"\""

from __future__ import annotations

from typing import Iterable


def aggregate_orders(orders: Iterable[dict]) -> dict:
    """Aggregate execution orders into simple metrics."""
    total = len(orders)
    filled = sum(1 for order in orders if order.get("status") == "FILLED")
    not_filled = total - filled
    symbols = {order.get("symbol") for order in orders if order.get("symbol")}
    qty_values = [order.get("qty", 0) for order in orders]
    price_orders = [order["price"] for order in orders if order.get("price") is not None]

    avg_price = sum(price_orders) / len(price_orders) if price_orders else 0.0

    return {
        "orders_total": total,
        "filled_total": filled,
        "not_filled_total": not_filled,
        "symbols": len(symbols),
        "qty_sum": sum(qty_values),
        "avg_price": avg_price,
    }
