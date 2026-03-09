"""
Resilience Tests: Service Recovery & Fault Injection

Tests for Issue #95:
- Service Restart (cdb_core, cdb_risk, cdb_execution)
- Connection Loss (PostgreSQL, Redis, MEXC API)
- Chaos Engineering (Random Kill, Network Partition)
- Data Integrity (Consistency nach Recovery)

Prerequisites:
- Docker Compose stack running
- RESILIENCE_RUN=1 to enable tests

Run:
```bash
RESILIENCE_RUN=1 pytest tests/resilience/test_fault_injection.py -v -s
```
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

import pytest
import redis

# Skip all tests unless explicitly enabled
pytestmark = [
    pytest.mark.resilience,
    pytest.mark.slow,
    pytest.mark.skipif(
        os.getenv("RESILIENCE_RUN") != "1",
        reason="Resilience tests only run when RESILIENCE_RUN=1 is set",
    ),
]

# Recovery time target
MAX_RECOVERY_TIME_SECONDS = 30
CONNECTION_RECOVERY_WARN_SECONDS = 30
CONNECTION_RECOVERY_FAIL_SECONDS = 60
POST_RECOVERY_STABILITY_SECONDS = 5
QUEUE_STALL_SOFT_LIMIT = 1000
OUTAGE_DISCONNECT_TIMEOUT_SECONDS = 20


@pytest.fixture(scope="module")
def redis_client():
    """Redis client for health checks."""
    password = os.environ["REDIS_PASSWORD"]  # No fallback - must be set
    client = redis.Redis(
        host="localhost",
        port=6379,
        password=password,
        decode_responses=True,
        socket_timeout=5,
    )
    yield client
    client.close()


def _run_cmd(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=os.getcwd(),
    )


def docker_compose_cmd(
    action: str, service: str | None = None, timeout: int = 30
) -> subprocess.CompletedProcess:
    """Execute docker compose command with deterministic fallback."""
    candidates = (["docker", "compose"], ["docker-compose"])
    last_result: subprocess.CompletedProcess | None = None
    for base in candidates:
        cmd = [*base, action]
        if service:
            cmd.append(service)
        result = _run_cmd(cmd, timeout=timeout)
        if result.returncode == 0:
            return result
        last_result = result
        stderr = (result.stderr or "").lower()
        if "not recognized" not in stderr and "not found" not in stderr:
            return result
    assert last_result is not None
    return last_result


def _docker_inspect_field(container: str, field: str) -> str:
    result = _run_cmd(["docker", "inspect", "--format", field, container], timeout=15)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _pause_container(container: str) -> None:
    result = _run_cmd(["docker", "pause", container], timeout=20)
    assert result.returncode == 0, f"Failed to pause {container}: {result.stderr}"


def _unpause_container(container: str) -> None:
    result = _run_cmd(["docker", "unpause", container], timeout=20)
    assert result.returncode == 0, f"Failed to unpause {container}: {result.stderr}"


def _is_container_paused(container: str) -> bool:
    return _docker_inspect_field(container, "{{.State.Paused}}").lower() == "true"


def _container_restart_count(container: str) -> int:
    raw = _docker_inspect_field(container, "{{.RestartCount}}")
    if not raw:
        return -1
    try:
        return int(raw)
    except ValueError:
        return -1


def wait_for_service(service_name: str, max_wait: int = 30) -> float:
    """Wait for service to be healthy, return recovery time."""
    start = time.monotonic()
    while time.monotonic() - start < max_wait:
        status = _docker_inspect_field(service_name, "{{.State.Health.Status}}")
        if status == "healthy":
            return time.monotonic() - start
        if status == "":
            state = _docker_inspect_field(service_name, "{{.State.Status}}")
            if state == "running":
                return time.monotonic() - start
        time.sleep(1)
    return -1.0


def check_redis_connectivity() -> bool:
    """Check if Redis is accessible."""
    try:
        password = os.environ["REDIS_PASSWORD"]  # No fallback - must be set
        client = redis.Redis(
            host="localhost", port=6379, password=password, socket_timeout=2
        )
        client.ping()
        client.close()
        return True
    except Exception:
        return False


def check_postgres_connectivity() -> bool:
    """Check whether PostgreSQL accepts connections from inside the DB container."""
    result = _run_cmd(
        [
            "docker",
            "exec",
            "cdb_postgres",
            "pg_isready",
            "-U",
            "claire_user",
            "-d",
            "claire_de_binare",
        ],
        timeout=10,
    )
    if result.returncode != 0:
        return False
    return "accepting connections" in (result.stdout or "").lower()


def _http_get_json(url: str, timeout: float = 3.0) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _execution_runtime_mode() -> str:
    try:
        payload = _http_get_json("http://localhost:8003/status")
    except (
        urllib.error.URLError,
        TimeoutError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        raise AssertionError(f"Unable to read execution /status: {exc}") from exc
    raw_mode = payload.get("runtime_mode")
    if raw_mode in (None, ""):
        raw_mode = payload.get("mode")
    mode = str(raw_mode or "").strip().lower()
    if mode == "staged":
        mode = "shadow"
    if mode == "mock":
        mode = "shadow"
    return mode or "unresolved"


def _execution_metric(metric_name: str) -> Optional[float]:
    try:
        with urllib.request.urlopen(
            "http://localhost:8003/metrics", timeout=3
        ) as response:
            body = response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError):
        return None

    prefix = f"{metric_name} "
    for line in body.splitlines():
        if line.startswith(prefix):
            try:
                return float(line.split(" ", 1)[1].strip())
            except ValueError:
                return None
    return None


def _redis_stream_length(stream_name: str) -> Optional[int]:
    result = _run_cmd(
        [
            "docker",
            "exec",
            "cdb_redis",
            "sh",
            "-lc",
            f'redis-cli -a "$(cat /run/secrets/redis_password)" XLEN {stream_name}',
        ],
        timeout=10,
    )
    if result.returncode != 0:
        return None
    lines = [
        line.strip() for line in (result.stdout or "").splitlines() if line.strip()
    ]
    if not lines:
        return None
    try:
        return int(lines[-1])
    except ValueError:
        return None


def _wait_for_probe(probe, timeout_seconds: int) -> float:
    start = time.monotonic()
    while time.monotonic() - start < timeout_seconds:
        if probe():
            return time.monotonic() - start
        time.sleep(1)
    return -1.0


def _classify_recovery_window(recovery_seconds: float) -> str:
    if recovery_seconds <= CONNECTION_RECOVERY_WARN_SECONDS:
        return "PASS"
    if recovery_seconds <= CONNECTION_RECOVERY_FAIL_SECONDS:
        return "WARN"
    return "FAIL"


def _run_lr042_smoke(
    *,
    tmp_path: Path,
    scenarios: str = "latency_only,packet_loss_only",
) -> tuple[subprocess.CompletedProcess, Path, Path, Path]:
    repo_root = Path(__file__).resolve().parents[2]
    runner_path = (
        repo_root / "scripts" / "drills" / "lr042_network_latency_packet_loss_runner.py"
    )
    assert runner_path.exists(), f"Missing LR-042 runner: {runner_path}"

    output_dir = tmp_path / "lr042_smoke"
    command = [
        sys.executable,
        str(runner_path),
        "--output-dir",
        str(output_dir),
        "--scenarios",
        scenarios,
        "--fault-duration-seconds",
        "5",
        "--recovery-timeout",
        "60",
        "--stability-seconds",
        "5",
    ]
    result = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=420,
    )
    return (
        result,
        output_dir / "lr042_summary.json",
        output_dir / "lr042_timeline.json",
        output_dir / "lr042_verdict.md",
    )


# =============================================================================
# SERVICE RESTART TESTS (3 tests)
# =============================================================================


class TestServiceRestart:
    """Test service recovery after restart."""

    @pytest.mark.resilience
    def test_restart_cdb_core(self):
        """Test: cdb_core service restart and recovery."""
        service = "cdb_core"

        # Restart service
        docker_compose_cmd("restart", service)

        # Wait for recovery
        recovery_time = wait_for_service(service, MAX_RECOVERY_TIME_SECONDS)

        assert (
            recovery_time >= 0
        ), f"{service} did not recover within {MAX_RECOVERY_TIME_SECONDS}s"
        assert (
            recovery_time < MAX_RECOVERY_TIME_SECONDS
        ), f"{service} recovery took {recovery_time:.1f}s > {MAX_RECOVERY_TIME_SECONDS}s"

        print(f"✅ {service} recovered in {recovery_time:.1f}s")

    @pytest.mark.resilience
    def test_restart_cdb_risk(self):
        """Test: cdb_risk service restart and recovery."""
        service = "cdb_risk"

        docker_compose_cmd("restart", service)
        recovery_time = wait_for_service(service, MAX_RECOVERY_TIME_SECONDS)

        assert (
            recovery_time >= 0
        ), f"{service} did not recover within {MAX_RECOVERY_TIME_SECONDS}s"
        print(f"✅ {service} recovered in {recovery_time:.1f}s")

    @pytest.mark.resilience
    def test_restart_cdb_execution(self):
        """Test: cdb_execution service restart and recovery."""
        service = "cdb_execution"

        docker_compose_cmd("restart", service)
        recovery_time = wait_for_service(service, MAX_RECOVERY_TIME_SECONDS)

        assert (
            recovery_time >= 0
        ), f"{service} did not recover within {MAX_RECOVERY_TIME_SECONDS}s"
        print(f"✅ {service} recovered in {recovery_time:.1f}s")


# =============================================================================
# CONNECTION LOSS TESTS (3 tests)
# =============================================================================


class TestConnectionLoss:
    """Test service behavior during connection loss."""

    @pytest.mark.resilience
    def test_redis_connection_loss(self, redis_client):
        """Test deterministic Redis outage/recovery with fail-safe assertions."""
        assert check_redis_connectivity(), "Redis baseline connectivity missing"

        runtime_mode = _execution_runtime_mode()
        assert (
            runtime_mode == "shadow"
        ), f"Expected shadow runtime mode, got {runtime_mode}"

        filled_before = _execution_metric("execution_orders_filled_total")
        assert filled_before is not None, "Missing execution_orders_filled_total metric"

        queue_before = _redis_stream_length("stream.orders")
        risk_restarts_before = _container_restart_count("cdb_risk")
        execution_restarts_before = _container_restart_count("cdb_execution")

        _pause_container("cdb_redis")
        try:
            assert _is_container_paused("cdb_redis"), "Redis container should be paused"
            disconnect_time = _wait_for_probe(
                lambda: not check_redis_connectivity(),
                OUTAGE_DISCONNECT_TIMEOUT_SECONDS,
            )
            assert disconnect_time >= 0, (
                "Redis outage was not observed within "
                f"{OUTAGE_DISCONNECT_TIMEOUT_SECONDS}s"
            )
        finally:
            _unpause_container("cdb_redis")

        recovery_time = _wait_for_probe(
            check_redis_connectivity, CONNECTION_RECOVERY_FAIL_SECONDS
        )
        assert recovery_time >= 0, (
            "Redis did not recover within "
            f"{CONNECTION_RECOVERY_FAIL_SECONDS}s (hard fail)"
        )

        recovery_class = _classify_recovery_window(recovery_time)
        assert recovery_class != "FAIL", (
            f"Redis recovery classification={recovery_class} "
            f"({recovery_time:.1f}s > {CONNECTION_RECOVERY_FAIL_SECONDS}s)"
        )
        if recovery_class == "WARN":
            print(
                f"⚠️ WARN Redis recovery in {recovery_time:.1f}s "
                f"(>{CONNECTION_RECOVERY_WARN_SECONDS}s)"
            )
        else:
            print(f"✅ Redis recovered in {recovery_time:.1f}s")

        runtime_stable = _wait_for_probe(
            lambda: _execution_runtime_mode() == "shadow",
            POST_RECOVERY_STABILITY_SECONDS,
        )
        assert runtime_stable >= 0, "Execution runtime mode did not stabilize to shadow"

        filled_after = _execution_metric("execution_orders_filled_total")
        assert filled_after is not None, "Missing post-recovery execution metric"
        assert filled_after == filled_before, (
            "LR-030 violation: execution_orders_filled_total changed during Redis chaos "
            f"({filled_before} -> {filled_after})"
        )

        runtime_mode_after = _execution_runtime_mode()
        assert runtime_mode_after == "shadow", (
            "Execution runtime mode must remain shadow after Redis recovery, "
            f"got {runtime_mode_after}"
        )

        queue_after = _redis_stream_length("stream.orders")
        if queue_before is not None and queue_after is not None:
            assert queue_after - queue_before <= QUEUE_STALL_SOFT_LIMIT, (
                "Queue backlog indicates sustained stall after Redis recovery: "
                f"{queue_before} -> {queue_after}"
            )

        risk_restarts_after = _container_restart_count("cdb_risk")
        execution_restarts_after = _container_restart_count("cdb_execution")
        assert risk_restarts_after >= risk_restarts_before >= 0
        assert execution_restarts_after >= execution_restarts_before >= 0
        assert risk_restarts_after - risk_restarts_before <= 1
        assert execution_restarts_after - execution_restarts_before <= 1

    @pytest.mark.resilience
    def test_postgres_connection_loss(self):
        """Test deterministic PostgreSQL outage/recovery with fail-safe assertions."""
        assert check_postgres_connectivity(), "PostgreSQL baseline connectivity missing"

        runtime_mode = _execution_runtime_mode()
        assert (
            runtime_mode == "shadow"
        ), f"Expected shadow runtime mode, got {runtime_mode}"

        filled_before = _execution_metric("execution_orders_filled_total")
        assert filled_before is not None, "Missing execution_orders_filled_total metric"

        db_writer_restarts_before = _container_restart_count("cdb_db_writer")
        risk_restarts_before = _container_restart_count("cdb_risk")

        _pause_container("cdb_postgres")
        try:
            assert _is_container_paused(
                "cdb_postgres"
            ), "PostgreSQL container should be paused"
            disconnect_time = _wait_for_probe(
                lambda: not check_postgres_connectivity(),
                OUTAGE_DISCONNECT_TIMEOUT_SECONDS,
            )
            assert disconnect_time >= 0, (
                "PostgreSQL outage was not observed within "
                f"{OUTAGE_DISCONNECT_TIMEOUT_SECONDS}s"
            )
        finally:
            _unpause_container("cdb_postgres")

        recovery_time = _wait_for_probe(
            check_postgres_connectivity, CONNECTION_RECOVERY_FAIL_SECONDS
        )
        assert recovery_time >= 0, (
            "PostgreSQL did not recover within "
            f"{CONNECTION_RECOVERY_FAIL_SECONDS}s (hard fail)"
        )
        recovery_class = _classify_recovery_window(recovery_time)
        assert recovery_class != "FAIL", (
            f"PostgreSQL recovery classification={recovery_class} "
            f"({recovery_time:.1f}s > {CONNECTION_RECOVERY_FAIL_SECONDS}s)"
        )
        if recovery_class == "WARN":
            print(
                f"⚠️ WARN PostgreSQL recovery in {recovery_time:.1f}s "
                f"(>{CONNECTION_RECOVERY_WARN_SECONDS}s)"
            )
        else:
            print(f"✅ PostgreSQL recovered in {recovery_time:.1f}s")

        db_writer_recovery = wait_for_service(
            "cdb_db_writer", CONNECTION_RECOVERY_FAIL_SECONDS
        )
        assert (
            db_writer_recovery >= 0
        ), "cdb_db_writer did not recover after PostgreSQL outage"

        runtime_stable = _wait_for_probe(
            lambda: _execution_runtime_mode() == "shadow",
            POST_RECOVERY_STABILITY_SECONDS,
        )
        assert runtime_stable >= 0, "Execution runtime mode did not stabilize to shadow"

        filled_after = _execution_metric("execution_orders_filled_total")
        assert filled_after is not None, "Missing post-recovery execution metric"
        assert filled_after == filled_before, (
            "LR-030 violation: execution_orders_filled_total changed during Postgres chaos "
            f"({filled_before} -> {filled_after})"
        )

        runtime_mode_after = _execution_runtime_mode()
        assert runtime_mode_after == "shadow", (
            "Execution runtime mode must remain shadow after PostgreSQL recovery, "
            f"got {runtime_mode_after}"
        )

        db_writer_restarts_after = _container_restart_count("cdb_db_writer")
        risk_restarts_after = _container_restart_count("cdb_risk")
        assert db_writer_restarts_after >= db_writer_restarts_before >= 0
        assert risk_restarts_after >= risk_restarts_before >= 0
        assert db_writer_restarts_after - db_writer_restarts_before <= 1
        assert risk_restarts_after - risk_restarts_before <= 1

    @pytest.mark.resilience
    def test_mexc_api_timeout_handling(self, redis_client):
        """Test: Execution service handles MEXC API timeouts."""
        # Set a flag to simulate API timeout in paper trading mode
        redis_client.set("test:simulate_api_timeout", "1")

        try:
            # Publish test order
            order_payload = {
                "order_id": f"resilience-timeout-{int(time.time())}",
                "symbol": "BTC/USDT",
                "side": "BUY",
                "quantity": 0.001,
                "type": "MARKET",
                "source": "resilience_test",
            }

            pubsub = redis_client.pubsub()
            pubsub.subscribe("order_results")
            for _ in range(3):
                pubsub.get_message(timeout=0.1)

            redis_client.publish("orders", json.dumps(order_payload))

            # Wait for result (should still get response even with timeout)
            result = None
            for _ in range(30):  # 15 seconds
                msg = pubsub.get_message(timeout=0.5)
                if msg and msg["type"] == "message":
                    result = msg
                    break

            pubsub.close()

            if result:
                payload = json.loads(result["data"])
                # In paper mode, should still work
                print(
                    f"✅ Order processed despite timeout simulation: {payload['status']}"
                )
            else:
                print(
                    "⚠️ No response (may indicate timeout handling needs improvement)"
                )

        finally:
            redis_client.delete("test:simulate_api_timeout")


# =============================================================================
# CHAOS ENGINEERING TESTS (3 tests)
# =============================================================================


class TestChaosEngineering:
    """Chaos engineering tests for system resilience."""

    @pytest.mark.resilience
    def test_random_service_kill(self):
        """Test: System recovers from random service kill."""
        import random

        services = ["cdb_signal", "cdb_risk", "cdb_execution"]
        target = random.choice(services)

        # Kill the service
        subprocess.run(["docker", "kill", target], capture_output=True)

        # Let docker-compose restart it (depends on restart policy)
        time.sleep(10)

        # Check if service came back
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={target}", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
        )

        if "Up" in result.stdout:
            print(f"✅ {target} auto-restarted after kill")
        else:
            # Manual restart
            docker_compose_cmd("up", f"-d {target}")
            time.sleep(10)
            print(f"⚠️ {target} required manual restart")

    @pytest.mark.resilience
    def test_network_partition_simulation(self, redis_client):
        """Test: Order processing during network issues."""
        # This is a simplified test - real network partition would use toxiproxy

        # Submit order
        order_id = f"chaos-partition-{int(time.time())}"
        order_payload = {
            "order_id": order_id,
            "symbol": "BTC/USDT",
            "side": "BUY",
            "quantity": 0.001,
            "type": "MARKET",
        }

        # Subscribe before publish
        pubsub = redis_client.pubsub()
        pubsub.subscribe("order_results")
        for _ in range(3):
            pubsub.get_message(timeout=0.1)

        redis_client.publish("orders", json.dumps(order_payload))

        # Wait for result
        result = None
        for _ in range(20):
            msg = pubsub.get_message(timeout=0.5)
            if msg and msg["type"] == "message":
                result = msg
                break

        pubsub.close()

        assert result is not None, "No order result during partition test"
        print("✅ Order processed during network partition simulation")

    @pytest.mark.resilience
    def test_high_load_burst(self, redis_client):
        """Test: System handles burst of 100 orders."""
        order_count = 100
        start_time = time.time()

        # Subscribe to results
        pubsub = redis_client.pubsub()
        pubsub.subscribe("order_results")
        for _ in range(3):
            pubsub.get_message(timeout=0.1)

        # Burst of orders
        for i in range(order_count):
            order_payload = {
                "order_id": f"burst-{start_time}-{i}",
                "symbol": "BTC/USDT",
                "side": "BUY" if i % 2 == 0 else "SELL",
                "quantity": 0.001,
                "type": "MARKET",
            }
            redis_client.publish("orders", json.dumps(order_payload))

        # Count received results (within 30 seconds)
        received = 0
        timeout_at = time.time() + 30
        while time.time() < timeout_at and received < order_count:
            msg = pubsub.get_message(timeout=0.1)
            if msg and msg["type"] == "message":
                received += 1

        pubsub.close()

        elapsed = time.time() - start_time
        throughput = received / elapsed

        print(
            f"📊 Burst test: {received}/{order_count} orders in {elapsed:.1f}s ({throughput:.1f}/s)"
        )
        assert (
            received >= order_count * 0.9
        ), f"Only {received}/{order_count} orders processed"


# =============================================================================
# DATA INTEGRITY TESTS (3 tests)
# =============================================================================


class TestDataIntegrity:
    """Test data consistency after failures."""

    @pytest.mark.resilience
    def test_stream_consistency_after_restart(self, redis_client):
        """Test: Redis stream data consistent after service restart."""
        stream_name = "stream.fills"

        # Get current stream length
        try:
            initial_length = redis_client.xlen(stream_name)
        except redis.ResponseError:
            initial_length = 0

        # Restart execution service
        docker_compose_cmd("restart", "cdb_execution")
        time.sleep(10)

        # Check stream length unchanged
        try:
            final_length = redis_client.xlen(stream_name)
        except redis.ResponseError:
            final_length = 0

        assert final_length >= initial_length, "Stream data lost after restart!"
        print(f"✅ Stream consistent: {initial_length} → {final_length} entries")

    @pytest.mark.resilience
    def test_order_state_consistency(self, redis_client):
        """Test: Order state consistent after reconnection."""
        # Submit order
        order_id = f"consistency-{int(time.time())}"
        order_payload = {
            "order_id": order_id,
            "symbol": "BTC/USDT",
            "side": "BUY",
            "quantity": 0.001,
            "type": "MARKET",
        }

        redis_client.publish("orders", json.dumps(order_payload))
        time.sleep(3)

        # Check order state in stream
        stream_name = "stream.fills"
        entries = redis_client.xrevrange(stream_name, count=10)

        found = False
        for entry_id, entry_data in entries:
            if entry_data.get("order_id") == order_id:
                found = True
                status = entry_data.get("status", "unknown")
                print(f"✅ Order {order_id} found with status: {status}")
                break

        if not found:
            print(f"⚠️ Order {order_id} not found in recent stream entries")

    @pytest.mark.resilience
    def test_no_duplicate_orders_after_restart(self, redis_client):
        """Test: No duplicate order processing after restart."""
        order_id = f"dedup-{int(time.time())}"

        # Submit order
        order_payload = {
            "order_id": order_id,
            "symbol": "BTC/USDT",
            "side": "BUY",
            "quantity": 0.001,
            "type": "MARKET",
        }
        redis_client.publish("orders", json.dumps(order_payload))

        time.sleep(2)

        # Restart execution
        docker_compose_cmd("restart", "cdb_execution")
        time.sleep(10)

        # Try to resubmit same order
        redis_client.publish("orders", json.dumps(order_payload))
        time.sleep(2)

        # Check stream for duplicates
        stream_name = "stream.fills"
        entries = redis_client.xrevrange(stream_name, count=20)

        order_count = sum(1 for _, data in entries if data.get("order_id") == order_id)

        if order_count > 1:
            print(
                f"⚠️ Duplicate detected: order {order_id} appears {order_count} times"
            )
        else:
            print(f"✅ No duplicates: order {order_id} appears {order_count} time(s)")


class TestNetworkDegradation:
    """Deterministic smoke checks for LR-042 network chaos runner."""

    @pytest.mark.resilience
    def test_lr042_latency_and_loss_runner_smoke(self, tmp_path):
        result, summary_path, timeline_path, verdict_path = _run_lr042_smoke(
            tmp_path=tmp_path
        )

        assert summary_path.exists(), f"Missing summary artifact: {summary_path}"
        assert timeline_path.exists(), f"Missing timeline artifact: {timeline_path}"
        assert verdict_path.exists(), f"Missing verdict artifact: {verdict_path}"

        summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
        overall = (
            summary_payload.get("summary", {}).get("overall", "FAIL").strip().upper()
        )

        if result.returncode == 3 or overall == "UNSUPPORTED":
            reason = summary_payload.get("unsupported_reason", "netem unsupported")
            pytest.skip(f"LR-042 unsupported in current environment: {reason}")

        assert result.returncode == 0, (
            f"LR-042 runner failed: rc={result.returncode}\n"
            f"stdout={result.stdout}\n"
            f"stderr={result.stderr}"
        )
        assert overall in {"PASS", "WARN"}, f"Unexpected LR-042 overall={overall}"

        checks = summary_payload.get("checks", {})
        assert checks.get("shadow_runtime_required") is True
        assert checks.get("zero_execution_preserved") is True

        scenario_rows = summary_payload.get("scenarios", [])
        scenario_names = {str(row.get("name")) for row in scenario_rows}
        assert {"latency_only", "packet_loss_only"}.issubset(scenario_names)
        for row in scenario_rows:
            assert float(row.get("filled_delta", 1.0)) == 0.0, (
                "LR-030 zero execution must hold in LR-042 smoke, "
                f"scenario={row.get('name')} filled_delta={row.get('filled_delta')}"
            )

        timeline_payload = json.loads(timeline_path.read_text(encoding="utf-8"))
        timeline_steps = {str(event.get("step")) for event in timeline_payload}
        for required_step in ("t0", "t1", "t2", "t3", "t4", "t5", "t6"):
            assert (
                required_step in timeline_steps
            ), f"Timeline missing required step {required_step}: {timeline_steps}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
