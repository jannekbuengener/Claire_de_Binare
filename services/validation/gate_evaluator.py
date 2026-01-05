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
            min_orders=_parse_int_env("VALIDATION_MIN_ORDERS", 1),
            min_fill_rate=_parse_float_env(
                "VALIDATION_MIN_FILL_RATE", 0.45, min_value=0.0, max_value=1.0
            ),
            min_qty_sum=_parse_float_env(
                "VALIDATION_MIN_QTY_SUM", 0.0, min_value=0.0, max_value=None
            ),
        )

    def as_dict(self) -> Dict[str, float | int]:
        return {
            "min_orders": self.min_orders,
            "min_fill_rate": self.min_fill_rate,
            "min_qty_sum": self.min_qty_sum,
        }


class ThresholdConfigError(ValueError):
    """Raised when gate threshold environment values are invalid."""


def _parse_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip()
    if not value:
        raise ThresholdConfigError(f"{name} is empty")
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ThresholdConfigError(f"{name} must be an integer") from exc
    if parsed < 0:
        raise ThresholdConfigError(f"{name} must be >= 0")
    return parsed


def _parse_float_env(
    name: str, default: float, min_value: float | None, max_value: float | None
) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip()
    if not value:
        raise ThresholdConfigError(f"{name} is empty")
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ThresholdConfigError(f"{name} must be a float") from exc
    if min_value is not None and parsed < min_value:
        raise ThresholdConfigError(f"{name} must be >= {min_value}")
    if max_value is not None and parsed > max_value:
        raise ThresholdConfigError(f"{name} must be <= {max_value}")
    return parsed


class GateEvaluator:
    """Evaluate metrics and return a structured gate decision."""

    def __init__(self, thresholds: GateThresholds | None = None) -> None:
        self.thresholds = thresholds or GateThresholds.from_env()

    def evaluate(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        orders_total = int(summary.get("orders_total", 0) or 0)
        filled_total = int(summary.get("filled_total", 0) or 0)
        qty_sum = float(summary.get("qty_sum", 0.0) or 0.0)
        fill_rate = float(filled_total / orders_total) if orders_total else 0.0

        criteria_used = self.thresholds.as_dict()
        criteria = {
            "min_orders": {
                "threshold": criteria_used["min_orders"],
                "actual": orders_total,
                "pass": orders_total >= criteria_used["min_orders"],
            },
            "min_fill_rate": {
                "threshold": criteria_used["min_fill_rate"],
                "actual": fill_rate,
                "pass": fill_rate >= criteria_used["min_fill_rate"],
            },
            "min_qty_sum": {
                "threshold": criteria_used["min_qty_sum"],
                "actual": qty_sum,
                "pass": qty_sum >= criteria_used["min_qty_sum"],
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

        reasons = ["all criteria passed"] if overall_pass else failed
        reason = (
            "all criteria passed"
            if overall_pass
            else f"failed: {', '.join(failed)}"
        )

        return {
            "timestamp": utcnow().isoformat(),
            "overall_pass": overall_pass,
            "risk_assessment": risk_level,
            "criteria_results": criteria,
            "criteria_used": criteria_used,
            "reasons": reasons,
            "reason": reason,
        }
