"""Paper Runtime Stimulus Runner — Issue #2988

Deterministic, operator-only CLI that publishes a canonical BTCUSDT 1m candle
fixture into the existing runtime ``market_data`` Redis input surface.  Produces
a comparison-grade SIGNAL -> DECISION -> ORDER(paper_) -> FILL chain under
MOCK_TRADING=true / DRY_RUN=true / MEXC_TESTNET=true without modifying any
service logic or runner contract.

Safety boundaries
----------------
- Never authorises Live-Go or Echtgeld-Go.
- LR remains NO-GO in tool output text.
- Publishes ONLY when ``--publish`` is passed AND safety preflight PASSes.
- Default mode is ``--dry-run-preview`` (no Redis write).
- No DB writes.  No secrets/DSNs in output.

Governance references: #2988, #2968, #2969, #2961, #1900

.. note::

    This runner does NOT import or call any DB writer, correlation_ledger module,
    or paper_reference_window_export.  It only publishes to the Redis
    ``market_data`` channel and prints a summary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("paper_runtime_stimulus_runner")

LR_STATUS = "NO-GO"

DEFAULT_FIXTURE_PATH = Path(__file__).resolve().parent.parent.parent / (
    "tests/fixtures/arvp/paper_runtime_stimulus_btcusdt_breakout_v1.json"
)

ONE_MINUTE_MS = 60_000


def _wait_for_breakout_candle_sweep(
    breakout_ts_s: int,
    *,
    interval_s: int = 60,
    pad_s: float = 2.0,
) -> float:
    """Block until cdb_candles sweep can emit the breakout OHLCV window."""
    wait_s = max(0.0, breakout_ts_s + interval_s - time.time()) + pad_s
    if wait_s > 0:
        time.sleep(wait_s)
    return wait_s


def compute_stimulus_run_id(
    base_ts_ms: int, fixture_path: Path, runtime_relative: bool
) -> str:
    """Deterministic, non-secret run identifier for attribution.

    Combines base timestamp, fixture path stem, and mode flag into a short
    hex hash.  Visible in payloads and summary output for traceability.
    """
    raw = f"{base_ts_ms}|{fixture_path.stem}|{runtime_relative}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def align_to_minute(ts_ms: int) -> int:
    """Round down to the nearest 1-minute boundary."""
    return (ts_ms // ONE_MINUTE_MS) * ONE_MINUTE_MS


def resolve_runtime_base_ts_ms(
    spec: FixtureSpec,
    *,
    wall_clock_ms: int | None = None,
    explicit_base_ms: int | None = None,
    extra_offset_minutes: int = 0,
) -> int:
    """Anchor a runtime-relative series so the breakout candle lands on the current minute.

    Without this offset, ``--runtime-relative`` would place warmup at wall-clock *now*
    and push the breakout ~warmup_count minutes into the future, which breaks regime
    lookup anchoring and mixes poorly with live ``market_data``.
    """
    if explicit_base_ms is not None:
        base = align_to_minute(explicit_base_ms)
    else:
        now_ms = wall_clock_ms if wall_clock_ms is not None else int(time.time() * 1000)
        base = align_to_minute(now_ms) - spec.warmup_count * spec.cadence_ms
    if extra_offset_minutes > 0:
        base -= extra_offset_minutes * ONE_MINUTE_MS
    return base


def _fetch_market_close_from_redis(symbol: str) -> float | None:
    """Best-effort read of ``close_now`` from market_state for price anchoring."""
    try:
        import redis as _redis

        client = _redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD"),
            db=int(os.getenv("REDIS_DB", "0")),
            decode_responses=True,
            socket_connect_timeout=2,
        )
        client.ping()
        for prefix in ("market_state", "market_state_shadow"):
            raw = client.get(f"{prefix}:{symbol}")
            if not raw:
                continue
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                continue
            for key in ("close_now", "close"):
                value = parsed.get(key)
                if value is None or value == "":
                    continue
                close = float(value)
                if close > 0:
                    return close
    except Exception:
        return None
    return None


def resolve_runtime_warmup_base_price(
    spec: FixtureSpec,
    *,
    explicit_base_price: float | None = None,
    market_close: float | None = None,
) -> float:
    """Choose a warmup start price that ends near the live market close when possible."""
    if explicit_base_price is not None and explicit_base_price > 0:
        return explicit_base_price
    if market_close is not None and market_close > 0:
        return market_close - (spec.warmup_count - 1) * spec.warmup_price_step
    return spec.warmup_base_price


REQUIRED_SAFETY_ENV = {
    "MOCK_TRADING": "true",
    "DRY_RUN": "true",
    "MEXC_TESTNET": "true",
}

REJECTED_ENV = {
    "LIVE_TRADING_CONFIRMED": "yes",
}


@dataclass(frozen=True, slots=True)
class SafetyPreflightResult:
    passed: bool
    checks: dict[str, str]
    failures: list[str]

    def summary(self) -> str:
        lines = ["=== Safety Preflight ==="]
        for k, v in self.checks.items():
            lines.append(f"  {k}: {v}")
        if self.failures:
            lines.append("FAILURES:")
            for f in self.failures:
                lines.append(f"  - {f}")
        lines.append(f"  LR status: {LR_STATUS}")
        lines.append(f"  Result: {'PASS' if self.passed else 'REJECT'}")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class FixtureSpec:
    strategy_id: str
    symbol: str
    cadence_ms: int
    entry_lookback_minutes: int
    exit_lookback_minutes: int
    breakout_buffer: float
    min_minutes_between_entries: int
    warmup_count: int
    warmup_base_ts_ms: int
    warmup_base_price: float
    warmup_price_step: float
    warmup_volume: float
    warmup_trade_qty: str
    warmup_regime_id: int
    warmup_market_state_fresh: bool
    warmup_regime_fresh: bool
    breakout_close_premium_pct: float
    breakout_volume: float
    breakout_trade_qty: str


def run_safety_preflight() -> SafetyPreflightResult:
    checks: dict[str, str] = {}
    failures: list[str] = []

    for key, expected in REQUIRED_SAFETY_ENV.items():
        actual = os.getenv(key, "").lower()
        passed = actual == expected
        checks[key] = (
            f"{'PASS' if passed else 'FAIL'} (expected={expected!r}, actual={actual!r})"
        )
        if not passed:
            failures.append(f"{key}={actual!r} (expected {expected!r})")

    for key, rejected_val in REJECTED_ENV.items():
        actual = os.getenv(key, "").lower()
        detected = actual == rejected_val
        checks[key] = f"{'REJECT' if detected else 'OK'} (actual={actual!r})"
        if detected:
            failures.append(f"{key}={actual!r} is explicitly rejected")

    use_real_balance = os.getenv("USE_REAL_BALANCE", "false").lower()
    checks["USE_REAL_BALANCE"] = (
        f"{'OK' if use_real_balance != 'true' else 'REJECT'} (actual={use_real_balance!r})"
    )
    if use_real_balance == "true":
        failures.append(f"USE_REAL_BALANCE=true is rejected")

    return SafetyPreflightResult(
        passed=len(failures) == 0,
        checks=checks,
        failures=failures,
    )


def load_fixture_spec(path: Path) -> FixtureSpec:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    warmup = raw["warmup"]
    breakout = raw["breakout"]

    return FixtureSpec(
        strategy_id=raw["strategy_id"],
        symbol=raw["symbol"],
        cadence_ms=raw["cadence_ms"],
        entry_lookback_minutes=raw["entry_lookback_minutes"],
        exit_lookback_minutes=raw["exit_lookback_minutes"],
        breakout_buffer=raw["breakout_buffer"],
        min_minutes_between_entries=raw["min_minutes_between_entries"],
        warmup_count=warmup["count"],
        warmup_base_ts_ms=warmup["base_ts_ms"],
        warmup_base_price=warmup["base_price"],
        warmup_price_step=warmup["price_step"],
        warmup_volume=warmup["volume"],
        warmup_trade_qty=warmup["trade_qty"],
        warmup_regime_id=warmup["regime_id"],
        warmup_market_state_fresh=warmup["market_state_fresh"],
        warmup_regime_fresh=warmup["regime_fresh"],
        breakout_close_premium_pct=breakout["close_premium_pct"],
        breakout_volume=breakout["volume"],
        breakout_trade_qty=breakout["trade_qty"],
    )


def validate_fixture_spec(spec: FixtureSpec) -> list[str]:
    errors: list[str] = []

    if spec.strategy_id != "primary_breakout_v1":
        errors.append(
            f"strategy_id must be primary_breakout_v1, got {spec.strategy_id!r}"
        )

    if spec.symbol != "BTCUSDT":
        errors.append(
            f"symbol must be BTCUSDT for primary_breakout_v1, got {spec.symbol!r}"
        )

    if spec.cadence_ms != ONE_MINUTE_MS:
        errors.append(f"cadence_ms must be {ONE_MINUTE_MS} (1m), got {spec.cadence_ms}")

    max_lookback = max(spec.entry_lookback_minutes, spec.exit_lookback_minutes)
    if spec.warmup_count < max_lookback:
        errors.append(
            f"warmup_count ({spec.warmup_count}) must be >= max lookback ({max_lookback})"
        )

    if spec.breakout_buffer < 0:
        errors.append(f"breakout_buffer must be >= 0, got {spec.breakout_buffer}")

    if spec.warmup_price_step <= 0:
        errors.append(f"warmup_price_step must be > 0, got {spec.warmup_price_step}")

    if spec.breakout_close_premium_pct <= 0:
        errors.append(
            f"breakout_close_premium_pct must be > 0, got {spec.breakout_close_premium_pct}"
        )

    if spec.min_minutes_between_entries < 0:
        errors.append(
            f"min_minutes_between_entries must be >= 0, "
            f"got {spec.min_minutes_between_entries}"
        )

    return errors


def generate_fixture_candles(
    spec: FixtureSpec,
    *,
    base_ts_ms_override: int | None = None,
    warmup_base_price_override: float | None = None,
    stimulus_run_id: str | None = None,
) -> list[dict[str, Any]]:
    candles: list[dict[str, Any]] = []
    base_ts = (
        base_ts_ms_override
        if base_ts_ms_override is not None
        else spec.warmup_base_ts_ms
    )
    warmup_base_price = (
        warmup_base_price_override
        if warmup_base_price_override is not None
        else spec.warmup_base_price
    )

    for i in range(spec.warmup_count):
        ts_ms = base_ts + i * spec.cadence_ms
        price = warmup_base_price + i * spec.warmup_price_step
        candle = {
            "symbol": spec.symbol,
            "ts_ms": ts_ms,
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "volume": spec.warmup_volume,
            "trade_qty": spec.warmup_trade_qty,
            "source": "stimulus_fixture",
            "side": "buy",
            "regime_id": spec.warmup_regime_id,
            "market_state_fresh": spec.warmup_market_state_fresh,
            "regime_fresh": spec.warmup_regime_fresh,
        }
        if stimulus_run_id is not None:
            candle["stimulus_run_id"] = stimulus_run_id
        candles.append(candle)

    warmup_end_ts_ms = base_ts + spec.warmup_count * spec.cadence_ms
    highest_high = warmup_base_price + (spec.warmup_count - 1) * spec.warmup_price_step
    breakout_threshold = highest_high * (1 + spec.breakout_buffer)
    # Minimal lift above threshold: preserves breakout fires=true while keeping ATR
    # near the warmup cadence (large premium spikes classify HIGH_VOL_CHAOTIC).
    breakout_close = breakout_threshold + spec.warmup_price_step

    breakout_candle = {
        "symbol": spec.symbol,
        "ts_ms": warmup_end_ts_ms,
        "open": highest_high,
        "high": breakout_close,
        "low": highest_high,
        "close": breakout_close,
        "volume": spec.breakout_volume,
        "trade_qty": spec.breakout_trade_qty,
        "source": "stimulus_fixture",
        "side": "buy",
        "regime_id": spec.warmup_regime_id,
        "market_state_fresh": spec.warmup_market_state_fresh,
        "regime_fresh": spec.warmup_regime_fresh,
    }
    if stimulus_run_id is not None:
        breakout_candle["stimulus_run_id"] = stimulus_run_id
    candles.append(breakout_candle)

    return candles


def to_market_data_payload(candle: dict[str, Any]) -> dict[str, Any]:
    """Convert a candle dict to a market_data pub/sub payload.

    Follows the schema expected by ``SignalEngine.process_market_data`` and
    ``MarketData.from_dict``.  Includes ``regime_id``, ``market_state_fresh``,
    ``regime_fresh`` at the top level so that
    ``_process_primary_breakout_v1`` reads them from ``raw_data``.
    """
    payload = {
        "schema_version": "v1.0",
        "source": candle.get("source", "stimulus_fixture"),
        "symbol": candle["symbol"],
        "ts_ms": candle["ts_ms"],
        "price": str(candle["close"]),
        "trade_qty": candle.get("trade_qty", "1.0"),
        "side": candle.get("side", "buy"),
        "close": candle["close"],
        "high": candle["high"],
        "low": candle["low"],
        "open": candle.get("open", candle["close"]),
        "volume": candle["volume"],
        "regime_id": candle["regime_id"],
        "market_state_fresh": candle["market_state_fresh"],
        "regime_fresh": candle["regime_fresh"],
    }
    run_id = candle.get("stimulus_run_id")
    if run_id is not None:
        payload["stimulus_run_id"] = run_id
    return payload


def fixture_summary(
    spec: FixtureSpec,
    candles: list[dict[str, Any]],
    *,
    stimulus_run_id: str | None = None,
    runtime_relative: bool = False,
) -> str:
    warmup_start = candles[0]["ts_ms"]
    warmup_end = candles[-2]["ts_ms"] if len(candles) > 1 else candles[0]["ts_ms"]
    breakout_ts = candles[-1]["ts_ms"]
    warmup_base = candles[0]["close"]
    highest_high = warmup_base + (spec.warmup_count - 1) * spec.warmup_price_step
    breakout_threshold = highest_high * (1 + spec.breakout_buffer)
    breakout_close = candles[-1]["close"]
    mode = "runtime-relative" if runtime_relative else "static-historical"

    lines = [
        f"=== Fixture Summary ===",
        f"  mode: {mode}",
        f"  strategy_id: {spec.strategy_id}",
        f"  symbol: {spec.symbol}",
        f"  cadence: 1m ({spec.cadence_ms} ms)",
        f"  warmup candles: {spec.warmup_count}",
        f"  breakout candles: 1",
        f"  total candles: {len(candles)}",
        f"  warmup range: ts_ms {warmup_start} - {warmup_end}",
        f"  breakout ts_ms: {breakout_ts}",
        f"  highest_high (warmup): {highest_high}",
        f"  breakout threshold (highest_high * (1 + {spec.breakout_buffer})): {breakout_threshold}",
        f"  breakout close: {breakout_close}",
        f"  breakout fires: {breakout_close > breakout_threshold}",
        f"  LR status: {LR_STATUS}",
    ]
    if stimulus_run_id is not None:
        lines.append(f"  stimulus_run_id: {stimulus_run_id}")
    return "\n".join(lines)


class StimulusPublisher:
    """Injectable publisher abstraction for market_data events.

    In production mode, publishes to Redis ``market_data`` channel.
    In tests, can be replaced with a mock.
    """

    def __init__(
        self,
        redis_host: str = "redis",
        redis_port: int = 6379,
        redis_password: Optional[str] = None,
        redis_db: int = 0,
    ):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_password = redis_password
        self.redis_db = redis_db
        self._client: Any = None

    def _get_client(self):
        if self._client is None:
            import redis as _redis

            self._client = _redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                db=self.redis_db,
                decode_responses=True,
            )
            self._client.ping()
        return self._client

    def publish(self, channel: str, message: str) -> int:
        client = self._get_client()
        return client.publish(channel, message)

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


def run_preview(
    candles: list[dict[str, Any]],
    spec: FixtureSpec,
    *,
    stimulus_run_id: str | None = None,
    runtime_relative: bool = False,
) -> str:
    payloads = [to_market_data_payload(c) for c in candles]
    summary = fixture_summary(
        spec,
        candles,
        stimulus_run_id=stimulus_run_id,
        runtime_relative=runtime_relative,
    )
    lines = [
        summary,
        f"=== Preview Mode (no Redis publish) ===",
        f"  intended market_data events: {len(payloads)}",
        f"  expected chain target: SIGNAL >= 1, DECISION >= 1, ORDER(paper_) >= 1, FILL >= 1",
        f"  next runtime validation command:",
        f"    python -m services.validation.paper_runtime_stimulus_runner --publish --fixture <path>",
        f"  (requires running BLUE/RED stack with MOCK_TRADING=true)",
    ]
    return "\n".join(lines)


def run_publish(
    candles: list[dict[str, Any]],
    spec: FixtureSpec,
    publisher: StimulusPublisher,
    max_wait_seconds: int = 300,
    delay_seconds: float = 0.01,
    stop_after_complete_chain: bool = False,
    *,
    stimulus_run_id: str | None = None,
    runtime_relative: bool = False,
) -> str:
    payloads = [to_market_data_payload(c) for c in candles]
    summary = fixture_summary(
        spec,
        candles,
        stimulus_run_id=stimulus_run_id,
        runtime_relative=runtime_relative,
    )
    logger.info(summary)

    published = 0
    expected_events = len(payloads) + (1 if runtime_relative else 0)
    follow_up_tick_published = False
    follow_up_tick_ts_ms: int | None = None
    follow_up_tick_price: float | None = None
    sweep_wait_s = 0.0

    for i, payload in enumerate(payloads):
        message = json.dumps(payload)
        try:
            publisher.publish("market_data", message)
            published += 1
        except Exception as exc:
            logger.error("Failed to publish candle %d: %s", i, exc)
            break

        if delay_seconds > 0 and i < len(payloads) - 1:
            time.sleep(delay_seconds)

    if runtime_relative and published == len(payloads):
        breakout_ts_s = int(candles[-1]["ts_ms"] // 1000)
        sweep_wait_s = _wait_for_breakout_candle_sweep(
            breakout_ts_s, interval_s=spec.cadence_ms // 1000
        )
        follow_up_payload = to_market_data_payload(candles[-1])
        follow_up_tick_ts_ms = int(time.time() * 1000)
        follow_up_payload["ts_ms"] = follow_up_tick_ts_ms
        if stimulus_run_id is not None:
            follow_up_payload["stimulus_run_id"] = stimulus_run_id
        try:
            publisher.publish("market_data", json.dumps(follow_up_payload))
            published += 1
            follow_up_tick_published = True
            follow_up_tick_price = float(candles[-1]["close"])
        except Exception as exc:
            logger.error("Failed to publish follow-up tick: %s", exc)

    lines = [
        summary,
        f"=== Publish Result ===",
        f"  published: {published}/{expected_events} market_data events",
        f"  burst_published: {published - (1 if follow_up_tick_published else 0)}/{len(payloads)}",
        f"  follow_up_tick_published: {follow_up_tick_published}",
        f"  follow_up_tick_ts_ms: {follow_up_tick_ts_ms}",
        f"  follow_up_tick_price: {follow_up_tick_price}",
        f"  sweep_wait_s: {sweep_wait_s:.1f}",
        f"  stop_after_complete_chain: {stop_after_complete_chain}",
        f"  max_wait_seconds: {max_wait_seconds}",
        f"  LR status: {LR_STATUS}",
        f"  NOTE: This tool does not authorise Live-Go or Echtgeld-Go.",
        f"  To verify chain formation, query the audit ledger after runtime processes events.",
    ]
    return "\n".join(lines)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Paper Runtime Stimulus Runner — deterministic market_data fixture publisher "
            "for comparison-grade paper windows. Does NOT authorise Live-Go."
        ),
    )
    parser.add_argument(
        "--dry-run-preview",
        action="store_true",
        default=True,
        help="Preview fixture without publishing (default).",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        default=False,
        help="Publish fixture to Redis market_data channel. Requires safety preflight PASS.",
    )
    parser.add_argument(
        "--symbol",
        default="BTCUSDT",
        help="Trading symbol (default: BTCUSDT).",
    )
    parser.add_argument(
        "--strategy-id",
        default="primary_breakout_v1",
        help="Strategy ID (default: primary_breakout_v1).",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE_PATH,
        help="Path to fixture JSON file.",
    )
    parser.add_argument(
        "--max-wait-seconds",
        type=int,
        default=300,
        help="Maximum wait time for chain formation (default: 300).",
    )
    parser.add_argument(
        "--stop-after-complete-chain",
        action="store_true",
        default=False,
        help="Stop after detecting one complete SIGNAL->DECISION->ORDER(paper_)->FILL chain.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0.01,
        help="Delay between candle publications in seconds (default: 0.01).",
    )
    parser.add_argument(
        "--runtime-relative",
        action="store_true",
        default=False,
        help=(
            "Shift fixture timestamps to current wall-clock (or --base-ts-ms) "
            "aligned to 1m cadence. Preserves candle shape and breakout condition."
        ),
    )
    parser.add_argument(
        "--base-ts-ms",
        type=int,
        default=None,
        help=(
            "Explicit base timestamp in ms for --runtime-relative mode. "
            "Defaults to current wall-clock aligned to 1m boundary."
        ),
    )
    parser.add_argument(
        "--start-offset-minutes",
        type=int,
        default=0,
        help=(
            "Additional backward shift (minutes) applied after the runtime-relative "
            "warmup anchor. Default 0: breakout candle aligns to the current minute."
        ),
    )
    parser.add_argument(
        "--base-price",
        type=float,
        default=None,
        help=(
            "Override warmup start price. When omitted in --runtime-relative mode, "
            "the runner tries market_state close_now before falling back to the fixture."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s"
    )

    preflight = run_safety_preflight()
    print(preflight.summary())

    if not preflight.passed:
        if args.publish:
            print("SAFETY PREFLIGHT FAILED — publish not allowed.")
            return 2

    spec = load_fixture_spec(args.fixture)

    errors = validate_fixture_spec(spec)
    if errors:
        print("FIXTURE VALIDATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 3

    base_ts_ms_override: int | None = None
    warmup_base_price_override: float | None = None
    runtime_relative = args.runtime_relative
    if runtime_relative:
        base_ts_ms_override = resolve_runtime_base_ts_ms(
            spec,
            explicit_base_ms=args.base_ts_ms,
            extra_offset_minutes=args.start_offset_minutes,
        )
        market_close = _fetch_market_close_from_redis(spec.symbol)
        warmup_base_price_override = resolve_runtime_warmup_base_price(
            spec,
            explicit_base_price=args.base_price,
            market_close=market_close,
        )

    run_id = compute_stimulus_run_id(
        (
            base_ts_ms_override
            if base_ts_ms_override is not None
            else spec.warmup_base_ts_ms
        ),
        args.fixture,
        runtime_relative,
    )

    candles = generate_fixture_candles(
        spec,
        base_ts_ms_override=base_ts_ms_override,
        warmup_base_price_override=warmup_base_price_override,
        stimulus_run_id=run_id,
    )

    if spec.symbol != args.symbol:
        print(f"FIXTURE symbol {spec.symbol!r} does not match --symbol {args.symbol!r}")
        return 3
    if spec.strategy_id != args.strategy_id:
        print(
            f"FIXTURE strategy_id {spec.strategy_id!r} does not match "
            f"--strategy-id {args.strategy_id!r}"
        )
        return 3

    if not args.publish:
        output = run_preview(
            candles,
            spec,
            stimulus_run_id=run_id,
            runtime_relative=runtime_relative,
        )
        print(output)
        return 0

    if not preflight.passed:
        print("SAFETY PREFLIGHT FAILED — cannot proceed with publish.")
        return 2

    publisher = StimulusPublisher(
        redis_host=os.getenv("REDIS_HOST", "redis"),
        redis_port=int(os.getenv("REDIS_PORT", "6379")),
        redis_password=os.getenv("REDIS_PASSWORD"),
        redis_db=int(os.getenv("REDIS_DB", "0")),
    )
    try:
        output = run_publish(
            candles,
            spec,
            publisher,
            max_wait_seconds=args.max_wait_seconds,
            delay_seconds=args.delay_seconds,
            stop_after_complete_chain=args.stop_after_complete_chain,
            stimulus_run_id=run_id,
            runtime_relative=runtime_relative,
        )
        print(output)
        return 0
    finally:
        publisher.close()


if __name__ == "__main__":
    sys.exit(main())
