#!/usr/bin/env python3
"""Core-flow smoke check: Signal -> Risk -> Execution -> DB."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

import psycopg2
import redis

REPORT_PATH = Path("reports/CORE_FLOW_E2E_SMOKE.md")
RISK_HEALTH_URL = "http://localhost:8002/health"
EXECUTION_HEALTH_URL = "http://localhost:8003/health"
ALLOCATION_STREAM = "stream.allocation_decisions"
SIGNALS_STREAM = "stream.signals"
ORDER_RESULTS_STREAM = "stream.order_results"
SIGNALS_TOPIC = "signals"


@dataclass
class SmokeOutcome:
    passed: bool
    signal_id: str
    order_result_status: str | None
    order_count: int
    trade_count: int
    details: list[str]


def _fetch_json(url: str, timeout: int = 3) -> dict[str, Any]:
    with urlopen(url, timeout=timeout) as response:  # noqa: S310
        raw = response.read().decode("utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"unexpected payload from {url}")
    return parsed


def _check_http_health(url: str) -> tuple[bool, str]:
    try:
        payload = _fetch_json(url)
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return False, f"{url} not reachable: {exc}"
    status = str(payload.get("status", "")).lower()
    if status not in {"ok", "running"}:
        return False, f"{url} unhealthy payload: {payload}"
    return True, f"{url} healthy ({status})"


def _connect_redis() -> redis.Redis:
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    password = os.getenv("REDIS_PASSWORD")
    client = redis.Redis(
        host=host,
        port=port,
        password=password,
        db=int(os.getenv("REDIS_DB", "0")),
        decode_responses=True,
    )
    client.ping()
    return client


def _connect_postgres():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "claire_de_binare"),
        user=os.getenv("POSTGRES_USER", "claire_user"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
    )


def _query_count(conn, sql: str, params: tuple[Any, ...] = ()) -> int:
    with conn.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
    return int(row[0]) if row else 0


def _latest_matching_result(
    client: redis.Redis, *, signal_id: str, lookback: int = 100
) -> dict[str, str] | None:
    entries = client.xrevrange(ORDER_RESULTS_STREAM, "+", "-", count=lookback)
    for entry_id, payload in entries:
        if payload.get("signal_id") == signal_id:
            result = dict(payload)
            result["entry_id"] = entry_id
            return result
    return None


def _publish_allocation(
    client: redis.Redis, *, strategy_id: str, allocation_pct: float
) -> None:
    payload = {
        "strategy_id": strategy_id,
        "allocation_pct": f"{allocation_pct:.4f}",
        "timestamp": str(int(time.time())),
    }
    client.xadd(ALLOCATION_STREAM, payload, maxlen=10000)


def _publish_signal(
    client: redis.Redis, *, signal_id: str, strategy_id: str, symbol: str
) -> None:
    now_s = int(time.time())
    payload = {
        "type": "signal",
        "signal_id": signal_id,
        "strategy_id": strategy_id,
        "symbol": symbol,
        "side": "BUY",
        "reason": "core_flow_smoke_probe",
        "timestamp": now_s,
        "ts_ms": now_s * 1000,
        "price": "100000.0",
        "confidence": "0.95",
        "pct_change": "1.0",
        "pct_change_15m": "1.0",
        "volume_15m": "150000.0",
    }
    client.publish(SIGNALS_TOPIC, json.dumps(payload))
    client.xadd(SIGNALS_STREAM, payload, maxlen=10000)


def run_smoke(timeout_seconds: int, verbose: bool) -> SmokeOutcome:
    details: list[str] = []
    signal_id = f"sig-smoke-core-{int(time.time() * 1000)}"
    strategy_id = "paper"
    symbol = "BTCUSDT"

    for endpoint in (RISK_HEALTH_URL, EXECUTION_HEALTH_URL):
        ok, msg = _check_http_health(endpoint)
        details.append(msg)
        if not ok:
            return SmokeOutcome(
                passed=False,
                signal_id=signal_id,
                order_result_status=None,
                order_count=0,
                trade_count=0,
                details=details,
            )

    redis_client = _connect_redis()
    pg_conn = _connect_postgres()
    try:
        baseline_orders = _query_count(pg_conn, "SELECT COUNT(*) FROM orders;")
        baseline_trades = _query_count(pg_conn, "SELECT COUNT(*) FROM trades;")
        details.append(f"baseline orders={baseline_orders}, trades={baseline_trades}")

        _publish_allocation(redis_client, strategy_id=strategy_id, allocation_pct=0.30)
        details.append("published allocation bootstrap for strategy_id=paper")
        time.sleep(0.5)

        _publish_signal(
            redis_client,
            signal_id=signal_id,
            strategy_id=strategy_id,
            symbol=symbol,
        )
        details.append(f"published smoke signal {signal_id}")

        deadline = time.time() + timeout_seconds
        matched_result: dict[str, str] | None = None
        order_count = 0
        trade_count = 0
        while time.time() < deadline:
            matched_result = _latest_matching_result(redis_client, signal_id=signal_id)
            order_count = _query_count(
                pg_conn,
                "SELECT COUNT(*) FROM orders WHERE signal_id = %s;",
                (signal_id,),
            )
            trade_count = _query_count(
                pg_conn,
                "SELECT COUNT(*) FROM trades WHERE signal_id = %s;",
                (signal_id,),
            )
            if matched_result is not None and order_count > 0 and trade_count > 0:
                status = matched_result.get("status")
                details.append(
                    f"matched stream.order_results entry status={status}, orders={order_count}, trades={trade_count}"
                )
                return SmokeOutcome(
                    passed=True,
                    signal_id=signal_id,
                    order_result_status=status,
                    order_count=order_count,
                    trade_count=trade_count,
                    details=details,
                )
            time.sleep(1.0)

        if matched_result is None:
            details.append("no matching stream.order_results event before timeout")
        else:
            details.append(
                "order_result received but DB rows incomplete: "
                f"status={matched_result.get('status')} orders={order_count} trades={trade_count}"
            )
        return SmokeOutcome(
            passed=False,
            signal_id=signal_id,
            order_result_status=(
                matched_result.get("status") if matched_result else None
            ),
            order_count=order_count,
            trade_count=trade_count,
            details=details,
        )
    finally:
        pg_conn.close()


def write_report(outcome: SmokeOutcome) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).isoformat()
    status_line = "PASS" if outcome.passed else "FAIL"
    lines = [
        "# CORE FLOW E2E SMOKE",
        "",
        f"- Generated: `{stamp}`",
        f"- Result: `{status_line}`",
        f"- Signal ID: `{outcome.signal_id}`",
        f"- Order result status: `{outcome.order_result_status or 'n/a'}`",
        f"- Orders persisted for signal: `{outcome.order_count}`",
        f"- Trades persisted for signal: `{outcome.trade_count}`",
        "",
        "## Details",
        "",
    ]
    lines.extend(f"- {detail}" for detail in outcome.details)
    lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run core-flow smoke check.")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=20)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout_seconds <= 0:
        raise ValueError("--timeout-seconds must be > 0")

    outcome = run_smoke(timeout_seconds=args.timeout_seconds, verbose=args.verbose)
    write_report(outcome)

    if args.verbose:
        for detail in outcome.details:
            print(detail)
        print(f"report={REPORT_PATH}")

    if outcome.passed:
        print("CORE_FLOW_E2E_SMOKE: PASS")
        return 0
    print("CORE_FLOW_E2E_SMOKE: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"CORE_FLOW_E2E_SMOKE: ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
