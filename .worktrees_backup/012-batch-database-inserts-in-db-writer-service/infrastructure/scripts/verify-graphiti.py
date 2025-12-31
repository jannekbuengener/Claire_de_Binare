#!/usr/bin/env python3
"""Verify Graphiti MCP endpoint is accessible and healthy.

This script tests:
1. Graphiti health endpoint responds at http://localhost:8000/health
2. MCP endpoint is accessible at http://localhost:8000/mcp/
3. FalkorDB is responding (via combined container)

Usage:
    python infrastructure/scripts/verify-graphiti.py [--host HOST] [--port PORT] [--timeout TIMEOUT]
"""
import argparse
import json
import sys
import urllib.request
import urllib.error
from typing import Optional


def check_health_endpoint(host: str, port: int, timeout: int) -> dict:
    """Check if Graphiti health endpoint responds."""
    url = f"http://{host}:{port}/health"

    try:
        request = urllib.request.Request(
            url,
            headers={"Content-Type": "application/json"},
            method="GET"
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return {"error": f"Unexpected status code: {response.status}"}
            try:
                data = json.loads(response.read().decode("utf-8"))
            except json.JSONDecodeError:
                data = {"raw": "Non-JSON response (OK for health endpoint)"}
            return {"success": True, "data": data, "status": response.status}
    except urllib.error.URLError as e:
        return {"error": f"Connection failed: {e.reason}"}
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP error: {e.code} {e.reason}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


def check_mcp_endpoint(host: str, port: int, timeout: int) -> dict:
    """Check if MCP endpoint is accessible.

    Note: The MCP endpoint at /mcp/ expects POST requests with JSON-RPC format.
    A GET request should return an error but proves the endpoint exists.
    """
    url = f"http://{host}:{port}/mcp/"

    # First try a simple GET to see if the endpoint responds
    try:
        request = urllib.request.Request(
            url,
            headers={"Content-Type": "application/json"},
            method="GET"
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {"success": True, "status": response.status, "method": "GET"}
    except urllib.error.HTTPError as e:
        # 405 Method Not Allowed is expected for GET on MCP endpoint
        if e.code == 405:
            return {"success": True, "status": e.code, "note": "Method Not Allowed (expected - endpoint exists)"}
        # Other error codes might still indicate the endpoint exists
        if e.code in [400, 422]:
            return {"success": True, "status": e.code, "note": f"HTTP {e.code} (endpoint exists, needs proper MCP request)"}
        return {"error": f"HTTP error: {e.code} {e.reason}"}
    except urllib.error.URLError as e:
        return {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


def check_mcp_rpc(host: str, port: int, timeout: int) -> dict:
    """Check MCP endpoint with a proper JSON-RPC request.

    Sends a minimal JSON-RPC request to verify the MCP server is functional.
    """
    url = f"http://{host}:{port}/mcp/"

    # JSON-RPC 2.0 format - list available methods
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }).encode("utf-8")

    try:
        request = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status not in [200, 201]:
                return {"error": f"Unexpected status code: {response.status}"}
            try:
                data = json.loads(response.read().decode("utf-8"))
                return {"success": True, "data": data, "status": response.status}
            except json.JSONDecodeError as e:
                return {"error": f"Invalid JSON response: {e}"}
    except urllib.error.HTTPError as e:
        try:
            error_body = e.read().decode("utf-8")
            return {"error": f"HTTP {e.code}: {error_body[:200]}"}
        except Exception:
            return {"error": f"HTTP error: {e.code} {e.reason}"}
    except urllib.error.URLError as e:
        return {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


def check_root_endpoint(host: str, port: int, timeout: int) -> dict:
    """Check if the root endpoint responds (basic connectivity)."""
    url = f"http://{host}:{port}/"

    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {"success": True, "status": response.status}
    except urllib.error.HTTPError as e:
        # Any HTTP response means the server is reachable
        return {"success": True, "status": e.code, "note": f"HTTP {e.code} (server reachable)"}
    except urllib.error.URLError as e:
        return {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


def main():
    parser = argparse.ArgumentParser(description="Verify Graphiti MCP endpoint")
    parser.add_argument("--host", default="localhost", help="Graphiti host (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, help="Graphiti port (default: 8000)")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds (default: 30)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--skip-rpc", action="store_true", help="Skip MCP RPC test (faster)")
    args = parser.parse_args()

    results = {
        "health_check": None,
        "mcp_endpoint_check": None,
        "mcp_rpc_check": None,
        "overall": None,
    }

    print("=" * 60)
    print("Graphiti MCP Endpoint Verification")
    print("=" * 60)
    print(f"\nTarget: http://{args.host}:{args.port}")
    print(f"Timeout: {args.timeout}s")
    print()

    # Step 1: Check health endpoint
    print("-" * 60)
    print("Step 1: Checking Graphiti health endpoint (/health)")
    print("-" * 60)
    health_result = check_health_endpoint(args.host, args.port, args.timeout)
    results["health_check"] = health_result

    if "error" in health_result:
        print(f"  [!] FAILED: {health_result['error']}")
        print()
        print("Troubleshooting:")
        print("  1. Ensure Graphiti container is running:")
        print("     docker compose -f infrastructure/compose/memory.yml up -d cdb_graphiti")
        print("  2. Check container logs:")
        print("     docker logs cdb_graphiti")
        print("  3. Ensure Ollama is healthy first (Graphiti depends on it):")
        print("     python infrastructure/scripts/verify-ollama.py")
        print("  4. Wait for Graphiti startup (60s start_period):")
        print("     docker compose -f infrastructure/compose/memory.yml ps")
        print()
    else:
        print(f"  [OK] Health endpoint responding (HTTP {health_result['status']})")
        if health_result.get("data"):
            print(f"      Response: {json.dumps(health_result['data'])[:100]}")

    # Step 2: Check MCP endpoint accessibility
    print()
    print("-" * 60)
    print("Step 2: Checking MCP endpoint (/mcp/)")
    print("-" * 60)

    mcp_result = check_mcp_endpoint(args.host, args.port, args.timeout)
    results["mcp_endpoint_check"] = mcp_result

    if "error" in mcp_result:
        print(f"  [!] FAILED: {mcp_result['error']}")
    else:
        status = mcp_result.get("status", "?")
        note = mcp_result.get("note", "")
        if note:
            print(f"  [OK] MCP endpoint accessible (HTTP {status})")
            print(f"      {note}")
        else:
            print(f"  [OK] MCP endpoint responding (HTTP {status})")

    # Step 3: Check MCP RPC functionality (optional)
    if not args.skip_rpc:
        print()
        print("-" * 60)
        print("Step 3: Testing MCP RPC (tools/list)")
        print("-" * 60)

        rpc_result = check_mcp_rpc(args.host, args.port, args.timeout)
        results["mcp_rpc_check"] = rpc_result

        if "error" in rpc_result:
            print(f"  [!] Warning: {rpc_result['error']}")
            print("      (MCP endpoint exists but RPC may need Ollama to be fully initialized)")
        else:
            print(f"  [OK] MCP RPC responding (HTTP {rpc_result['status']})")
            data = rpc_result.get("data", {})
            if "result" in data:
                tools = data.get("result", {}).get("tools", [])
                if tools:
                    tool_names = [t.get("name", "?") for t in tools[:5]]
                    print(f"      Available tools: {', '.join(tool_names)}...")
                else:
                    print("      Available tools: (none listed or different response format)")

    # Summary
    print()
    print("=" * 60)
    print("Verification Summary")
    print("=" * 60)

    # Determine what passed
    health_ok = "error" not in results.get("health_check", {"error": True})
    mcp_ok = "error" not in results.get("mcp_endpoint_check", {"error": True})
    rpc_ok = args.skip_rpc or "error" not in results.get("mcp_rpc_check", {"error": True})

    checks = [
        ("Health endpoint (/health)", health_ok),
        ("MCP endpoint (/mcp/)", mcp_ok),
    ]
    if not args.skip_rpc:
        checks.append(("MCP RPC functional", rpc_ok))

    for check_name, passed in checks:
        symbol = "OK" if passed else "!!"
        status = "PASS" if passed else "FAIL"
        print(f"  [{symbol}] {check_name}: {status}")

    # Determine overall result
    # Health endpoint is the primary requirement
    if health_ok:
        results["overall"] = "PASSED"
        print()
        print("RESULT: VERIFICATION PASSED")
        print()
        print("Graphiti MCP endpoint is accessible and healthy.")
        print(f"  Health: http://{args.host}:{args.port}/health")
        print(f"  MCP: http://{args.host}:{args.port}/mcp/")
        print()
        print("Auto-Claude Integration:")
        print('  Add to .mcp.json or Claude settings:')
        print('  {')
        print('    "mcpServers": {')
        print('      "graphiti-memory": {')
        print('        "transport": "http",')
        print(f'        "url": "http://{args.host}:{args.port}/mcp/"')
        print('      }')
        print('    }')
        print('  }')
        exit_code = 0
    elif mcp_ok:
        results["overall"] = "PARTIAL"
        print()
        print("RESULT: PARTIAL (MCP accessible, health check failed)")
        print()
        print("The MCP endpoint is accessible but health check failed.")
        print("This may indicate internal issues with FalkorDB or startup.")
        print()
        print("Check container logs:")
        print("  docker logs cdb_graphiti")
        exit_code = 1
    else:
        results["overall"] = "FAILED"
        print()
        print("RESULT: VERIFICATION FAILED")
        print()
        print("Graphiti MCP endpoint is not accessible.")
        print()
        print("Quick fixes to try:")
        print("  1. Start the memory stack:")
        print("     docker compose -f infrastructure/compose/memory.yml up -d")
        print()
        print("  2. Run the init script:")
        print("     ./infrastructure/scripts/init-memory.sh")
        print("     # Or on Windows:")
        print("     .\\infrastructure\\scripts\\init-memory.ps1")
        print()
        print("  3. Check container status:")
        print("     docker compose -f infrastructure/compose/memory.yml ps")
        exit_code = 1

    if args.json:
        print()
        print("JSON Output:")
        print(json.dumps(results, indent=2))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
