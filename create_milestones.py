#!/usr/bin/env python3
"""
create_milestones.py - Creates 9 GitHub Milestones for Claire de Binaire
Uses GitHub REST API directly without gh CLI dependency
"""

import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# GitHub API Configuration
REPO_OWNER = "jannekbuengener"
REPO_NAME = "Claire_de_Binare_Cleanroom"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Milestones to create
MILESTONES = [
    {
        "title": "M1 - Foundation & Governance Setup",
        "description": "Establish project foundation with documentation, governance structures, and development standards. Includes KODEX, ADRs, and initial architecture decisions.",
        "state": "open"
    },
    {
        "title": "M2 - N1 Architektur Finalisierung",
        "description": "Finalize N1 (Paper Trading) architecture. Complete system design, service boundaries, event flows, and database schema. Ready for implementation phase.",
        "state": "open"
    },
    {
        "title": "M3 - Risk-Layer Hardening & Guards",
        "description": "Implement and test all 7 risk validation layers: Data Quality, Position Limits, Daily Drawdown, Total Exposure, Circuit Breaker, Spread Check, Timeout Check. Achieve 100% coverage.",
        "state": "open"
    },
    {
        "title": "M4 - Event-Driven Core (Redis Pub/Sub)",
        "description": "Build event-driven message bus using Redis Pub/Sub. Implement all event types (market_data, signals, orders, order_results, alerts) with proper routing and error handling.",
        "state": "open"
    },
    {
        "title": "M5 - Persistenz + Analytics Layer",
        "description": "Complete PostgreSQL integration with 5 core tables (signals, orders, trades, positions, portfolio_snapshots). Implement analytics queries and reporting capabilities.",
        "state": "open"
    },
    {
        "title": "M6 - Dockerized Runtime (Local Environment)",
        "description": "Fully containerized development environment with docker-compose. All 8 services running healthy: Redis, PostgreSQL, Signal Engine, Risk Manager, Execution Service, WebSocket Screener, Grafana, Prometheus.",
        "state": "open"
    },
    {
        "title": "M7 - Initial Live-Test (MEXC Testnet)",
        "description": "First live integration with MEXC Testnet. Paper trading with real market data. Performance validation and system stability testing.",
        "state": "open"
    },
    {
        "title": "M8 - Production Hardening & Security Review",
        "description": "Security audit, penetration testing, secret management hardening. Performance optimization and load testing. Final production readiness review.",
        "state": "open"
    },
    {
        "title": "M9 - Production Release 1.0",
        "description": "Official production release with full documentation, deployment playbooks, monitoring dashboards, and 24/7 operational procedures. System ready for live trading.",
        "state": "open"
    }
]


def create_milestone(milestone: dict) -> bool:
    """Create a single milestone via GitHub REST API"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/milestones"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    data = json.dumps(milestone).encode('utf-8')

    try:
        request = Request(url, data=data, headers=headers, method='POST')
        with urlopen(request) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(f"✅ Created: {milestone['title']}")
            return True
    except HTTPError as e:
        error_body = e.read().decode('utf-8')
        error_data = json.loads(error_body)

        # Check if milestone already exists
        if "already_exists" in error_data.get("errors", [{}])[0].get("code", ""):
            print(f"⚠️  Already exists: {milestone['title']}")
            return True
        else:
            print(f"❌ Error creating {milestone['title']}: {error_data.get('message', str(e))}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error for {milestone['title']}: {str(e)}")
        return False


def main():
    """Main function to create all milestones"""
    print("🚀 Creating GitHub Milestones for Claire de Binaire...\n")

    # Check for GitHub token
    if not GITHUB_TOKEN:
        print("❌ ERROR: GITHUB_TOKEN environment variable not set!")
        print("\nTo create a token:")
        print("1. Go to: https://github.com/settings/tokens/new")
        print("2. Give it a name: 'Claire Milestones'")
        print("3. Select scopes: 'repo' (full repository access)")
        print("4. Generate token")
        print("5. Export it: export GITHUB_TOKEN=your_token_here")
        sys.exit(1)

    # Create all milestones
    success_count = 0
    for milestone in MILESTONES:
        if create_milestone(milestone):
            success_count += 1

    print(f"\n✅ Successfully created/verified {success_count}/{len(MILESTONES)} milestones!")
    print("\nVerify at:")
    print(f"https://github.com/{REPO_OWNER}/{REPO_NAME}/milestones")


if __name__ == "__main__":
    main()
