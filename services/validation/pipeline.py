"""Minimal validation pipeline that wires collectors to aggregators."""

from __future__ import annotations

from services.validation.aggregator import aggregate_orders
from services.validation.collectors import (
    ExecutionCollector,
    ExecutionCollectorConfig,
)


def collect_execution_orders(window_start: str, window_end: str, db_client: object) -> list[dict]:
    """Run a read-only collector query and return normalized orders."""
    config = ExecutionCollectorConfig(db_client=db_client, redis_client=None)
    collector = ExecutionCollector(config=config)
    return collector.collect_execution_orders(window_start, window_end)


def run_validation_window(window_start: str, window_end: str, db_client: object) -> dict:
    """Single-shot pipeline iteration collecting + aggregating metrics."""
    orders = collect_execution_orders(window_start, window_end, db_client)
    summary = aggregate_orders(orders)
    return {
        "window_start": window_start,
        "window_end": window_end,
        "summary": summary,
    }
