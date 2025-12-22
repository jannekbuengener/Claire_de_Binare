import json
import logging
import os
import time
from datetime import datetime, timezone
from urllib import request
from urllib.error import URLError, HTTPError

import pytest

from tests.e2e.support import (
    circuit_breaker_disabled,
    resolve_stream_candidates,
    resolve_stream_name,
    reset_circuit_breaker,
)

logger = logging.getLogger(__name__)

ORDER_RESULTS_STREAM = resolve_stream_name(
    ("STREAM_ORDER_RESULTS",), "order_results"
)
ALLOCATION_STREAM = resolve_stream_name(
    ("RISK_ALLOCATION_STREAM",), "stream.allocation_decisions"
)
BOT_SHUTDOWN_STREAMS = resolve_stream_candidates(
    ("RISK_BOT_SHUTDOWN_STREAM", "STREAM_BOT_SHUTDOWN"),
    "stream.bot_shutdown",
)
RISK_RESET_STREAM = resolve_stream_name(
    ("RISK_RESET_STREAM",), "stream.risk_reset"
)
ORDERS_STREAM = resolve_stream_name(("RISK_ORDERS_STREAM",), "stream.orders")


def _refresh_stream_names() -> None:
    global ORDER_RESULTS_STREAM
    global ALLOCATION_STREAM
    global BOT_SHUTDOWN_STREAMS
    global RISK_RESET_STREAM
    global ORDERS_STREAM
    ORDER_RESULTS_STREAM = resolve_stream_name(
        ("STREAM_ORDER_RESULTS",), "order_results"
    )
    ALLOCATION_STREAM = resolve_stream_name(
        ("RISK_ALLOCATION_STREAM",), "stream.allocation_decisions"
    )
    BOT_SHUTDOWN_STREAMS = resolve_stream_candidates(
        ("RISK_BOT_SHUTDOWN_STREAM", "STREAM_BOT_SHUTDOWN"),
        "stream.bot_shutdown",
    )
    RISK_RESET_STREAM = resolve_stream_name(
        ("RISK_RESET_STREAM",), "stream.risk_reset"
    )
    ORDERS_STREAM = resolve_stream_name(("RISK_ORDERS_STREAM",), "stream.orders")


def _load_dotenv_for_e2e() -> None:
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        return
    load_dotenv(override=False)


def _http_get_json(url: str, timeout: float = 2.0) -> dict:
    try:
        with request.urlopen(url, timeout=timeout) as response:
            payload = response.read()
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"HTTP request failed for {url}: {exc}") from exc
    return json.loads(payload.decode("utf-8"))


def _wait_for_stream(
    redis_client, stream: str, start_id: str, timeout_s: float, match=None
) -> list:
    deadline = time.time() + timeout_s
    results: list[dict] = []
    last_id = start_id
    while time.time() < deadline:
        entries = redis_client.xread({stream: last_id}, count=10, block=1000)
        if not entries:
            continue
        for _stream, messages in entries:
            for entry_id, payload in messages:
                last_id = entry_id
                if match is None or match(payload):
                    results.append(payload)
        if results:
            break
    return results


def _get_stream_last_id(redis_client, stream: str) -> str:
    try:
        info = redis_client.xinfo_stream(stream)
        return info.get("last-generated-id", "0-0")
    except Exception:
        return "0-0"


def _check_diagnostics(result: dict, expected_status: str) -> None:
    """Verify rejection diagnostics are present for REJECTED orders."""
    status = result.get("status", "").lower()

    if status == "rejected":
        # Must have diagnostics
        assert result.get("source_service"), f"Missing source_service in {result}"
        assert result.get("reject_reason_code"), f"Missing reject_reason_code in {result}"
        assert result.get("reject_stage"), f"Missing reject_stage in {result}"
        # causing_event_id is optional but recommended

        logger.info(
            "✅ Rejection diagnostics: source=%s reason=%s stage=%s event=%s",
            result.get("source_service"),
            result.get("reject_reason_code"),
            result.get("reject_stage"),
            result.get("causing_event_id"),
        )


def _wait_for_db_rows(
    pg_conn,
    table: str,
    symbol: str,
    since: datetime,
    min_rows: int,
    timeout_s: float = 10,
) -> int:
    deadline = time.time() + timeout_s
    last_count = 0
    while time.time() < deadline:
        last_count = _count_rows(pg_conn, table, symbol, since)
        if last_count >= min_rows:
            break
        time.sleep(0.5)
    return last_count


def _wait_for_orders_blocked(risk_url: str, baseline: int, timeout_s: float = 5) -> int:
    deadline = time.time() + timeout_s
    last_blocked = baseline
    while time.time() < deadline:
        try:
            status = _http_get_json(f"{risk_url}/status")
            last_blocked = int(status.get("orders_blocked", 0))
        except Exception:
            time.sleep(0.5)
            continue
        if last_blocked > baseline:
            break
        time.sleep(0.5)
    return last_blocked


@pytest.fixture(scope="module")
def e2e_env():
    if not os.getenv("E2E_RUN"):
        pytest.skip("Set E2E_RUN=1 to enable E2E tests.")

    try:
        import redis
    except ModuleNotFoundError:
        pytest.skip("redis package not installed.")

    try:
        import psycopg2
    except ModuleNotFoundError:
        pytest.skip("psycopg2 package not installed.")

    _load_dotenv_for_e2e()
    _refresh_stream_names()

    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_password = os.getenv("REDIS_PASSWORD")
    redis_client = redis.Redis(
        host=redis_host,
        port=redis_port,
        password=redis_password or None,
        decode_responses=True,
    )
    try:
        redis_client.ping()
    except Exception as exc:
        pytest.skip(f"Redis not reachable at {redis_host}:{redis_port}: {exc}")

    reset_circuit_breaker(redis_client)

    pg_host = os.getenv("POSTGRES_HOST", "localhost")
    pg_port = int(os.getenv("POSTGRES_PORT", "5432"))
    pg_db = os.getenv("POSTGRES_DB", "claire_de_binare")
    pg_user = os.getenv("POSTGRES_USER", "claire_user")
    pg_password = os.getenv("POSTGRES_PASSWORD")
    if not pg_password:
        pytest.skip("POSTGRES_PASSWORD not set for E2E tests.")

    try:
        pg_conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            database=pg_db,
            user=pg_user,
            password=pg_password,
        )
    except Exception as exc:
        pytest.skip(f"Postgres not reachable at {pg_host}:{pg_port}: {exc}")

    risk_url = os.getenv("RISK_URL", "http://localhost:8002")
    execution_url = os.getenv("EXECUTION_URL", "http://localhost:8003")
    core_url = os.getenv("CORE_URL", "http://localhost:8001")

    for name, url in {
        "risk": f"{risk_url}/health",
        "execution": f"{execution_url}/health",
        "core": f"{core_url}/health",
    }.items():
        try:
            _http_get_json(url)
        except Exception as exc:
            pytest.skip(f"{name} service not reachable: {exc}")

    yield {
        "redis": redis_client,
        "pg": pg_conn,
        "risk_url": risk_url,
        "execution_url": execution_url,
    }

    pg_conn.close()


def _set_allocation(redis_client, strategy_id: str, allocation_pct: float) -> None:
    redis_client.xadd(
        ALLOCATION_STREAM,
        {"strategy_id": strategy_id, "allocation_pct": allocation_pct, "cooldown_until": 0},
        maxlen=10000,
    )


def _publish_signal(redis_client, symbol: str, strategy_id: str) -> None:
    payload = {
        "type": "signal",
        "signal_id": f"{strategy_id}-{int(time.time())}",
        "strategy_id": strategy_id,
        "symbol": symbol,
        "side": "BUY",
        "direction": "BUY",
        "strength": 1.0,
        "confidence": 0.9,
        "price": 50000,
        "pct_change": 5.0,
        "timestamp": int(time.time()),
        "signal_type": "buy",
        "metadata": {"source": "e2e"},
    }
    redis_client.publish("signals", json.dumps(payload))


def _publish_order(redis_client, symbol: str, strategy_id: str) -> None:
    payload = {
        "type": "order",
        "order_id": f"e2e_{int(time.time() * 1000)}",
        "symbol": symbol,
        "side": "BUY",
        "quantity": 0.01,
        "price": 50000,
        "timestamp": int(time.time()),
        "strategy_id": strategy_id,
    }
    redis_client.publish("orders", json.dumps(payload))


def _publish_order_result(
    redis_client,
    symbol: str,
    strategy_id: str,
    side: str,
    quantity: float,
    price: float,
    status: str = "FILLED",
    bot_id: str | None = None,
    reject_reason_code: str | None = None,
    error_message: str | None = None,
    filled_quantity: float | None = None,
) -> None:
    resolved_status = status.upper()
    resolved_filled = (
        filled_quantity
        if filled_quantity is not None
        else (quantity if resolved_status == "FILLED" else 0.0)
    )
    payload = {
        "type": "order_result",
        "order_id": f"e2e_result_{int(time.time() * 1000)}",
        "status": resolved_status,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "filled_quantity": resolved_filled,
        "price": price,
        "timestamp": int(time.time()),
        "strategy_id": strategy_id,
        "bot_id": bot_id,
        "reject_reason_code": reject_reason_code,
        "error_message": error_message,
    }
    redis_client.publish("order_results", json.dumps(payload))


def _count_rows(pg_conn, table: str, symbol: str, since: datetime) -> int:
    column = "created_at" if table == "orders" else "timestamp"
    with pg_conn.cursor() as cursor:
        cursor.execute(
            f"SELECT COUNT(*) FROM {table} WHERE symbol = %s AND {column} >= %s",
            (symbol, since),
        )
        return int(cursor.fetchone()[0])


@pytest.mark.e2e
def test_tc_p0_001_happy_path_market_to_trade(e2e_env):
    """TC-P0-001: Happy Path (market_data -> trade)."""
    redis_client = e2e_env["redis"]
    pg_conn = e2e_env["pg"]

    symbol = "E2E_P0_001"
    strategy_id = "e2e_p0_001"

    _set_allocation(redis_client, strategy_id, allocation_pct=0.5)
    time.sleep(1)
    start_id = _get_stream_last_id(redis_client, ORDER_RESULTS_STREAM)
    started_at = datetime.now(timezone.utc)

    for _ in range(3):
        _publish_signal(redis_client, symbol, strategy_id)

    results = _wait_for_stream(
        redis_client,
        ORDER_RESULTS_STREAM,
        start_id,
        timeout_s=15,
        match=lambda r: r.get("symbol") == symbol and r.get("strategy_id") == strategy_id,
    )

    assert results, "No order_results received for TC-P0-001."

    # Check diagnostics for all results
    for r in results:
        _check_diagnostics(r, expected_status="filled")

    statuses = {r.get("status", "").lower() for r in results}
    assert "filled" in statuses, f"Expected FILLED result, got: {statuses}"

    orders_count = _wait_for_db_rows(pg_conn, "orders", symbol, started_at, min_rows=1)
    trades_count = _wait_for_db_rows(pg_conn, "trades", symbol, started_at, min_rows=1)

    assert orders_count > 0, "Expected at least one order persisted."
    assert trades_count > 0, "Expected at least one trade persisted."


@pytest.mark.e2e
def test_tc_p0_002_risk_block_position_limit(e2e_env):
    """TC-P0-002: Risk Blockierung (Position Limit)."""
    redis_client = e2e_env["redis"]
    risk_url = e2e_env["risk_url"]

    symbol = "E2E_P0_002"
    strategy_id = "e2e_p0_002"

    before = _http_get_json(f"{risk_url}/status")
    blocked_before = before.get("orders_blocked", 0)

    _set_allocation(redis_client, strategy_id, allocation_pct=0.0)
    start_id = _get_stream_last_id(redis_client, ORDER_RESULTS_STREAM)

    _publish_signal(redis_client, symbol, strategy_id)

    blocked_after = _wait_for_orders_blocked(risk_url, blocked_before)

    assert blocked_after > blocked_before, "Expected risk layer to block oversized order."

    results = _wait_for_stream(
        redis_client,
        ORDER_RESULTS_STREAM,
        start_id,
        timeout_s=4,
        match=lambda r: r.get("symbol") == symbol and r.get("strategy_id") == strategy_id,
    )
    assert not results, "Blocked order should not reach execution."


@pytest.mark.e2e
def test_tc_p0_003_daily_drawdown_stop(e2e_env):
    """TC-P0-003: Daily Drawdown Stop."""
    redis_client = e2e_env["redis"]
    risk_url = e2e_env["risk_url"]

    symbol = "E2E_P0_003"
    strategy_id = "e2e_p0_003"
    bot_id = "e2e_p0_003_bot"

    _set_allocation(redis_client, strategy_id, allocation_pct=0.5)
    time.sleep(1)

    status = _http_get_json(f"{risk_url}/status")
    risk_state = status.get("risk_state", {})
    peak_equity = float(
        risk_state.get("peak_equity")
        or risk_state.get("equity")
        or risk_state.get("initial_balance")
        or 10000.0
    )
    if peak_equity <= 0:
        boost_buy = 1.0
        boost_sell = 1000.0
        boost_target = abs(peak_equity) + 1000.0
        boost_qty = max(boost_target / (boost_sell - boost_buy), 1.0)
        _publish_order_result(
            redis_client, symbol, strategy_id, "BUY", boost_qty, boost_buy, bot_id=bot_id
        )
        _publish_order_result(
            redis_client, symbol, strategy_id, "SELL", boost_qty, boost_sell, bot_id=bot_id
        )
        time.sleep(0.5)
        status = _http_get_json(f"{risk_url}/status")
        risk_state = status.get("risk_state", {})
        peak_equity = float(
            risk_state.get("peak_equity")
            or risk_state.get("equity")
            or risk_state.get("initial_balance")
            or 10000.0
        )

    max_drawdown_pct = float(os.getenv("MAX_DAILY_DRAWDOWN_PCT", "0.05"))
    target_loss = peak_equity * (max_drawdown_pct + 0.05)
    buy_price = 1000.0
    sell_price = 100.0
    qty = max(target_loss / (buy_price - sell_price), 1.0)

    _publish_order_result(
        redis_client, symbol, strategy_id, "BUY", qty, buy_price, bot_id=bot_id
    )
    _publish_order_result(
        redis_client, symbol, strategy_id, "SELL", qty, sell_price, bot_id=bot_id
    )

    deadline = time.time() + 5
    breaker_active = False
    while time.time() < deadline:
        status = _http_get_json(f"{risk_url}/status")
        breaker_active = bool(
            status.get("risk_state", {}).get("circuit_breaker", False)
        )
        if breaker_active:
            break
        time.sleep(0.5)

    assert breaker_active, "Expected circuit breaker to be active after drawdown."

    start_id = _get_stream_last_id(redis_client, ORDER_RESULTS_STREAM)
    blocked_before = _http_get_json(f"{risk_url}/status").get("orders_blocked", 0)

    _publish_signal(redis_client, symbol, strategy_id)

    blocked_after = _wait_for_orders_blocked(risk_url, blocked_before)
    assert blocked_after > blocked_before, "Expected drawdown guard to block signals."

    results = _wait_for_stream(
        redis_client,
        ORDER_RESULTS_STREAM,
        start_id,
        timeout_s=4,
        match=lambda r: r.get("symbol") == symbol and r.get("strategy_id") == strategy_id,
    )
    assert not results, "Blocked drawdown signal should not reach execution."

    redis_client.xadd(RISK_RESET_STREAM, {"reset_type": "all"}, maxlen=10000)
    time.sleep(1)


@pytest.mark.e2e
def test_tc_p0_004_circuit_breaker_trigger(e2e_env):
    """TC-P0-004: Circuit Breaker Trigger."""
    if circuit_breaker_disabled():
        pytest.skip("E2E_DISABLE_CIRCUIT_BREAKER=1 disables bot-shutdown handling.")

    redis_client = e2e_env["redis"]
    risk_url = e2e_env["risk_url"]

    symbol = "E2E_P0_004"
    strategy_id = "e2e_p0_004"
    bot_id = "e2e_p0_004_bot"

    shutdown_start_ids = {
        stream: _get_stream_last_id(redis_client, stream)
        for stream in BOT_SHUTDOWN_STREAMS
    }
    orders_start_id = _get_stream_last_id(redis_client, ORDERS_STREAM)
    failure_threshold = int(os.getenv("CIRCUIT_MAX_CONSECUTIVE_FAILURES", "3"))

    for _ in range(max(failure_threshold, 1)):
        _publish_order_result(
            redis_client,
            symbol,
            strategy_id,
            side="BUY",
            quantity=1.0,
            price=100.0,
            status="REJECTED",
            bot_id=bot_id,
            reject_reason_code="EXECUTION_REJECTED",
            error_message="e2e forced rejection",
        )

    shutdown_events: list[dict] = []
    for stream in BOT_SHUTDOWN_STREAMS:
        shutdown_events = _wait_for_stream(
            redis_client,
            stream,
            shutdown_start_ids.get(stream, "0-0"),
            timeout_s=10,
            match=lambda r: r.get("strategy_id") == strategy_id
            and r.get("priority") == "SAFETY",
        )
        if shutdown_events:
            break

    assert shutdown_events, "Expected circuit breaker shutdown event."

    deadline = time.time() + 5
    breaker_active = False
    while time.time() < deadline:
        status = _http_get_json(f"{risk_url}/status")
        breaker_active = bool(status.get("risk_state", {}).get("circuit_breaker"))
        if breaker_active:
            break
        time.sleep(0.5)

    assert breaker_active, "Expected circuit breaker to be active after failures."

    blocked_before = _http_get_json(f"{risk_url}/status").get("orders_blocked", 0)
    _publish_signal(redis_client, symbol, strategy_id)

    blocked_after = _wait_for_orders_blocked(risk_url, blocked_before)
    assert blocked_after > blocked_before, "Expected circuit breaker to block signals."

    orders = _wait_for_stream(
        redis_client,
        ORDERS_STREAM,
        orders_start_id,
        timeout_s=4,
        match=lambda r: r.get("symbol") == symbol and r.get("strategy_id") == strategy_id,
    )
    assert not orders, "Circuit breaker should prevent new orders after latch."

    redis_client.xadd(RISK_RESET_STREAM, {"reset_type": "all"}, maxlen=10000)
    time.sleep(1)


@pytest.mark.e2e
def test_tc_p0_005_data_persistence_check(e2e_env):
    """TC-P0-005: Data Persistence Check."""
    redis_client = e2e_env["redis"]
    pg_conn = e2e_env["pg"]

    symbol = "E2E_P0_005"
    strategy_id = "e2e_p0_005"

    _set_allocation(redis_client, strategy_id, allocation_pct=0.5)
    time.sleep(1)
    start_id = _get_stream_last_id(redis_client, ORDER_RESULTS_STREAM)
    started_at = datetime.now(timezone.utc)

    _publish_signal(redis_client, symbol, strategy_id)
    results = _wait_for_stream(
        redis_client,
        ORDER_RESULTS_STREAM,
        start_id,
        timeout_s=15,
        match=lambda r: r.get("symbol") == symbol and r.get("strategy_id") == strategy_id,
    )

    assert results, "No order_results received for persistence check."

    # Check diagnostics for all results
    for r in results:
        _check_diagnostics(r, expected_status="filled")

    statuses = {r.get("status", "").lower() for r in results}
    assert "filled" in statuses, f"Expected FILLED result, got: {statuses}"

    orders_count = _wait_for_db_rows(pg_conn, "orders", symbol, started_at, min_rows=1)
    trades_count = _wait_for_db_rows(pg_conn, "trades", symbol, started_at, min_rows=1)

    assert orders_count > 0, "Expected orders table to contain rows."
    assert trades_count > 0, "Expected trades table to contain rows."
