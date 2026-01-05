"""CLI runner for 72h validation windows."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any, Dict

from core.utils.clock import utcnow
from core.utils.postgres_client import create_postgres_connection
from services.risk.real_validation_fetcher import RealValidationFetcher
from services.validation.gate_evaluator import GateEvaluator
from services.validation.pipeline import run_validation_window


def _parse_iso(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _fill_rate(summary: Dict[str, Any]) -> float:
    orders_total = int(summary.get("orders_total", 0) or 0)
    filled_total = int(summary.get("filled_total", 0) or 0)
    return float(filled_total / orders_total) if orders_total else 0.0


def run(window_start: str, window_end: str) -> Dict[str, Any]:
    conn = create_postgres_connection()
    try:
        summary = run_validation_window(window_start, window_end, conn)
    finally:
        conn.close()

    orders_summary = summary["summary"]
    win_rate = _fill_rate(orders_summary)
    duration_hours = (
        _parse_iso(window_end) - _parse_iso(window_start)
    ).total_seconds() / 3600

    metrics = {
        "total_trades": int(orders_summary.get("orders_total", 0) or 0),
        "win_rate": win_rate,
        "total_pnl": 0.0,
        "max_drawdown": 0.0,
        "sharpe_ratio": 0.0,
        "avg_trade_duration": "0h",
        "largest_loss": 0.0,
        "largest_win": 0.0,
        "final_balance": 0.0,
    }

    evaluation = GateEvaluator().evaluate(orders_summary)

    report = {
        "window_start": window_start,
        "window_end": window_end,
        "duration_hours": duration_hours,
        "orders_summary": orders_summary,
        "metrics": metrics,
        "evaluation": evaluation,
        "generated_at": utcnow().isoformat(),
    }

    fetcher = RealValidationFetcher()
    run_id = fetcher.start_72h_validation(start_time=_parse_iso(window_start).isoformat())
    fetcher.update_validation_progress(
        run_id,
        metrics,
        summary=orders_summary,
        validation=evaluation,
        report=report,
    )
    fetcher.complete_validation(
        run_id,
        evaluation["overall_pass"],
        end_time=_parse_iso(window_end).isoformat(),
    )
    report["validation_run_id"] = run_id

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a 72h validation window.")
    parser.add_argument("--window-start", required=True, help="ISO-8601 window start")
    parser.add_argument("--window-end", required=True, help="ISO-8601 window end")
    args = parser.parse_args()

    report = run(args.window_start, args.window_end)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
