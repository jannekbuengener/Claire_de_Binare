#!/bin/bash
# create_milestones.sh - Erstellt 9 GitHub Milestones für Claire de Binare
# Nutzt GitHub REST API da gh CLI milestone-Befehl nicht verfügbar ist

set -e

echo "🚀 Erstelle GitHub Milestones für Claire de Binare..."
echo ""

# M1 - Foundation & Governance Setup
echo "Creating M1 - Foundation & Governance Setup..."
gh api repos/:owner/:repo/milestones --method POST --field title="M1 - Foundation & Governance Setup" --field description="Establish project foundation with documentation, governance structures, and development standards. Includes KODEX, ADRs, and initial architecture decisions." --field state="open"

# M2 - N1 Architektur Finalisierung
echo "Creating M2 - N1 Architektur Finalisierung..."
gh api repos/:owner/:repo/milestones --method POST --field title="M2 - N1 Architektur Finalisierung" --field description="Finalize N1 (Paper Trading) architecture. Complete system design, service boundaries, event flows, and database schema. Ready for implementation phase." --field state="open"

# M3 - Risk-Layer Hardening & Guards
echo "Creating M3 - Risk-Layer Hardening & Guards..."
gh api repos/:owner/:repo/milestones --method POST --field title="M3 - Risk-Layer Hardening & Guards" --field description="Implement and test all 7 risk validation layers: Data Quality, Position Limits, Daily Drawdown, Total Exposure, Circuit Breaker, Spread Check, Timeout Check. Achieve 100% coverage." --field state="open"

# M4 - Event-Driven Core (Redis Pub/Sub)
echo "Creating M4 - Event-Driven Core (Redis Pub/Sub)..."
gh api repos/:owner/:repo/milestones --method POST --field title="M4 - Event-Driven Core (Redis Pub/Sub)" --field description="Build event-driven message bus using Redis Pub/Sub. Implement all event types (market_data, signals, orders, order_results, alerts) with proper routing and error handling." --field state="open"

# M5 - Persistenz + Analytics Layer
echo "Creating M5 - Persistenz + Analytics Layer..."
gh api repos/:owner/:repo/milestones --method POST --field title="M5 - Persistenz + Analytics Layer" --field description="Complete PostgreSQL integration with 5 core tables (signals, orders, trades, positions, portfolio_snapshots). Implement analytics queries and reporting capabilities." --field state="open"

# M6 - Dockerized Runtime (Local Environment)
echo "Creating M6 - Dockerized Runtime (Local Environment)..."
gh api repos/:owner/:repo/milestones --method POST --field title="M6 - Dockerized Runtime (Local Environment)" --field description="Fully containerized development environment with docker-compose. All 8 services running healthy: Redis, PostgreSQL, Signal Engine, Risk Manager, Execution Service, WebSocket Screener, Grafana, Prometheus." --field state="open"

# M7 - Initial Live-Test (MEXC Testnet)
echo "Creating M7 - Initial Live-Test (MEXC Testnet)..."
gh api repos/:owner/:repo/milestones --method POST --field title="M7 - Initial Live-Test (MEXC Testnet)" --field description="First live integration with MEXC Testnet. Paper trading with real market data. Performance validation and system stability testing." --field state="open"

# M8 - Production Hardening & Security Review
echo "Creating M8 - Production Hardening & Security Review..."
gh api repos/:owner/:repo/milestones --method POST --field title="M8 - Production Hardening & Security Review" --field description="Security audit, penetration testing, secret management hardening. Performance optimization and load testing. Final production readiness review." --field state="open"

# M9 - Production Release 1.0
echo "Creating M9 - Production Release 1.0..."
gh api repos/:owner/:repo/milestones --method POST --field title="M9 - Production Release 1.0" --field description="Official production release with full documentation, deployment playbooks, monitoring dashboards, and 24/7 operational procedures. System ready for live trading." --field state="open"

echo ""
echo "✅ Alle 9 Milestones erfolgreich erstellt!"
echo ""
echo "Prüfe mit: gh api repos/:owner/:repo/milestones"
