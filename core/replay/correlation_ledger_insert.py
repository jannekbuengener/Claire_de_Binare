"""Correlation ledger insert result classification (#3970 / #3956 regression)."""

from __future__ import annotations

from enum import Enum
from typing import Any


class CorrelationLedgerInsertResult(str, Enum):
    INSERTED = "inserted"
    CONFLICT = "conflict"
    SKIPPED = "skipped"
    ERROR = "error"


def classify_insert_rowcount(rowcount: int) -> CorrelationLedgerInsertResult:
    """Map psycopg2 rowcount after INSERT ... ON CONFLICT DO NOTHING."""
    if rowcount == 1:
        return CorrelationLedgerInsertResult.INSERTED
    if rowcount == 0:
        return CorrelationLedgerInsertResult.CONFLICT
    return CorrelationLedgerInsertResult.ERROR


def evaluate_false_zero_event_risk(
    *,
    ledger_lane_count: int | None,
    insert_conflicts_total: int | None,
    signals_generated_total: int | None,
) -> dict[str, Any]:
    """Distinguish true zero activity from conflict-suppressed ledger rows."""
    lane = ledger_lane_count if ledger_lane_count is not None else 0
    conflicts = insert_conflicts_total or 0
    signals = signals_generated_total or 0
    false_zero_risk = lane <= 0 and (conflicts > 0 or signals > 0)
    return {
        "false_zero_event_risk": false_zero_risk,
        "ledger_lane_count": ledger_lane_count,
        "insert_conflicts_total": insert_conflicts_total,
        "signals_generated_total": signals_generated_total,
        "interpretation": (
            "ledger_insert_conflict_or_signal_without_ledger_row"
            if false_zero_risk
            else "no_false_zero_risk_detected"
        ),
    }


def parse_prometheus_counter(metrics_body: str, metric_name: str) -> int | None:
    """Parse a counter value from Prometheus text exposition."""
    total = 0
    found = False
    prefix = metric_name
    for line in metrics_body.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        if line.startswith(prefix):
            found = True
            parts = line.rsplit(" ", 1)
            if len(parts) == 2:
                try:
                    total += int(float(parts[1]))
                except ValueError:
                    continue
    return total if found else None
