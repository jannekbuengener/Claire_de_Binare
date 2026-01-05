"""Pass/fail evaluation for 72h validation summaries."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict

from core.utils.clock import utcnow


@dataclass(frozen=True)
class GateThresholds:
    """Thresholds for validation gate decisions."""

    min_orders: int
    min_fill_rate: float
    min_qty_sum: float

    @classmethod
    def from_env(cls) -> "GateThresholds":
        return cls(
            min_orders=int(os.getenv("VALIDATION_MIN_ORDERS", "1")),
            min_fill_rate=float(os.getenv("VALIDATION_MIN_FILL_RATE", "0.45")),
            min_qty_sum=float(os.getenv("VALIDATION_MIN_QTY_SUM", "0.0")),
        )


class GateEvaluator:
    """Evaluate metrics and return a structured gate decision."""

    def __init__(self, thresholds: GateThresholds | None = None) -> None:
        self.thresholds = thresholds or GateThresholds.from_env()

    def evaluate(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        orders_total = int(summary.get("orders_total", 0) or 0)
        filled_total = int(summary.get("filled_total", 0) or 0)
        qty_sum = float(summary.get("qty_sum", 0.0) or 0.0)
        fill_rate = float(filled_total / orders_total) if orders_total else 0.0

        criteria = {
            "min_orders": {
                "threshold": self.thresholds.min_orders,
                "actual": orders_total,
                "pass": orders_total >= self.thresholds.min_orders,
            },
            "min_fill_rate": {
                "threshold": self.thresholds.min_fill_rate,
                "actual": fill_rate,
                "pass": fill_rate >= self.thresholds.min_fill_rate,
            },
            "min_qty_sum": {
                "threshold": self.thresholds.min_qty_sum,
                "actual": qty_sum,
                "pass": qty_sum >= self.thresholds.min_qty_sum,
            },
        }

        failed = [name for name, info in criteria.items() if not info["pass"]]
        overall_pass = not failed

        if overall_pass and fill_rate >= 0.6:
            risk_level = "low"
        elif overall_pass:
            risk_level = "medium"
        else:
            risk_level = "high"

        reason = "all criteria passed" if overall_pass else f"failed: {', '.join(failed)}"

        return {
            "timestamp": utcnow().isoformat(),
            "overall_pass": overall_pass,
            "risk_assessment": risk_level,
            "criteria_results": criteria,
            "reason": reason,
        }
