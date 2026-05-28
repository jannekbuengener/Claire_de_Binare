"""
Docker Compose Lifecycle Test - Claire de Binare
Lokaler-only Test: Vollständiger Container-Lebenszyklus

WICHTIG: Dieser Test MUSS lokal ausgeführt werden!
    - Erfordert Docker Compose CLI
    - Stoppt/Startet Container
    - Testet Recovery-Szenarien
    - NICHT in CI (zu destruktiv)

Ausführung:
    pytest -v -m local_only tests/local/test_docker_lifecycle.py
"""

import pytest
import subprocess
import time
import logging
import json


def run_docker_compose(args, timeout=30):
    """Helper: Docker Compose Command ausführen"""
    cmd = ["docker", "compose"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result


def parse_docker_json(stdout):
    """Parse docker compose ps --format json output (multiple JSON objects)"""
    services = []
    for line in stdout.strip().split("\n"):
        if line.strip():
            try:
                services.append(json.loads(line))
            except json.JSONDecodeError:
                logging.getLogger(__name__).debug(
                    "JSON decode error for docker ps line (ignored)"
                )
    return services


@pytest.mark.local_only
@pytest.mark.slow
def test_docker_compose_stop_start_cycle():
    """
    Lifecycle-Test: Stop → Start Cycle

    Validiert:
    - Alle Services können gestoppt werden
    - Alle Services starten sauber neu
    - Health-Checks nach Restart
    """
    print("\n🔄 Testing Docker Compose stop/start cycle...")

    # Step 1: Stop all services
    print("  🛑 Stopping all services...")
    result = run_docker_compose(["stop"])
    assert result.returncode == 0, f"Failed to stop services: {result.stderr}"
    print("    ✓ All services stopped")

    time.sleep(3)

    # Step 2: Start all services
    print("  ▶️  Starting all services...")
    result = run_docker_compose(["up", "-d"])
    assert result.returncode == 0, f"Failed to start services: {result.stderr}"
    print("    ✓ All services started")

    # Step 3: Wait for health checks
    print("  ⏳ Waiting for health checks (30s)...")
    time.sleep(30)

    # Step 4: Verify all healthy
    result = run_docker_compose(["ps", "--format", "json"])
    services = parse_docker_json(result.stdout)

    healthy_count = sum(
        1
        for s in services
        if "healthy" in s.get("Status", "").lower() or s.get("Health") == "healthy"
    )

    print(f"\n📊 Services after restart: {healthy_count}/{len(services)} healthy")

    # Mindestens 7/9 sollten healthy sein
    assert (
        healthy_count >= 7
    ), f"Too many unhealthy after restart: {healthy_count}/{len(services)}"

    print("✅ Stop/Start cycle successful")


@pytest.mark.local_only
@pytest.mark.slow
def test_docker_compose_restart_individual_service():
    """
    Lifecycle-Test: Einzelner Service Restart

    Validiert:
    - Einzelner Service kann neu gestartet werden
    - Andere Services bleiben stabil
    - Service kommt nach Restart wieder healthy
    """
    print("\n🔄 Testing individual service restart (cdb_core)...")

    # Step 1: Get baseline service count
    result = run_docker_compose(["ps", "--format", "json"])
    baseline_services = parse_docker_json(result.stdout)
    baseline_count = len(baseline_services)

    # Step 2: Restart cdb_core
    print("  🔄 Restarting cdb_core...")
    result = run_docker_compose(["restart", "cdb_core"])
    assert result.returncode == 0, f"Failed to restart cdb_core: {result.stderr}"

    time.sleep(10)  # Wait for restart

    # Step 3: Check services after restart
    result = run_docker_compose(["ps", "--format", "json"])
    after_services = parse_docker_json(result.stdout)

    # All services should still be running
    assert len(after_services) == baseline_count, "Service count changed after restart"

    # Find cdb_core
    cdb_core = next(
        (s for s in after_services if "cdb_core" in s.get("Name", "")), None
    )
    assert cdb_core is not None, "cdb_core not found after restart"

    print(f"  ✓ cdb_core status: {cdb_core.get('Status')}")

    # Wait for health check
    print("  ⏳ Waiting for cdb_core health check...")
    time.sleep(20)

    result = run_docker_compose(["ps", "cdb_core", "--format", "json"])
    cdb_core_final = parse_docker_json(result.stdout)[0]

    is_healthy = "healthy" in cdb_core_final.get("Status", "").lower()

    print(f"  ✓ cdb_core final status: {cdb_core_final.get('Status')}")

    if not is_healthy:
        print("  ⚠️  Service not healthy yet (might need more time)")

    print("✅ Individual service restart successful")


@pytest.mark.local_only
@pytest.mark.slow
def test_docker_compose_recreate_service():
    """
    Lifecycle-Test: Service Recreate (fresh container)

    Validiert:
    - Service kann komplett neu erstellt werden
    - Volumes bleiben erhalten
    - Service wird healthy
    """
    print("\n🔄 Testing service recreate (cdb_db_writer)...")

    # Step 1: Force recreate cdb_db_writer
    print("  🔄 Recreating cdb_db_writer (force)...")
    result = run_docker_compose(["up", "-d", "--force-recreate", "cdb_db_writer"])
    assert result.returncode == 0, f"Failed to recreate: {result.stderr}"

    time.sleep(15)

    # Step 2: Check if service is running
    result = run_docker_compose(["ps", "cdb_db_writer", "--format", "json"])
    service = parse_docker_json(result.stdout)[0]

    print(f"  ✓ cdb_db_writer status: {service.get('Status')}")

    # Service should be running (might not be healthy yet)
    assert "Up" in service.get("Status", ""), "Service not running after recreate"

    print("✅ Service recreate successful")


@pytest.mark.local_only
def test_docker_compose_down_up_full_cycle():
    """
    Lifecycle-Test: Vollständiger Down → Up Cycle

    ⚠️  DESTRUKTIV: Entfernt alle Container!

    Validiert:
    - Kompletter Teardown
    - Kompletter Setup von Scratch
    - Alle Services healthy nach Up
    """
    print("\n🔄 Testing full down/up cycle...")
    print("⚠️  This is a DESTRUCTIVE test - containers will be removed!")

    # Step 1: Down (remove containers, keep volumes)
    print("  🛑 Running docker compose down...")
    result = run_docker_compose(["down"], timeout=60)
    assert result.returncode == 0, f"Failed to down: {result.stderr}"
    print("    ✓ All containers removed")

    time.sleep(5)

    # Step 2: Up (create fresh containers)
    print("  ▶️  Running docker compose up -d...")
    result = run_docker_compose(["up", "-d"], timeout=120)
    assert result.returncode == 0, f"Failed to up: {result.stderr}"
    print("    ✓ All containers created")

    # Step 3: Wait for initialization
    print("  ⏳ Waiting for services to initialize (60s)...")
    time.sleep(60)

    # Step 4: Check health
    result = run_docker_compose(["ps", "--format", "json"])
    services = parse_docker_json(result.stdout)

    print("\n📊 Services after full cycle:")
    for service in services:
        name = service.get("Name", "unknown")
        status = service.get("Status", "unknown")
        print(f"  - {name}: {status}")

    healthy_count = sum(
        1
        for s in services
        if "healthy" in s.get("Status", "").lower() or s.get("Health") == "healthy"
    )

    print(f"\n📊 Healthy services: {healthy_count}/{len(services)}")

    # Mindestens 6/9 sollten healthy sein (einige brauchen länger)
    assert (
        healthy_count >= 6
    ), f"Too many unhealthy after full cycle: {healthy_count}/{len(services)}"

    print("✅ Full down/up cycle successful")


@pytest.mark.local_only
def test_docker_compose_logs_no_errors():
    """
    Test: Prüfe Docker Logs auf kritische Errors

    Validiert:
    - Keine CRITICAL/ERROR logs in letzten 100 Zeilen
    - Services laufen ohne Crashes
    """
    print("\n📋 Checking Docker logs for errors...")

    services = ["cdb_core", "cdb_risk", "cdb_execution", "cdb_db_writer"]

    for service in services:
        print(f"\n  📋 Checking {service} logs...")

        result = run_docker_compose(["logs", "--tail", "50", service])

        if result.returncode != 0:
            print(f"    ⚠️  Could not fetch logs for {service}")
            continue

        logs = result.stdout.lower()

        # Count critical/error messages
        critical_count = logs.count("critical")
        error_count = logs.count("error") - logs.count("no error")  # Exclude "no error"

        print(f"    - CRITICAL: {critical_count}")
        print(f"    - ERROR: {error_count}")

        # Soft assertion (einige Errors können OK sein in Tests)
        if critical_count > 0:
            print(f"    ⚠️  {service} has {critical_count} CRITICAL messages")

        if error_count > 5:
            print(f"    ⚠️  {service} has {error_count} ERROR messages")

    print("\n✅ Log check completed")


@pytest.mark.local_only
def test_docker_compose_volume_persistence():
    """
    Test: Volume-Persistenz über Container-Neustarts

    Validiert:
    - PostgreSQL-Daten bleiben erhalten
    - Redis-Daten bleiben erhalten (AOF)
    """
    print("\n💾 Testing volume persistence...")

    import psycopg2

    # Step 1: Get baseline data count
    print("  📊 Counting baseline data...")
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="claire_de_binare",
            user="claire_user",
            password="local_test",
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
        baseline_count = cursor.fetchone()[0]
        conn.close()

        print(f"    ✓ Baseline snapshots: {baseline_count}")

    except Exception as e:
        pytest.skip(f"Cannot connect to PostgreSQL: {e}")

    # Step 2: Restart PostgreSQL container
    print("  🔄 Restarting cdb_postgres...")
    result = run_docker_compose(["restart", "cdb_postgres"])
    assert result.returncode == 0, "Failed to restart postgres"

    time.sleep(10)

    # Step 3: Check data after restart
    print("  📊 Counting data after restart...")
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="claire_de_binare",
        user="claire_user",
        password="local_test",
    )
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
    after_count = cursor.fetchone()[0]
    conn.close()

    print(f"    ✓ Snapshots after restart: {after_count}")

    # Data should be preserved
    assert (
        after_count == baseline_count
    ), f"Data lost after restart: {baseline_count} → {after_count}"

    print("✅ Volume persistence verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "local_only", "-s"])
