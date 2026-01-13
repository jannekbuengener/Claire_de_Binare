"""CLI runner for 72h validation windows.

Classification: worker/CLI (no HTTP/health endpoint).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable

from core.utils.clock import utcnow
from core.utils.postgres_client import create_postgres_connection
from services.risk.real_validation_fetcher import RealValidationFetcher
from services.validation.gate_evaluator import GateEvaluator, ThresholdConfigError
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


def _default_summary() -> Dict[str, Any]:
    return {
        "orders_total": 0,
        "filled_total": 0,
        "not_filled_total": 0,
        "symbols": 0,
        "qty_sum": 0.0,
        "avg_price": 0.0,
    }


def _connect_with_retries(
    connect_timeout: int = 5, retries: int = 2, sleep_seconds: float = 0.5
) -> Any:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return create_postgres_connection(connect_timeout=connect_timeout)
        except Exception as exc:  # pragma: no cover - raised on connection failure
            last_error = exc
            if attempt < retries:
                time.sleep(sleep_seconds)
    if last_error:
        raise last_error
    raise RuntimeError("Failed to connect to Postgres")


def _derive_reasons(reasons: Iterable[str]) -> list[str]:
    return [item for item in reasons if item]


def _build_metrics(summary: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "total_trades": int(summary.get("orders_total", 0) or 0),
        "win_rate": _fill_rate(summary),
        "total_pnl": 0.0,
        "max_drawdown": 0.0,
        "sharpe_ratio": 0.0,
        "avg_trade_duration": "0h",
        "largest_loss": 0.0,
        "largest_win": 0.0,
        "final_balance": 0.0,
    }


def _redacted_env() -> str:
    sensitive_markers = ("PASSWORD", "SECRET", "KEY", "TOKEN")
    allowed_prefixes = ("VALIDATION_", "POSTGRES_", "ENV", "LOG_LEVEL")
    lines: list[str] = []
    for key in sorted(os.environ):
        if not key.startswith(allowed_prefixes):
            continue
        value = os.environ.get(key, "")
        if any(marker in key for marker in sensitive_markers):
            value = "***REDACTED***"
        lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


def _write_evidence(report_dir: Path, report: Dict[str, Any]) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "report.json"
    stdout_path = report_dir / "stdout.log"
    env_path = report_dir / "env_redacted.txt"
    hash_path = report_dir / "report.json.sha256"

    payload = json.dumps(report, indent=2, sort_keys=True)
    report_path.write_text(payload, encoding="utf-8")
    stdout_path.write_text(payload + "\n", encoding="utf-8")
    env_path.write_text(_redacted_env(), encoding="utf-8")

    digest = hashlib.sha256(report_path.read_bytes()).hexdigest()
    hash_path.write_text(f"{digest}  report.json\n", encoding="utf-8")


def run(window_start: str, window_end: str) -> Dict[str, Any]:
    generated_at = utcnow().isoformat()
    summary = _default_summary()
    reasons: list[str] = []
    criteria_used: Dict[str, Any] = {}
    duration_hours = 0.0
    parsed_start = None
    parsed_end = None

    try:
        parsed_start = _parse_iso(window_start)
        parsed_end = _parse_iso(window_end)
        duration_hours = (parsed_end - parsed_start).total_seconds() / 3600
    except ValueError as exc:
        reasons.append(f"invalid_window: {exc.__class__.__name__}")
        parsed_start = utcnow()
        parsed_end = parsed_start

    try:
        conn = _connect_with_retries()
        try:
            summary_payload = run_validation_window(window_start, window_end, conn)
            summary = summary_payload["summary"]
        finally:
            conn.close()
    except Exception as exc:
        reasons.append(f"db_unreachable: {exc.__class__.__name__}")

    try:
        evaluator = GateEvaluator()
        evaluation = evaluator.evaluate(summary)
        criteria_used = evaluation.get("criteria_used", {})
    except ThresholdConfigError as exc:
        evaluation = {
            "timestamp": generated_at,
            "overall_pass": False,
            "risk_assessment": "high",
            "criteria_results": {},
            "criteria_used": {},
            "reasons": [f"invalid_thresholds: {exc}"],
            "reason": "invalid thresholds",
        }
    except Exception as exc:  # pragma: no cover - defensive fallback
        evaluation = {
            "timestamp": generated_at,
            "overall_pass": False,
            "risk_assessment": "high",
            "criteria_results": {},
            "criteria_used": {},
            "reasons": [f"gate_error: {exc.__class__.__name__}"],
            "reason": "gate evaluation failed",
        }

    reasons = _derive_reasons([*evaluation.get("reasons", []), *reasons])
    overall_pass = bool(evaluation.get("overall_pass")) and not any(
        reason.startswith(("invalid_", "db_", "sqlite_")) for reason in reasons
    )

    evaluation["overall_pass"] = overall_pass
    evaluation["reasons"] = reasons
    evaluation["reason"] = "all criteria passed" if overall_pass else ", ".join(reasons)

    criteria_used = criteria_used or evaluation.get("criteria_used", {})
    metrics = _build_metrics(summary)

    report: Dict[str, Any] = {
        "schema_version": "1",
        "window_start": window_start,
        "window_end": window_end,
        "generated_at": generated_at,
        "orders_total": summary.get("orders_total", 0),
        "filled_total": summary.get("filled_total", 0),
        "not_filled_total": summary.get("not_filled_total", 0),
        "symbols": summary.get("symbols", 0),
        "pass": overall_pass,
        "reasons": reasons,
        "criteria_used": criteria_used,
        "duration_hours": duration_hours,
        "orders_summary": summary,
        "metrics": metrics,
        "evaluation": evaluation,
    }

    fetcher = RealValidationFetcher()
    run_id: int | None = None
    try:
        run_id = fetcher.start_72h_validation(start_time=parsed_start.isoformat())
    except Exception as exc:
        reasons.append(f"sqlite_start_failed: {exc.__class__.__name__}")

    if run_id is not None:
        report["validation_run_id"] = run_id
        try:
            fetcher.update_validation_progress(
                run_id,
                metrics,
                summary=summary,
                validation=evaluation,
                report=report,
            )
        except Exception as exc:
            reason = "sqlite_locked" if "locked" in str(exc).lower() else "sqlite_error"
            reasons.append(reason)

        try:
            fetcher.complete_validation(
                run_id,
                overall_pass,
                end_time=parsed_end.isoformat(),
            )
        except Exception as exc:
            reason = "sqlite_locked" if "locked" in str(exc).lower() else "sqlite_error"
            reasons.append(reason)

    report["reasons"] = _derive_reasons(reasons)
    report["pass"] = overall_pass and not any(
        reason.startswith(("invalid_", "db_", "sqlite_"))
        for reason in report["reasons"]
    )
    evaluation["overall_pass"] = report["pass"]
    evaluation["reasons"] = report["reasons"]
    evaluation["reason"] = (
        "all criteria passed" if report["pass"] else ", ".join(report["reasons"])
    )

    evidence_root = Path(
        os.getenv("VALIDATION_EVIDENCE_DIR", "/app/data/validation_runs")
    )
    evidence_id = (
        str(run_id) if run_id is not None else utcnow().strftime("local-%Y%m%dT%H%M%S")
    )
    _write_evidence(evidence_root / evidence_id, report)

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
