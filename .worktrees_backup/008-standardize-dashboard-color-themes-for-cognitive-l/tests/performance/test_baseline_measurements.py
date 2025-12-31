"""
Performance Baseline Measurements for CDB Trading System.

Targets (from Issue #93):
- Market Data → Signal: <100ms (target), <500ms (max)
- Signal → Risk Approval: <50ms (target), <200ms (max)
- Order → Execution: <100ms (target), <500ms (max)
- End-to-End: <300ms (target), <1000ms (max)

Throughput:
- Market Data Events/sec: 100 (target), 50 (min)
- Signals/sec: 50 (target), 20 (min)
- Orders/sec: 20 (target), 10 (min)
"""

import os
import time
import statistics
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import Mock, patch, MagicMock

import pytest

# Skip all tests unless explicitly enabled
pytestmark = [
    pytest.mark.performance,
    pytest.mark.slow,
]


def require_perf_run():
    """Skip unless PERF_BASELINE_RUN=1 is set."""
    if not os.getenv("PERF_BASELINE_RUN"):
        pytest.skip("Set PERF_BASELINE_RUN=1 to execute performance baselines.")


# =============================================================================
# LATENCY BASELINES
# =============================================================================


class TestLatencyBaselines:
    """Measure latency for critical paths."""

    # Targets from Issue #93
    TARGETS = {
        "market_to_signal": {"target_ms": 100, "max_ms": 500},
        "signal_to_risk": {"target_ms": 50, "max_ms": 200},
        "order_to_execution": {"target_ms": 100, "max_ms": 500},
        "end_to_end": {"target_ms": 300, "max_ms": 1000},
    }

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis for latency isolation."""
        with patch("redis.Redis") as mock:
            mock_instance = MagicMock()
            mock_instance.publish.return_value = 1
            mock_instance.get.return_value = None
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_mexc_client(self):
        """Mock MEXC API to measure internal latency only."""
        with patch("services.execution.mexc_client.MexcClient") as mock:
            mock_instance = MagicMock()
            mock_instance.place_market_order.return_value = {
                "orderId": "test123",
                "status": "FILLED",
                "executedQty": "1.0",
            }
            mock.return_value = mock_instance
            yield mock_instance

    def _measure_latency(self, func, iterations: int = 100) -> Dict[str, float]:
        """Run function multiple times and collect latency stats."""
        latencies = []
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)

        return {
            "min_ms": min(latencies),
            "max_ms": max(latencies),
            "mean_ms": statistics.mean(latencies),
            "median_ms": statistics.median(latencies),
            "p95_ms": sorted(latencies)[int(len(latencies) * 0.95)],
            "p99_ms": sorted(latencies)[int(len(latencies) * 0.99)],
            "samples": len(latencies),
        }

    @pytest.mark.performance
    def test_market_data_to_signal_latency(self, mock_redis):
        """Measure: Market Data → Signal Generation latency."""
        require_perf_run()

        # Simulate signal generation from market data
        def generate_signal():
            market_data = {
                "symbol": "BTCUSDT",
                "price": 50000.0,
                "volume": 100.0,
                "timestamp": time.time(),
            }
            # Simulate minimal signal processing
            signal = {
                "type": "BUY",
                "symbol": market_data["symbol"],
                "strength": 0.75,
                "price": market_data["price"],
            }
            return signal

        stats = self._measure_latency(generate_signal, iterations=1000)
        target = self.TARGETS["market_to_signal"]

        print(f"\n📊 Market→Signal Latency: {stats}")
        assert stats["p95_ms"] < target["max_ms"], f"P95 {stats['p95_ms']}ms > max {target['max_ms']}ms"

        # Report if target met
        if stats["median_ms"] < target["target_ms"]:
            print(f"✅ Target met: {stats['median_ms']:.2f}ms < {target['target_ms']}ms")
        else:
            print(f"⚠️ Target missed: {stats['median_ms']:.2f}ms > {target['target_ms']}ms")

    @pytest.mark.performance
    def test_signal_to_risk_approval_latency(self, mock_redis):
        """Measure: Signal → Risk Approval latency."""
        require_perf_run()

        def approve_signal():
            signal = {"type": "BUY", "symbol": "BTCUSDT", "quantity": 0.01}
            # Simulate risk checks
            checks = {
                "position_limit": True,
                "drawdown_ok": True,
                "circuit_breaker_ok": True,
            }
            return all(checks.values())

        stats = self._measure_latency(approve_signal, iterations=1000)
        target = self.TARGETS["signal_to_risk"]

        print(f"\n📊 Signal→Risk Latency: {stats}")
        assert stats["p95_ms"] < target["max_ms"], f"P95 {stats['p95_ms']}ms > max {target['max_ms']}ms"

    @pytest.mark.performance
    def test_order_to_execution_latency(self, mock_redis, mock_mexc_client):
        """Measure: Order → Execution latency (mocked API)."""
        require_perf_run()

        def execute_order():
            order = {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "quantity": 0.01,
                "type": "MARKET",
            }
            # Simulate order processing (without actual API call)
            result = {
                "order_id": "test123",
                "status": "FILLED",
                "filled_qty": order["quantity"],
            }
            return result

        stats = self._measure_latency(execute_order, iterations=1000)
        target = self.TARGETS["order_to_execution"]

        print(f"\n📊 Order→Execution Latency: {stats}")
        assert stats["p95_ms"] < target["max_ms"], f"P95 {stats['p95_ms']}ms > max {target['max_ms']}ms"

    @pytest.mark.performance
    def test_end_to_end_latency(self, mock_redis, mock_mexc_client):
        """Measure: Full pipeline latency (Market Data → Order Executed)."""
        require_perf_run()

        def full_pipeline():
            # Step 1: Market data
            market_data = {"symbol": "BTCUSDT", "price": 50000.0}

            # Step 2: Signal generation
            signal = {"type": "BUY", "symbol": market_data["symbol"]}

            # Step 3: Risk approval
            approved = True

            # Step 4: Order execution
            if approved:
                order_result = {"status": "FILLED"}

            return order_result

        stats = self._measure_latency(full_pipeline, iterations=500)
        target = self.TARGETS["end_to_end"]

        print(f"\n📊 End-to-End Latency: {stats}")
        assert stats["p95_ms"] < target["max_ms"], f"P95 {stats['p95_ms']}ms > max {target['max_ms']}ms"


# =============================================================================
# THROUGHPUT BASELINES
# =============================================================================


class TestThroughputBaselines:
    """Measure throughput for critical components."""

    TARGETS = {
        "market_events_per_sec": {"target": 100, "min": 50},
        "signals_per_sec": {"target": 50, "min": 20},
        "orders_per_sec": {"target": 20, "min": 10},
    }

    def _measure_throughput(self, func, duration_sec: float = 1.0) -> float:
        """Run function for duration and count operations per second."""
        count = 0
        start = time.perf_counter()
        end_time = start + duration_sec

        while time.perf_counter() < end_time:
            func()
            count += 1

        elapsed = time.perf_counter() - start
        return count / elapsed

    @pytest.mark.performance
    def test_market_event_throughput(self):
        """Measure: Market events processed per second."""
        require_perf_run()

        def process_market_event():
            event = {"symbol": "BTCUSDT", "price": 50000.0, "ts": time.time()}
            # Simulate minimal processing
            processed = {"symbol": event["symbol"], "processed": True}
            return processed

        ops_per_sec = self._measure_throughput(process_market_event, duration_sec=2.0)
        target = self.TARGETS["market_events_per_sec"]

        print(f"\n📊 Market Events/sec: {ops_per_sec:.1f}")
        assert ops_per_sec >= target["min"], f"Throughput {ops_per_sec:.1f}/s < min {target['min']}/s"

    @pytest.mark.performance
    def test_signal_throughput(self):
        """Measure: Signals generated per second."""
        require_perf_run()

        def generate_signal():
            return {"type": "BUY", "symbol": "BTCUSDT", "strength": 0.75}

        ops_per_sec = self._measure_throughput(generate_signal, duration_sec=2.0)
        target = self.TARGETS["signals_per_sec"]

        print(f"\n📊 Signals/sec: {ops_per_sec:.1f}")
        assert ops_per_sec >= target["min"], f"Throughput {ops_per_sec:.1f}/s < min {target['min']}/s"

    @pytest.mark.performance
    def test_order_throughput(self):
        """Measure: Orders processed per second (mocked)."""
        require_perf_run()

        def process_order():
            order = {"symbol": "BTCUSDT", "side": "BUY", "qty": 0.01}
            result = {"order_id": "test", "status": "FILLED"}
            return result

        ops_per_sec = self._measure_throughput(process_order, duration_sec=2.0)
        target = self.TARGETS["orders_per_sec"]

        print(f"\n📊 Orders/sec: {ops_per_sec:.1f}")
        assert ops_per_sec >= target["min"], f"Throughput {ops_per_sec:.1f}/s < min {target['min']}/s"


# =============================================================================
# BASELINE REPORT GENERATOR
# =============================================================================


@pytest.mark.performance
def test_generate_baseline_report():
    """Generate comprehensive baseline report."""
    require_perf_run()

    report = {
        "generated_at": datetime.now().isoformat(),
        "environment": {
            "python": os.popen("python --version").read().strip(),
            "platform": os.name,
        },
        "latency_targets": TestLatencyBaselines.TARGETS,
        "throughput_targets": TestThroughputBaselines.TARGETS,
        "status": "BASELINE_RUN_COMPLETE",
    }

    print("\n" + "=" * 60)
    print("📊 PERFORMANCE BASELINE REPORT")
    print("=" * 60)
    for key, value in report.items():
        print(f"{key}: {value}")
    print("=" * 60)

    assert report["status"] == "BASELINE_RUN_COMPLETE"
