#!/usr/bin/env python3
"""Verify data persistence across container restart.

This script tests the end-to-end persistence of the memory backend:
1. Check if services are healthy
2. Verify FalkorDB has data stored (via redis-cli in container)
3. Optionally restart containers
4. Wait for services to be healthy again
5. Verify FalkorDB data persisted after restart

Note: The Graphiti MCP Server uses WebSocket transport for MCP protocol.
This script verifies persistence at the database level (FalkorDB).

Usage:
    # Full automated test (requires docker access):
    python infrastructure/scripts/verify-persistence.py --auto-restart

    # Check only (no restart):
    python infrastructure/scripts/verify-persistence.py --skip-restart

    # Show detailed verification steps:
    python infrastructure/scripts/verify-persistence.py --verbose
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
import urllib.error
from typing import Optional, Tuple


# Configuration
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8000
DEFAULT_TIMEOUT = 60
COMPOSE_FILE = "infrastructure/compose/memory.yml"
GRAPHITI_CONTAINER = "cdb_graphiti"
OLLAMA_CONTAINER = "cdb_ollama"


def check_health(host: str, port: int, timeout: int) -> Tuple[bool, dict]:
    """Check if Graphiti health endpoint responds."""
    url = f"http://{host}:{port}/health"

    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            return response.status == 200, data
    except Exception as e:
        return False, {"error": str(e)}


def wait_for_health(host: str, port: int, timeout: int, max_wait: int = 120) -> bool:
    """Wait for the service to become healthy."""
    start_time = time.time()
    while time.time() - start_time < max_wait:
        healthy, _ = check_health(host, port, timeout)
        if healthy:
            return True
        print("  Waiting for service to be healthy...")
        time.sleep(5)
    return False


def run_command(command: list, timeout: int = 300) -> dict:
    """Run a shell command and return result."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except FileNotFoundError:
        return {"error": f"Command not found: {command[0]}"}
    except Exception as e:
        return {"error": str(e)}


def check_docker_available() -> bool:
    """Check if docker command is available."""
    result = run_command(["docker", "version"])
    return result.get("success", False)


def check_volume_exists(volume_name: str) -> dict:
    """Check if a Docker volume exists."""
    result = run_command(["docker", "volume", "inspect", volume_name])
    if result.get("success"):
        try:
            data = json.loads(result["stdout"])
            return {"exists": True, "data": data}
        except json.JSONDecodeError:
            return {"exists": True, "raw": result["stdout"]}
    return {"exists": False, "error": result.get("stderr", result.get("error", "Unknown error"))}


def check_falkordb_keys(container: str) -> dict:
    """Check FalkorDB for stored data using redis-cli."""
    result = run_command(["docker", "exec", container, "redis-cli", "-p", "6379", "KEYS", "*"])

    if not result.get("success"):
        return {"error": result.get("stderr", result.get("error", "Failed to query FalkorDB"))}

    keys = result["stdout"].split("\n") if result["stdout"] else []
    keys = [k.strip() for k in keys if k.strip()]

    return {"success": True, "keys": keys, "count": len(keys)}


def check_falkordb_ping(container: str) -> dict:
    """Ping FalkorDB to verify it's running."""
    result = run_command(["docker", "exec", container, "redis-cli", "-p", "6379", "PING"])

    if result.get("success") and "PONG" in result.get("stdout", ""):
        return {"success": True}
    return {"error": result.get("stderr", result.get("error", "FalkorDB not responding"))}


def restart_containers(compose_file: str) -> dict:
    """Restart containers using docker compose."""
    print("  Stopping containers...")
    down_result = run_command(["docker", "compose", "-f", compose_file, "down"])

    if not down_result.get("success") and "error" not in down_result:
        print(f"    Warning: docker compose down returned {down_result.get('returncode')}")

    print("  Starting containers...")
    up_result = run_command(["docker", "compose", "-f", compose_file, "up", "-d"])

    if not up_result.get("success"):
        return {"error": f"Failed to start containers: {up_result.get('stderr', up_result.get('error', 'unknown'))}"}

    return {"success": True}


def print_manual_test_steps():
    """Print manual steps for persistence verification."""
    print("""
==============================================================================
MANUAL PERSISTENCE VERIFICATION STEPS
==============================================================================

Since automated MCP testing requires WebSocket support, use these manual steps:

1. WRITE TEST DATA (via MCP client or FalkorDB directly):

   Using Claude Code with MCP configured:
   - Ask Claude to "remember that I prefer TypeScript"
   - Or use MCP add_episode method via WebSocket client

   Direct FalkorDB write (for testing):
   docker exec cdb_graphiti redis-cli -p 6379 SET persistence_test "verified"

2. VERIFY DATA EXISTS BEFORE RESTART:

   docker exec cdb_graphiti redis-cli -p 6379 KEYS '*'
   docker exec cdb_graphiti redis-cli -p 6379 GET persistence_test

3. RESTART CONTAINERS:

   docker compose -f infrastructure/compose/memory.yml down
   docker compose -f infrastructure/compose/memory.yml up -d

4. WAIT FOR SERVICES TO BE HEALTHY:

   # Wait 30-60 seconds, then check:
   curl http://localhost:8000/health
   docker ps --filter name=cdb_graphiti --format "{{.Names}}: {{.Status}}"

5. VERIFY DATA PERSISTED:

   docker exec cdb_graphiti redis-cli -p 6379 KEYS '*'
   docker exec cdb_graphiti redis-cli -p 6379 GET persistence_test

   # Expected: Same keys/data as before restart

6. CLEANUP TEST DATA (optional):

   docker exec cdb_graphiti redis-cli -p 6379 DEL persistence_test

==============================================================================
""")


def main():
    parser = argparse.ArgumentParser(
        description="Verify data persistence across container restart",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full automated test (requires docker):
  python infrastructure/scripts/verify-persistence.py --auto-restart

  # Check only (no restart):
  python infrastructure/scripts/verify-persistence.py --skip-restart

  # Print manual verification steps:
  python infrastructure/scripts/verify-persistence.py --manual
"""
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Graphiti host (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Graphiti port (default: {DEFAULT_PORT})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help=f"Request timeout (default: {DEFAULT_TIMEOUT}s)")
    parser.add_argument("--auto-restart", action="store_true", help="Automatically restart containers")
    parser.add_argument("--skip-restart", action="store_true", help="Skip restart, only verify current state")
    parser.add_argument("--manual", action="store_true", help="Print manual verification steps and exit")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    if args.manual:
        print_manual_test_steps()
        return 0

    results = {
        "health_check": None,
        "docker_available": None,
        "volumes": {},
        "falkordb_ping": None,
        "keys_before_restart": None,
        "restart": None,
        "health_after_restart": None,
        "keys_after_restart": None,
        "persistence_verified": None,
        "overall": None,
    }

    print("=" * 70)
    print("Memory Backend Persistence Verification")
    print("=" * 70)
    print(f"\nTarget: http://{args.host}:{args.port}")
    print(f"Compose File: {COMPOSE_FILE}")
    print()

    # Step 1: Check service health
    print("-" * 70)
    print("Step 1: Checking service health")
    print("-" * 70)

    healthy, health_data = check_health(args.host, args.port, args.timeout)
    results["health_check"] = {"healthy": healthy, "data": health_data}

    if healthy:
        print(f"  [OK] Service is healthy")
        if args.verbose:
            print(f"      Response: {json.dumps(health_data)}")
    else:
        print("  [!] Service not healthy or not running")
        print()
        print("  Start the memory stack first:")
        print(f"      docker compose -f {COMPOSE_FILE} up -d")
        print()
        print("  Then run the init script:")
        print("      ./infrastructure/scripts/init-memory.sh")
        print()
        print_manual_test_steps()
        results["overall"] = "FAILED"
        if args.json:
            print(json.dumps(results, indent=2))
        return 1

    # Step 2: Check Docker availability
    print()
    print("-" * 70)
    print("Step 2: Checking Docker access")
    print("-" * 70)

    docker_ok = check_docker_available()
    results["docker_available"] = docker_ok

    if docker_ok:
        print("  [OK] Docker is available")
    else:
        print("  [!] Docker command not available")
        print()
        print("  Cannot verify FalkorDB data without Docker access.")
        print("  See manual verification steps below.")
        print()
        print_manual_test_steps()
        results["overall"] = "MANUAL_REQUIRED"
        if args.json:
            print(json.dumps(results, indent=2))
        return 0  # Not a failure, just needs manual verification

    # Step 3: Check volumes exist
    print()
    print("-" * 70)
    print("Step 3: Checking Docker volumes")
    print("-" * 70)

    volumes_to_check = [
        ("cdb_graphiti_data", "FalkorDB data"),
        ("cdb_ollama_data", "Ollama models"),
        # Also check with stack name prefix
        ("cdb-memory_cdb_graphiti_data", "FalkorDB data (prefixed)"),
        ("cdb-memory_cdb_ollama_data", "Ollama models (prefixed)"),
    ]

    found_volumes = 0
    for vol_name, description in volumes_to_check:
        vol_result = check_volume_exists(vol_name)
        results["volumes"][vol_name] = vol_result
        if vol_result.get("exists"):
            print(f"  [OK] {description}: {vol_name}")
            found_volumes += 1

    if found_volumes == 0:
        print("  [!] No persistence volumes found")
        print("      This may indicate volumes haven't been created yet.")
        print("      Volumes are created on first container start.")

    # Step 4: Ping FalkorDB
    print()
    print("-" * 70)
    print("Step 4: Verifying FalkorDB connection")
    print("-" * 70)

    ping_result = check_falkordb_ping(GRAPHITI_CONTAINER)
    results["falkordb_ping"] = ping_result

    if ping_result.get("success"):
        print("  [OK] FalkorDB is responding (PONG)")
    else:
        print(f"  [!] FalkorDB not responding: {ping_result.get('error', 'unknown')}")
        results["overall"] = "FAILED"
        if args.json:
            print(json.dumps(results, indent=2))
        return 1

    # Step 5: Check keys before restart
    print()
    print("-" * 70)
    print("Step 5: Checking FalkorDB data (before restart)")
    print("-" * 70)

    keys_before = check_falkordb_keys(GRAPHITI_CONTAINER)
    results["keys_before_restart"] = keys_before

    if keys_before.get("success"):
        key_count = keys_before.get("count", 0)
        print(f"  [OK] Found {key_count} key(s) in FalkorDB")
        if args.verbose and keys_before.get("keys"):
            for key in keys_before["keys"][:10]:
                print(f"      - {key}")
            if len(keys_before["keys"]) > 10:
                print(f"      ... and {len(keys_before['keys']) - 10} more")
    else:
        print(f"  [!] Could not query keys: {keys_before.get('error', 'unknown')}")

    # Step 6: Restart containers (unless skipped)
    print()
    print("-" * 70)
    print("Step 6: Container restart")
    print("-" * 70)

    if args.skip_restart:
        print("  [--] Skipping restart (--skip-restart flag)")
        results["restart"] = {"skipped": True}
    elif args.auto_restart:
        print("  Restarting containers automatically...")
        restart_result = restart_containers(COMPOSE_FILE)
        results["restart"] = restart_result

        if "error" in restart_result:
            print(f"  [!] Restart failed: {restart_result['error']}")
            print()
            print("  Please restart containers manually:")
            print(f"      docker compose -f {COMPOSE_FILE} down")
            print(f"      docker compose -f {COMPOSE_FILE} up -d")
            results["overall"] = "MANUAL_REQUIRED"
        else:
            print("  [OK] Containers restarted")
    else:
        print("  Manual restart required.")
        print()
        print("  Please run the following commands in another terminal:")
        print(f"      docker compose -f {COMPOSE_FILE} down")
        print(f"      docker compose -f {COMPOSE_FILE} up -d")
        print()
        try:
            input("  Press Enter after restarting containers...")
        except EOFError:
            print("  (Non-interactive mode, skipping restart)")
            results["restart"] = {"skipped": True, "non_interactive": True}
        else:
            results["restart"] = {"manual": True}

    # Step 7: Wait for health after restart
    if not args.skip_restart and results.get("restart", {}).get("skipped") is not True:
        print()
        print("-" * 70)
        print("Step 7: Waiting for services to be healthy after restart")
        print("-" * 70)

        print("  Waiting for containers to initialize (30s)...")
        time.sleep(30)

        healthy = wait_for_health(args.host, args.port, args.timeout, max_wait=120)
        results["health_after_restart"] = {"healthy": healthy}

        if healthy:
            print("  [OK] Service is healthy after restart")
        else:
            print("  [!] Service did not become healthy after restart")
            results["overall"] = "FAILED"
            if args.json:
                print(json.dumps(results, indent=2))
            return 1

    # Step 8: Check keys after restart
    if not args.skip_restart and results.get("restart", {}).get("skipped") is not True:
        print()
        print("-" * 70)
        print("Step 8: Checking FalkorDB data (after restart)")
        print("-" * 70)

        keys_after = check_falkordb_keys(GRAPHITI_CONTAINER)
        results["keys_after_restart"] = keys_after

        if keys_after.get("success"):
            key_count = keys_after.get("count", 0)
            print(f"  [OK] Found {key_count} key(s) in FalkorDB")
            if args.verbose and keys_after.get("keys"):
                for key in keys_after["keys"][:10]:
                    print(f"      - {key}")
        else:
            print(f"  [!] Could not query keys: {keys_after.get('error', 'unknown')}")

        # Compare before and after
        before_count = keys_before.get("count", 0)
        after_count = keys_after.get("count", 0)

        if before_count > 0 and after_count >= before_count:
            results["persistence_verified"] = True
            print()
            print(f"  [OK] Data persisted: {before_count} keys before, {after_count} keys after")
        elif before_count == 0 and after_count == 0:
            results["persistence_verified"] = None
            print()
            print("  [--] No data to verify (both counts are 0)")
            print("      Add some data via MCP and re-run this test")
        else:
            results["persistence_verified"] = False
            print()
            print(f"  [!] Data may have been lost: {before_count} keys before, {after_count} keys after")

    # Summary
    print()
    print("=" * 70)
    print("Verification Summary")
    print("=" * 70)

    health_ok = results.get("health_check", {}).get("healthy", False)
    ping_ok = results.get("falkordb_ping", {}).get("success", False)
    volumes_ok = sum(1 for v in results.get("volumes", {}).values() if v.get("exists")) > 0
    persist_ok = results.get("persistence_verified", None)

    checks = [
        ("Service health", health_ok),
        ("FalkorDB responding", ping_ok),
        ("Volumes exist", volumes_ok),
    ]

    if not args.skip_restart and results.get("restart", {}).get("skipped") is not True:
        if persist_ok is True:
            checks.append(("Data persistence", True))
        elif persist_ok is False:
            checks.append(("Data persistence", False))
        else:
            checks.append(("Data persistence", None))

    for check_name, passed in checks:
        if passed is True:
            print(f"  [OK] {check_name}: PASS")
        elif passed is False:
            print(f"  [!!] {check_name}: FAIL")
        else:
            print(f"  [--] {check_name}: N/A (no data to verify)")

    # Determine overall result
    print()

    if health_ok and ping_ok and volumes_ok:
        if args.skip_restart:
            results["overall"] = "PASSED"
            print("RESULT: VERIFICATION PASSED")
            print()
            print("Memory backend is healthy with persistent storage configured.")
            print("Run with --auto-restart to verify data survives container restart.")
            exit_code = 0
        elif persist_ok is True:
            results["overall"] = "PASSED"
            print("RESULT: PERSISTENCE VERIFICATION PASSED")
            print()
            print("Data persisted successfully across container restart!")
            print("The memory backend is working correctly.")
            exit_code = 0
        elif persist_ok is None:
            results["overall"] = "PARTIAL"
            print("RESULT: PARTIAL (no data to verify)")
            print()
            print("Storage is configured correctly, but no data was present to verify.")
            print()
            print("To complete verification:")
            print("  1. Add data via MCP (WebSocket) or directly via FalkorDB:")
            print(f"     docker exec {GRAPHITI_CONTAINER} redis-cli -p 6379 SET test_key 'test_value'")
            print("  2. Run this script again with --auto-restart")
            exit_code = 0
        else:
            results["overall"] = "FAILED"
            print("RESULT: PERSISTENCE VERIFICATION FAILED")
            print()
            print("Data was lost after container restart.")
            print()
            print("Troubleshooting:")
            print(f"  1. Check volumes: docker volume inspect cdb_graphiti_data")
            print(f"  2. Check container logs: docker logs {GRAPHITI_CONTAINER}")
            print("  3. Verify volume mount in compose file")
            exit_code = 1
    else:
        results["overall"] = "FAILED"
        print("RESULT: VERIFICATION FAILED")
        print()
        print("Core infrastructure checks failed.")
        print()
        print("Troubleshooting:")
        print(f"  1. Start memory stack: docker compose -f {COMPOSE_FILE} up -d")
        print(f"  2. Check container status: docker compose -f {COMPOSE_FILE} ps")
        print(f"  3. Check logs: docker logs {GRAPHITI_CONTAINER}")
        exit_code = 1

    if args.json:
        print()
        print("JSON Output:")
        print(json.dumps(results, indent=2))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
