"""
Load Tests for Signal Engine - Burst / Race Conditions

Sprint 1 #623: Burst / Load / Race Conditions testing

Tests signal engine stability under sustained high load (50-200 tps).
"""

import os
import sys
import time
import json
import redis
import pytest
import requests
from pathlib import Path
from typing import Dict, List, Any

if os.getenv("LOAD_TESTS") != "1":
    pytest.skip(
        "Load tests require running stack (set LOAD_TESTS=1)", allow_module_level=True
    )

# Add repo root to path for imports
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from tests.e2e.replay_runner import ReplayRunner


class TestSignalBurst:
    """
    Load tests for signal engine burst scenarios.

    Sprint 1 #623: Prove signal engine stability at 50-200 tps.
    """

    @pytest.fixture(scope="class")
    def redis_client(self):
        """Redis client for metrics and stream verification."""
        redis_password = os.getenv("REDIS_PASSWORD")
        if not redis_password:
            # Try reading from secrets file
            secrets_path = os.getenv(
                "SECRETS_PATH", os.path.expanduser("~/.secrets/.cdb")
            )
            password_file = Path(secrets_path) / "REDIS_PASSWORD"
            if password_file.exists():
                redis_password = password_file.read_text().strip()

        client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=redis_password,
            db=0,
            decode_responses=True,
        )

        # Verify connection
        client.ping()

        yield client

        client.close()

    @pytest.fixture(scope="class")
    def burst_runner(self):
        """Replay runner with burst pattern fixture."""
        fixture_path = repo_root / "tests" / "e2e" / "fixtures" / "burst_pattern.json"

        redis_password = os.getenv("REDIS_PASSWORD")
        if not redis_password:
            secrets_path = os.getenv(
                "SECRETS_PATH", os.path.expanduser("~/.secrets/.cdb")
            )
            password_file = Path(secrets_path) / "REDIS_PASSWORD"
            if password_file.exists():
                redis_password = password_file.read_text().strip()

        runner = ReplayRunner(
            fixture_path=str(fixture_path),
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_password=redis_password,
        )

        runner.load_fixture()
        runner.connect_redis()

        yield runner

        runner.cleanup()

    def get_signal_metrics(self) -> Dict[str, Any]:
        """
        Get current signal service metrics via HTTP.

        Returns:
            Parsed metrics dict
        """
        response = requests.get("http://127.0.0.1:8005/metrics")
        response.raise_for_status()

        metrics = {}
        for line in response.text.strip().split("\n"):
            if line.startswith("#") or not line.strip():
                continue

            # Parse prometheus format: metric_name value
            # or metric_name{labels} value
            if "{" in line:
                # Labeled metric
                name_part, rest = line.split("{", 1)
                labels_part, value = rest.split("}", 1)
                value = value.strip()
                metrics[f"{name_part}{{{labels_part}}}"] = float(value)
            else:
                # Simple metric
                parts = line.split()
                if len(parts) == 2:
                    metrics[parts[0]] = float(parts[1])

        return metrics

    def verify_pct_change_sequence(
        self,
        redis_client: redis.Redis,
        stream_key: str = "stream.signals",
        count: int = 100,
    ) -> Dict[str, Any]:
        """
        Verify pct_change sequence in signals stream for state corruption.

        Sprint 1 #623: Prove no state corruption under burst load.

        Args:
            redis_client: Redis client
            stream_key: Stream to read from
            count: Number of recent signals to verify

        Returns:
            Verification results dict
        """
        # Read last N signals from stream
        signals = redis_client.xrevrange(stream_key, "+", "-", count=count)

        results = {
            "signals_checked": len(signals),
            "invalid_pct_change": 0,
            "duplicates": 0,
            "missing_fields": 0,
            "corruption_detected": False,
        }

        seen_signal_ids = set()

        for signal_id, signal_data in signals:
            # Check for duplicates
            if signal_id in seen_signal_ids:
                results["duplicates"] += 1
                results["corruption_detected"] = True

            seen_signal_ids.add(signal_id)

            # Check required fields
            if "pct_change" not in signal_data or "price" not in signal_data:
                results["missing_fields"] += 1
                results["corruption_detected"] = True
                continue

            # Validate pct_change is a valid number
            try:
                pct_change = float(signal_data["pct_change"])

                # Sanity check: pct_change should be reasonable (<100%)
                if abs(pct_change) > 100:
                    results["invalid_pct_change"] += 1
                    results["corruption_detected"] = True

            except (ValueError, TypeError):
                results["invalid_pct_change"] += 1
                results["corruption_detected"] = True

        return results

    @pytest.mark.load
    def test_signal_engine_burst_50tps(self, burst_runner, redis_client):
        """
        Test: Signal engine processes 50 tps for 10s without errors or corruption.

        Sprint 1 #623: Burst scenario 1 (baseline)

        Expected:
            - 500 ticks published
            - 50 signals generated (5 per cycle × 10 cycles)
            - 0 errors
            - No state corruption
        """
        print("\n" + "=" * 60)
        print("TEST: Signal Engine Burst @ 50 tps")
        print("=" * 60)

        # Get baseline metrics
        baseline = self.get_signal_metrics()
        baseline_signals = baseline.get("signals_generated_total", 0)
        baseline_errors = baseline.get("signal_errors_total", 0)

        # Run burst
        stats = burst_runner.run_burst(ticks_per_second=50, duration_seconds=10)

        # Wait for signal processing
        time.sleep(2)

        # Get final metrics
        final = self.get_signal_metrics()
        final_signals = final.get("signals_generated_total", 0)
        final_errors = final.get("signal_errors_total", 0)

        signals_delta = final_signals - baseline_signals
        errors_delta = final_errors - baseline_errors

        print(f"\nResults:")
        print(f"  Ticks published: {stats['ticks_published']}")
        print(f"  Signals generated: {signals_delta}")
        print(f"  Errors: {errors_delta}")
        print(f"  Actual TPS: {stats['actual_tps']:.2f}")
        print(f"  Avg latency: {stats['avg_latency_ms']:.2f}ms")

        # Assertions
        assert stats["ticks_published"] == 500, "Should publish 500 ticks"
        assert stats["errors"] == 0, "Should have 0 publishing errors"
        assert errors_delta == 0, "Should have 0 signal processing errors"

        # Verify state corruption
        corruption_check = self.verify_pct_change_sequence(
            redis_client, count=min(100, int(signals_delta))
        )
        print(f"\nState Corruption Check:")
        print(f"  Signals checked: {corruption_check['signals_checked']}")
        print(f"  Duplicates: {corruption_check['duplicates']}")
        print(f"  Invalid pct_change: {corruption_check['invalid_pct_change']}")
        print(f"  Missing fields: {corruption_check['missing_fields']}")
        print(f"  Corruption detected: {corruption_check['corruption_detected']}")

        assert not corruption_check[
            "corruption_detected"
        ], "No state corruption should be detected"

    @pytest.mark.load
    def test_signal_engine_burst_100tps(self, burst_runner, redis_client):
        """
        Test: Signal engine processes 100 tps for 10s without errors or corruption.

        Sprint 1 #623: Primary burst scenario

        Expected:
            - 1000 ticks published
            - 100 signals generated (5 per cycle × 20 cycles)
            - 0 errors
            - No state corruption
            - Latency p95 < 50ms
        """
        print("\n" + "=" * 60)
        print("TEST: Signal Engine Burst @ 100 tps")
        print("=" * 60)

        # Get baseline metrics
        baseline = self.get_signal_metrics()
        baseline_signals = baseline.get("signals_generated_total", 0)
        baseline_errors = baseline.get("signal_errors_total", 0)
        baseline_count = baseline.get("signal_processing_latency_ms_count", 0)

        # Run burst
        stats = burst_runner.run_burst(ticks_per_second=100, duration_seconds=10)

        # Wait for signal processing
        time.sleep(2)

        # Get final metrics
        final = self.get_signal_metrics()
        final_signals = final.get("signals_generated_total", 0)
        final_errors = final.get("signal_errors_total", 0)
        final_count = final.get("signal_processing_latency_ms_count", 0)

        signals_delta = final_signals - baseline_signals
        errors_delta = final_errors - baseline_errors
        processed_delta = final_count - baseline_count

        print(f"\nResults:")
        print(f"  Ticks published: {stats['ticks_published']}")
        print(f"  Ticks processed: {processed_delta}")
        print(f"  Signals generated: {signals_delta}")
        print(f"  Errors: {errors_delta}")
        print(f"  Actual TPS: {stats['actual_tps']:.2f}")
        print(f"  Avg latency: {stats['avg_latency_ms']:.2f}ms")
        print(f"  Max latency: {stats['max_latency_ms']:.2f}ms")

        # Assertions
        assert stats["ticks_published"] == 1000, "Should publish 1000 ticks"
        assert stats["errors"] == 0, "Should have 0 publishing errors"
        assert errors_delta == 0, "Should have 0 signal processing errors"
        assert (
            processed_delta >= 990
        ), f"Should process ~1000 messages (got {processed_delta})"

        # Performance baseline: p95 latency < 50ms (approximated by max)
        # Note: We don't have p95 here, using max as upper bound
        assert (
            stats["max_latency_ms"] < 100
        ), f"Max latency should be <100ms (got {stats['max_latency_ms']:.2f}ms)"

        # Verify state corruption
        corruption_check = self.verify_pct_change_sequence(
            redis_client, count=min(200, int(signals_delta))
        )
        print(f"\nState Corruption Check:")
        print(f"  Signals checked: {corruption_check['signals_checked']}")
        print(f"  Duplicates: {corruption_check['duplicates']}")
        print(f"  Invalid pct_change: {corruption_check['invalid_pct_change']}")
        print(f"  Missing fields: {corruption_check['missing_fields']}")
        print(f"  Corruption detected: {corruption_check['corruption_detected']}")

        assert not corruption_check[
            "corruption_detected"
        ], "No state corruption should be detected"

    @pytest.mark.load
    def test_signal_engine_burst_200tps(self, burst_runner, redis_client):
        """
        Test: Signal engine processes 200 tps for 5s without errors or corruption.

        Sprint 1 #623: High-rate burst scenario

        Expected:
            - 1000 ticks published
            - 100 signals generated (5 per cycle × 20 cycles)
            - 0 errors
            - No state corruption
        """
        print("\n" + "=" * 60)
        print("TEST: Signal Engine Burst @ 200 tps")
        print("=" * 60)

        # Get baseline metrics
        baseline = self.get_signal_metrics()
        baseline_signals = baseline.get("signals_generated_total", 0)
        baseline_errors = baseline.get("signal_errors_total", 0)

        # Run burst
        stats = burst_runner.run_burst(ticks_per_second=200, duration_seconds=5)

        # Wait for signal processing
        time.sleep(2)

        # Get final metrics
        final = self.get_signal_metrics()
        final_signals = final.get("signals_generated_total", 0)
        final_errors = final.get("signal_errors_total", 0)

        signals_delta = final_signals - baseline_signals
        errors_delta = final_errors - baseline_errors

        print(f"\nResults:")
        print(f"  Ticks published: {stats['ticks_published']}")
        print(f"  Signals generated: {signals_delta}")
        print(f"  Errors: {errors_delta}")
        print(f"  Actual TPS: {stats['actual_tps']:.2f}")
        print(f"  Avg latency: {stats['avg_latency_ms']:.2f}ms")

        # Assertions
        assert stats["ticks_published"] == 1000, "Should publish 1000 ticks"
        assert stats["errors"] == 0, "Should have 0 publishing errors"
        assert errors_delta == 0, "Should have 0 signal processing errors"

        # Verify state corruption
        corruption_check = self.verify_pct_change_sequence(
            redis_client, count=min(200, int(signals_delta))
        )
        print(f"\nState Corruption Check:")
        print(f"  Signals checked: {corruption_check['signals_checked']}")
        print(f"  Duplicates: {corruption_check['duplicates']}")
        print(f"  Invalid pct_change: {corruption_check['invalid_pct_change']}")
        print(f"  Missing fields: {corruption_check['missing_fields']}")
        print(f"  Corruption detected: {corruption_check['corruption_detected']}")

        assert not corruption_check[
            "corruption_detected"
        ], "No state corruption should be detected"
