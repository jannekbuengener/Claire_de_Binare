#!/usr/bin/env python3
"""
COPILOT SMART STARTUP ORCHESTRATOR
Intelligent system startup with health validation and smart error handling
"""

import subprocess
import time
import sys
import requests
from pathlib import Path


def run_command(cmd, description):
    """Run command with smart error handling.

    Args:
        cmd: Command as a list of strings (e.g., ['docker', 'compose', 'up', '-d']).
             List-based commands are required for security (prevents shell injection).
        description: Human-readable description of the command for logging.

    Returns:
        bool: True if command succeeded (exit code 0), False otherwise.

    Security Note:
        Uses list-based command execution (shell=False) to prevent command injection
        vulnerabilities. Never pass shell=True with untrusted input.
    """
    print(f"🚀 {description}...")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return True
        else:
            print(f"❌ {description} failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} timed out")
        return False
    except Exception as e:
        print(f"💥 {description} error: {e}")
        return False


def wait_for_service(name, url, max_attempts=12, delay=10):
    """Smart service health waiting with exponential backoff"""
    print(f"⏳ Waiting for {name} to become healthy...")

    for attempt in range(max_attempts):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {name} is healthy!")
                return True
        except requests.RequestException:
            pass

        wait_time = min(delay * (1.5**attempt), 60)  # Exponential backoff, max 60s
        print(f"   Attempt {attempt + 1}/{max_attempts}, waiting {wait_time:.1f}s...")
        time.sleep(wait_time)

    print(f"❌ {name} failed to become healthy after {max_attempts} attempts")
    return False


def smart_startup():
    """Orchestrate intelligent system startup"""
    print("🎯 COPILOT SMART STARTUP ORCHESTRATOR")
    print("=" * 60)

    # Check prerequisites
    print("\n📋 Checking prerequisites...")
    if not Path("docker-compose.yml").exists():
        print("❌ docker-compose.yml not found!")
        return False

    if not Path(".env").exists():
        print("⚠️ .env file missing - services may fail to start")

    # Start infrastructure
    if not run_command(['docker', 'compose', 'up', '-d'], "Starting Docker infrastructure"):
        return False

    # Smart health waiting
    print("\n🔍 Waiting for services to become healthy...")
    services = [
        ("Signal Engine", "http://localhost:5001/health"),
        ("Risk Manager", "http://localhost:5002/health"),
        ("Execution Service", "http://localhost:5003/health"),
    ]

    healthy_services = 0
    for name, url in services:
        if wait_for_service(name, url):
            healthy_services += 1

    # Smart diagnostics
    print(f"\n📊 STARTUP SUMMARY: {healthy_services}/{len(services)} services healthy")

    if healthy_services == len(services):
        print("🎉 SYSTEM STARTUP SUCCESSFUL - ALL SERVICES OPERATIONAL")
        return True
    elif healthy_services > 0:
        print("⚠️ PARTIAL STARTUP - Some services may need manual intervention")
        return True
    else:
        print("🚨 STARTUP FAILED - No services responding")
        return False


if __name__ == "__main__":
    success = smart_startup()
    sys.exit(0 if success else 1)
