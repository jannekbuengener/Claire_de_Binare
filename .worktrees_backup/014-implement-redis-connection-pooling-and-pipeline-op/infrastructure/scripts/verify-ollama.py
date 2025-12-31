#!/usr/bin/env python3
"""Verify Ollama API is running and required models are loaded.

This script tests:
1. Ollama API endpoint responds at http://localhost:11434/api/tags
2. nomic-embed-text model is available
3. deepseek-r1:7b model is available
4. Optional: Test embedding generation

Usage:
    python infrastructure/scripts/verify-ollama.py [--host HOST] [--port PORT] [--timeout TIMEOUT]
"""
import argparse
import json
import sys
import urllib.request
import urllib.error
from typing import Optional


REQUIRED_MODELS = [
    "nomic-embed-text",
    "deepseek-r1:7b",
]


def check_ollama_api(host: str, port: int, timeout: int) -> dict:
    """Check if Ollama API is accessible and return model list."""
    url = f"http://{host}:{port}/api/tags"

    try:
        request = urllib.request.Request(
            url,
            headers={"Content-Type": "application/json"},
            method="GET"
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return {"error": f"Unexpected status code: {response.status}"}
            data = json.loads(response.read().decode("utf-8"))
            return {"success": True, "data": data, "status": response.status}
    except urllib.error.URLError as e:
        return {"error": f"Connection failed: {e.reason}"}
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP error: {e.code} {e.reason}"}
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON response: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


def check_models_available(model_data: dict, required: list) -> dict:
    """Check if required models are available in the model list."""
    models = model_data.get("models", [])
    model_names = []

    for model in models:
        name = model.get("name", "")
        model_names.append(name)

    results = {}
    for required_model in required:
        found = False
        for name in model_names:
            if required_model in name:
                found = True
                results[required_model] = {"available": True, "full_name": name}
                break
        if not found:
            results[required_model] = {"available": False, "full_name": None}

    return {"models": results, "all_models": model_names}


def check_openai_compatible_api(host: str, port: int, timeout: int) -> dict:
    """Check if OpenAI-compatible API endpoint works."""
    url = f"http://{host}:{port}/v1/models"

    try:
        request = urllib.request.Request(
            url,
            headers={"Content-Type": "application/json"},
            method="GET"
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return {"error": f"Unexpected status code: {response.status}"}
            data = json.loads(response.read().decode("utf-8"))
            return {"success": True, "data": data, "status": response.status}
    except Exception as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Verify Ollama API and models")
    parser.add_argument("--host", default="localhost", help="Ollama host (default: localhost)")
    parser.add_argument("--port", type=int, default=11434, help="Ollama port (default: 11434)")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds (default: 30)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    results = {
        "api_check": None,
        "models_check": None,
        "openai_api_check": None,
        "overall": None,
    }

    print("=" * 60)
    print("Ollama API Verification")
    print("=" * 60)
    print(f"\nTarget: http://{args.host}:{args.port}")
    print(f"Timeout: {args.timeout}s")
    print(f"Required Models: {', '.join(REQUIRED_MODELS)}")
    print()

    # Step 1: Check API endpoint
    print("-" * 60)
    print("Step 1: Checking Ollama API endpoint (/api/tags)")
    print("-" * 60)
    api_result = check_ollama_api(args.host, args.port, args.timeout)
    results["api_check"] = api_result

    if "error" in api_result:
        print(f"  [✗] FAILED: {api_result['error']}")
        print()
        print("Troubleshooting:")
        print("  1. Ensure Ollama container is running:")
        print("     docker compose -f infrastructure/compose/memory.yml up -d cdb_ollama")
        print("  2. Check container logs:")
        print("     docker logs cdb_ollama")
        print("  3. Verify port is not blocked by firewall")
        print()
        results["overall"] = "FAILED"
        if args.json:
            print(json.dumps(results, indent=2))
        return 1

    print(f"  [✓] API responding (HTTP {api_result['status']})")

    # Step 2: Check models
    print()
    print("-" * 60)
    print("Step 2: Checking required models")
    print("-" * 60)

    model_data = api_result.get("data", {})
    model_check = check_models_available(model_data, REQUIRED_MODELS)
    results["models_check"] = model_check

    all_models_found = True
    for model_name, info in model_check["models"].items():
        if info["available"]:
            print(f"  [✓] {model_name}: {info['full_name']}")
        else:
            print(f"  [✗] {model_name}: NOT FOUND")
            all_models_found = False

    if not all_models_found:
        print()
        print("Missing models. To pull them, run:")
        for model_name, info in model_check["models"].items():
            if not info["available"]:
                print(f"  docker compose -f infrastructure/compose/memory.yml exec cdb_ollama ollama pull {model_name}")
        print()

    if model_check["all_models"]:
        print()
        print(f"All available models: {', '.join(model_check['all_models'])}")

    # Step 3: Check OpenAI-compatible API
    print()
    print("-" * 60)
    print("Step 3: Checking OpenAI-compatible API (/v1/models)")
    print("-" * 60)

    openai_result = check_openai_compatible_api(args.host, args.port, args.timeout)
    results["openai_api_check"] = openai_result

    if "error" in openai_result:
        print(f"  [!] Warning: {openai_result['error']}")
        print("      (This endpoint is optional but recommended for Graphiti integration)")
    else:
        print(f"  [✓] OpenAI-compatible API responding (HTTP {openai_result['status']})")
        models_list = openai_result.get("data", {}).get("data", [])
        if models_list:
            model_ids = [m.get("id", "unknown") for m in models_list]
            print(f"      Models: {', '.join(model_ids)}")

    # Summary
    print()
    print("=" * 60)
    print("Verification Summary")
    print("=" * 60)

    checks = [
        ("Ollama API accessible", "error" not in api_result),
        ("Required models available", all_models_found),
        ("OpenAI-compatible API", "error" not in openai_result),
    ]

    for check_name, passed in checks:
        symbol = "✓" if passed else "✗"
        status = "PASS" if passed else "FAIL"
        print(f"  [{symbol}] {check_name}: {status}")

    # Determine overall result
    # API and models are required, OpenAI API is optional
    if "error" not in api_result and all_models_found:
        results["overall"] = "PASSED"
        print()
        print("RESULT: VERIFICATION PASSED")
        print()
        print("Ollama is ready for Graphiti MCP integration.")
        print(f"  API Endpoint: http://{args.host}:{args.port}/api/tags")
        print(f"  OpenAI API: http://{args.host}:{args.port}/v1")
        exit_code = 0
    elif "error" not in api_result and not all_models_found:
        results["overall"] = "PARTIAL"
        print()
        print("RESULT: PARTIAL (API running, models missing)")
        print()
        print("Run the init script to pull required models:")
        print("  ./infrastructure/scripts/init-memory.sh")
        print("Or on Windows:")
        print("  .\\infrastructure\\scripts\\init-memory.ps1")
        exit_code = 1
    else:
        results["overall"] = "FAILED"
        print()
        print("RESULT: VERIFICATION FAILED")
        exit_code = 1

    if args.json:
        print()
        print("JSON Output:")
        print(json.dumps(results, indent=2))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
