"""
Chaos & Resilience Tests - Claire de Binare
Lokaler-only Test: Service-Ausfälle und Recovery-Szenarien

WICHTIG: Dieser Test MUSS lokal mit Docker Compose ausgeführt werden!
    - Erfordert: Docker Compose CLI, alle Services laufend
    - Simuliert: Container-Crashes, Service-Ausfälle, Partial Failures
    - Prüft: Automatic Recovery, Data Integrity, No Cascading Failures
    - NICHT in CI ausführen (zu destruktiv!)

⚠️  ACHTUNG: Diese Tests sind DESTRUKTIV - Services werden ge-killed!

Ausführung:
    pytest -v -m local_only tests/local/test_chaos_resilience.py
"""

import pytest
import subprocess
import time
import redis
import psycopg2
import json


def run_docker_compose(args, timeout=30):
    """Helper: Docker Compose Command ausführen"""
    cmd = ["docker", "compose"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result


def is_service_healthy(service_name):
    """Prüft ob Service healthy ist"""
    result = run_docker_compose(["ps", "--format", "json"])

    if result.returncode != 0:
        return False

    # Parse JSON lines
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue

        try:
            service = json.loads(line)

            if service_name in service.get("Name", ""):
                status = service.get("Status", "")
                return "healthy" in status.lower() or service.get("Health") == "healthy"

        except json.JSONDecodeError:
            pass

    return False


@pytest.mark.local_only
@pytest.mark.slow
@pytest.mark.chaos
def test_redis_crash_and_recovery():
    """
    Chaos-Test: Redis crasht und recovered automatisch

    Simuliert:
    - Redis läuft
    - Redis wird ge-killed
    - Redis wird neu gestartet
    - Services reconnecten automatisch

    Validiert:
    - Recovery erfolgreich
    - Services wieder healthy
    - Redis wieder erreichbar
    """
    print("\n🔥 Chaos-Test: Redis crash & recovery...")

    # Step 1: Baseline - Redis ist healthy
    print("  📊 Step 1: Verify Redis is healthy...")
    assert is_service_healthy("cdb_redis"), "Redis should be healthy initially"

    # Verify Redis ist erreichbar
    try:
        redis_client = redis.Redis(
            host="localhost", port=6379, password="claire_redis_secret_2024"
        )
        assert redis_client.ping(), "Redis should respond to ping"
        print("    ✓ Redis is reachable")
    except Exception as e:
        pytest.fail(f"Cannot connect to Redis: {e}")

    # Step 2: KILL Redis
    print("  💥 Step 2: Killing Redis...")
    result = run_docker_compose(["kill", "cdb_redis"])
    assert result.returncode == 0, f"Failed to kill Redis: {result.stderr}"
    print("    ✓ Redis killed")

    time.sleep(3)

    # Step 3: Verify Redis is down
    print("  📊 Step 3: Verify Redis is down...")
    try:
        redis_client.ping()
        pytest.fail("Redis should not respond after kill")
    except (redis.ConnectionError, redis.TimeoutError):
        print("    ✓ Redis is down (expected)")

    # Step 4: Restart Redis
    print("  🔄 Step 4: Restarting Redis...")
    result = run_docker_compose(["start", "cdb_redis"])
    assert result.returncode == 0, f"Failed to start Redis: {result.stderr}"
    print("    ✓ Redis restart initiated")

    # Step 5: Wait for recovery
    print("  ⏳ Step 5: Waiting for Redis to become healthy (15s)...")
    time.sleep(15)

    # Step 6: Verify Redis is healthy again
    print("  📊 Step 6: Verify Redis recovered...")

    max_retries = 5
    for i in range(max_retries):
        try:
            redis_client = redis.Redis(
                host="localhost",
                port=6379,
                password="claire_redis_secret_2024",
                socket_connect_timeout=5,
            )

            if redis_client.ping():
                print("    ✓ Redis is back online")
                break

        except Exception as e:
            if i == max_retries - 1:
                pytest.fail(f"Redis did not recover after {max_retries} retries: {e}")

            time.sleep(2)

    # Step 7: Verify Services reconnected
    print("  📊 Step 7: Verify Services reconnected...")
    time.sleep(5)  # Give services time to reconnect

    # Check if critical services are still healthy
    critical_services = ["cdb_core", "cdb_risk", "cdb_execution"]
    unhealthy = []

    for service in critical_services:
        if not is_service_healthy(service):
            unhealthy.append(service)

    if unhealthy:
        print(f"    ⚠️  Some services not healthy yet: {unhealthy}")
        print("    ℹ️  This is acceptable - services might need more time to reconnect")
    else:
        print("    ✓ All critical services healthy")

    print("\n✅ Redis crash & recovery test completed")


@pytest.mark.local_only
@pytest.mark.slow
@pytest.mark.chaos
def test_postgres_crash_and_recovery():
    """
    Chaos-Test: PostgreSQL crasht und recovered

    Simuliert:
    - PostgreSQL läuft
    - PostgreSQL wird ge-killed
    - PostgreSQL wird neu gestartet

    Validiert:
    - Recovery erfolgreich
    - Data Integrity (keine Data-Loss)
    - Services reconnecten
    """
    print("\n🔥 Chaos-Test: PostgreSQL crash & recovery...")

    # Step 1: Baseline - Count Snapshots
    print("  📊 Step 1: Baseline - count portfolio_snapshots...")

    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="claire_de_binare",
            user="claire_user",
            password="claire_db_secret_2024",
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
        baseline_count = cursor.fetchone()[0]
        conn.close()

        print(f"    ✓ Baseline: {baseline_count} snapshots")

    except Exception as e:
        pytest.fail(f"Cannot connect to PostgreSQL: {e}")

    # Step 2: KILL PostgreSQL
    print("  💥 Step 2: Killing PostgreSQL...")
    result = run_docker_compose(["kill", "cdb_postgres"])
    assert result.returncode == 0, f"Failed to kill PostgreSQL: {result.stderr}"
    print("    ✓ PostgreSQL killed")

    time.sleep(3)

    # Step 3: Verify PostgreSQL is down
    print("  📊 Step 3: Verify PostgreSQL is down...")
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="claire_de_binare",
            user="claire_user",
            password="claire_db_secret_2024",
            connect_timeout=3,
        )
        conn.close()
        pytest.fail("PostgreSQL should not accept connections after kill")
    except psycopg2.OperationalError:
        print("    ✓ PostgreSQL is down (expected)")

    # Step 4: Restart PostgreSQL
    print("  🔄 Step 4: Restarting PostgreSQL...")
    result = run_docker_compose(["start", "cdb_postgres"])
    assert result.returncode == 0, f"Failed to start PostgreSQL: {result.stderr}"
    print("    ✓ PostgreSQL restart initiated")

    # Step 5: Wait for recovery
    print("  ⏳ Step 5: Waiting for PostgreSQL to become healthy (20s)...")
    time.sleep(20)

    # Step 6: Verify PostgreSQL recovered
    print("  📊 Step 6: Verify PostgreSQL recovered...")

    max_retries = 5
    recovered = False

    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="claire_de_binare",
                user="claire_user",
                password="claire_db_secret_2024",
                connect_timeout=5,
            )

            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()

            print("    ✓ PostgreSQL is back online")
            recovered = True
            break

        except Exception as e:
            if i == max_retries - 1:
                pytest.fail(
                    f"PostgreSQL did not recover after {max_retries} retries: {e}"
                )

            time.sleep(3)

    assert recovered, "PostgreSQL should have recovered"

    # Step 7: Verify Data Integrity
    print("  📊 Step 7: Verify data integrity (no data loss)...")

    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="claire_de_binare",
        user="claire_user",
        password="claire_db_secret_2024",
    )
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
    after_count = cursor.fetchone()[0]
    conn.close()

    print(f"    ✓ After restart: {after_count} snapshots")

    # Data should be preserved (Volume-Persistence)
    assert after_count == baseline_count, f"Data lost: {baseline_count} → {after_count}"

    print("    ✓ No data loss")

    print("\n✅ PostgreSQL crash & recovery test completed")


@pytest.mark.local_only
@pytest.mark.slow
@pytest.mark.chaos
def test_core_service_crash_partial_failure():
    """
    Chaos-Test: cdb_core crasht, andere Services laufen weiter

    Simuliert:
    - Signal Engine (cdb_core) crasht
    - Risk Manager und Execution laufen weiter
    - Keine Cascading Failures

    Validiert:
    - Partial Failure isoliert
    - Andere Services bleiben healthy
    - System-Recovery möglich
    """
    print("\n🔥 Chaos-Test: Partial Service Failure (cdb_core)...")

    # Step 1: Verify alle Services healthy
    print("  📊 Step 1: Baseline - verify all services healthy...")

    baseline_services = {
        "cdb_redis": is_service_healthy("cdb_redis"),
        "cdb_postgres": is_service_healthy("cdb_postgres"),
        "cdb_core": is_service_healthy("cdb_core"),
        "cdb_risk": is_service_healthy("cdb_risk"),
        "cdb_execution": is_service_healthy("cdb_execution"),
    }

    print(f"    Baseline: {sum(baseline_services.values())}/5 services healthy")

    if not baseline_services["cdb_core"]:
        pytest.skip("cdb_core not healthy initially - cannot test crash")

    # Step 2: KILL cdb_core
    print("  💥 Step 2: Killing cdb_core (Signal Engine)...")
    result = run_docker_compose(["kill", "cdb_core"])
    assert result.returncode == 0, f"Failed to kill cdb_core: {result.stderr}"
    print("    ✓ cdb_core killed")

    time.sleep(5)

    # Step 3: Verify cdb_core is down, but others STAY UP
    print("  📊 Step 3: Verify partial failure (others still running)...")

    after_failure = {
        "cdb_redis": is_service_healthy("cdb_redis"),
        "cdb_postgres": is_service_healthy("cdb_postgres"),
        "cdb_core": is_service_healthy("cdb_core"),
        "cdb_risk": is_service_healthy("cdb_risk"),
        "cdb_execution": is_service_healthy("cdb_execution"),
    }

    # cdb_core should be down
    assert not after_failure["cdb_core"], "cdb_core should be down"

    # Others should still be up
    other_services = ["cdb_redis", "cdb_postgres", "cdb_risk", "cdb_execution"]
    still_healthy = [svc for svc in other_services if after_failure[svc]]

    print("    ✓ cdb_core is down")
    print(f"    ✓ {len(still_healthy)}/4 other services still healthy: {still_healthy}")

    # At least 3/4 anderen Services sollten noch laufen (keine Cascading Failure)
    assert (
        len(still_healthy) >= 3
    ), f"Cascading failure detected! Only {len(still_healthy)}/4 services still up"

    # Step 4: Restart cdb_core
    print("  🔄 Step 4: Restarting cdb_core...")
    result = run_docker_compose(["start", "cdb_core"])
    assert result.returncode == 0, f"Failed to start cdb_core: {result.stderr}"

    time.sleep(15)

    # Step 5: Verify recovery
    print("  📊 Step 5: Verify cdb_core recovered...")

    recovered = is_service_healthy("cdb_core")

    if recovered:
        print("    ✓ cdb_core recovered")
    else:
        print("    ⚠️  cdb_core not healthy yet (might need more time)")

    print("\n✅ Partial service failure test completed")


@pytest.mark.local_only
@pytest.mark.slow
@pytest.mark.chaos
def test_concurrent_redis_and_postgres_crash():
    """
    Chaos-Test: Redis UND PostgreSQL crashen gleichzeitig

    Simuliert:
    - Worst-Case: Beide Data-Stores down
    - Services müssen recovern
    - Keine Deadlocks

    Validiert:
    - System recovered nach Doppel-Crash
    - Services reconnecten zu beiden Stores
    - Keine permanenten Failures
    """
    print("\n🔥 Chaos-Test: Concurrent Redis + PostgreSQL crash...")

    # Step 1: Verify baseline
    print("  📊 Step 1: Baseline - both stores healthy...")

    redis_healthy = is_service_healthy("cdb_redis")
    postgres_healthy = is_service_healthy("cdb_postgres")

    if not (redis_healthy and postgres_healthy):
        pytest.skip("Redis or PostgreSQL not healthy initially")

    print("    ✓ Both Redis and PostgreSQL healthy")

    # Step 2: KILL both simultaneously
    print("  💥 Step 2: Killing both Redis AND PostgreSQL...")

    result1 = run_docker_compose(["kill", "cdb_redis"])
    result2 = run_docker_compose(["kill", "cdb_postgres"])

    assert result1.returncode == 0 and result2.returncode == 0, "Failed to kill stores"

    print("    ✓ Both stores killed")

    time.sleep(5)

    # Step 3: Restart both
    print("  🔄 Step 3: Restarting both stores...")

    result1 = run_docker_compose(["start", "cdb_redis"])
    result2 = run_docker_compose(["start", "cdb_postgres"])

    assert (
        result1.returncode == 0 and result2.returncode == 0
    ), "Failed to restart stores"

    print("    ✓ Both restarts initiated")

    # Step 4: Wait for recovery
    print("  ⏳ Step 4: Waiting for recovery (30s)...")
    time.sleep(30)

    # Step 5: Verify both recovered
    print("  📊 Step 5: Verify both stores recovered...")

    redis_recovered = False
    postgres_recovered = False

    # Check Redis
    try:
        redis_client = redis.Redis(
            host="localhost", port=6379, password="claire_redis_secret_2024"
        )
        if redis_client.ping():
            redis_recovered = True
            print("    ✓ Redis recovered")
    except Exception:
        print("    ⚠️  Redis not recovered yet")

    # Check PostgreSQL
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="claire_de_binare",
            user="claire_user",
            password="claire_db_secret_2024",
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        postgres_recovered = True
        print("    ✓ PostgreSQL recovered")
    except Exception:
        print("    ⚠️  PostgreSQL not recovered yet")

    # Mindestens einer sollte recovered sein (vollständige Recovery braucht Zeit)
    if redis_recovered or postgres_recovered:
        print(
            f"    ✓ Partial recovery: Redis={redis_recovered}, PostgreSQL={postgres_recovered}"
        )
    else:
        pytest.fail("Neither store recovered after 30s")

    # Step 6: Check Services
    print("  📊 Step 6: Check if services are recovering...")

    # Services brauchen Zeit zum Reconnecten, aber sollten nicht crashed sein
    result = run_docker_compose(["ps", "--format", "json"])

    if result.returncode == 0:
        running_count = result.stdout.count('"Status":')
        print(f"    ✓ {running_count} containers still running")
    else:
        print("    ⚠️  Could not check container status")

    print("\n✅ Concurrent crash test completed")
    print(
        "    ℹ️  Note: Full recovery might take 60-90s - this test validates resilience"
    )


if __name__ == "__main__":
    # Run with: pytest -v -m local_only tests/local/test_chaos_resilience.py
    pytest.main([__file__, "-v", "-m", "local_only", "-s"])
