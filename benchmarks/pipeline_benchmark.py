"""Deterministic, offline performance benchmark for the core pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
import platform
import random
import time
import tracemalloc
from typing import Iterable

from core.domain.models import Order, OrderResult, Signal


@dataclass(frozen=True)
class MarketData:
    symbol: str
    price: float
    volume: float
    pct_change: float
    timestamp: int


@dataclass(frozen=True)
class BenchmarkConfig:
    iterations: int = 1000
    warmup: int = 100
    seed: int = 42
    threshold_pct: float = 2.0
    min_volume: float = 100_000.0
    strategy_id: str = "bench-strategy"
    allocation_pct: float = 0.25
    test_balance: float = 10_000.0
    max_position_pct: float = 0.10
    max_exposure_pct: float = 0.30


@dataclass
class RiskState:
    total_exposure: float = 0.0
    positions: dict[str, float] = None

    def __post_init__(self) -> None:
        if self.positions is None:
            self.positions = {}


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    rank = int((percentile / 100.0) * (len(sorted_vals) - 1))
    return sorted_vals[rank]


def _generate_market_data(count: int, seed: int) -> list[MarketData]:
    rng = random.Random(seed)
    now = int(time.time())
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT"]
    data: list[MarketData] = []
    for i in range(count):
        symbol = symbols[i % len(symbols)]
        price = 100.0 + rng.random() * 100.0
        pct_change = rng.uniform(-1.0, 5.0)
        volume = rng.uniform(50_000.0, 200_000.0)
        data.append(
            MarketData(
                symbol=symbol,
                price=price,
                volume=volume,
                pct_change=pct_change,
                timestamp=now + i,
            )
        )
    return data


def _market_to_signal(event: MarketData, config: BenchmarkConfig) -> Signal | None:
    if event.pct_change < config.threshold_pct:
        return None
    if event.volume < config.min_volume:
        return None
    return Signal(
        signal_id=f"{event.symbol}-{event.timestamp}",
        strategy_id=config.strategy_id,
        symbol=event.symbol,
        side="BUY",
        timestamp=event.timestamp,
        price=event.price,
        pct_change=event.pct_change,
        reason=f"pct_change>={config.threshold_pct}",
    )


def _risk_to_order(signal: Signal, config: BenchmarkConfig, state: RiskState) -> Order | None:
    if not signal.strategy_id:
        return None

    max_position_value = config.test_balance * config.max_position_pct
    position_value = max_position_value * config.allocation_pct
    max_exposure = config.test_balance * config.max_exposure_pct

    if state.total_exposure + position_value > max_exposure:
        return None

    quantity = position_value / max(signal.price or 1.0, 1e-9)
    return Order(
        order_id=f"order-{signal.signal_id}",
        symbol=signal.symbol,
        side=signal.side or "BUY",
        quantity=quantity,
        price=signal.price,
        signal_id=signal.signal_id,
        reason=signal.reason,
        timestamp=signal.timestamp,
        client_id=f"{signal.symbol}-{signal.timestamp}",
    )


def _execute_order(order: Order) -> OrderResult:
    return OrderResult(
        order_id=order.order_id or "",
        status="FILLED",
        symbol=order.symbol,
        side=order.side,
        quantity=order.quantity,
        filled_quantity=order.quantity,
        timestamp=int(time.time()),
        price=order.price,
        client_id=order.client_id,
    )


def _update_exposure(state: RiskState, result: OrderResult) -> None:
    if result.price is None:
        return
    notional = result.filled_quantity * result.price
    state.total_exposure += notional
    state.positions[result.symbol] = state.positions.get(result.symbol, 0.0) + notional


def _run_pipeline(events: Iterable[MarketData], config: BenchmarkConfig) -> list[float]:
    latencies_ms: list[float] = []
    state = RiskState()
    for event in events:
        start = time.perf_counter()
        signal = _market_to_signal(event, config)
        if signal:
            order = _risk_to_order(signal, config, state)
            if order:
                result = _execute_order(order)
                _update_exposure(state, result)
        end = time.perf_counter()
        latencies_ms.append((end - start) * 1000.0)
    return latencies_ms


def run_benchmark(config: BenchmarkConfig) -> dict:
    startup_start = time.perf_counter()
    warmup_events = _generate_market_data(config.warmup, config.seed)
    run_events = _generate_market_data(config.iterations, config.seed + 1)
    _run_pipeline(warmup_events, config)
    startup_end = time.perf_counter()

    tracemalloc.start()
    cpu_start = time.process_time()
    wall_start = time.perf_counter()
    latencies_ms = _run_pipeline(run_events, config)
    wall_end = time.perf_counter()
    cpu_end = time.process_time()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    total_wall = max(wall_end - wall_start, 1e-9)

    metrics = {
        "p50_ms": _percentile(latencies_ms, 50),
        "p95_ms": _percentile(latencies_ms, 95),
        "p99_ms": _percentile(latencies_ms, 99),
        "throughput_eps": len(latencies_ms) / total_wall,
        "cpu_time_s": cpu_end - cpu_start,
        "wall_time_s": total_wall,
        "memory_peak_kb": peak / 1024.0,
        "startup_s": startup_end - startup_start,
    }

    return {
        "meta": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "commit": os.getenv("GIT_COMMIT", "unknown"),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
        },
        "config": {
            "iterations": config.iterations,
            "warmup": config.warmup,
            "seed": config.seed,
            "threshold_pct": config.threshold_pct,
            "min_volume": config.min_volume,
            "strategy_id": config.strategy_id,
            "allocation_pct": config.allocation_pct,
            "test_balance": config.test_balance,
            "max_position_pct": config.max_position_pct,
            "max_exposure_pct": config.max_exposure_pct,
        },
        "metrics": metrics,
    }
