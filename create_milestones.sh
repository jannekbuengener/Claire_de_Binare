#!/bin/bash
# Script zum Erstellen der Claire de Binaire GitHub Milestones
# Ausführen mit: bash create_milestones.sh

set -e

echo "🎯 Erstelle GitHub Milestones für Claire de Binaire..."
echo ""

# M1 - Foundation & Governance Setup
echo "📋 Erstelle M1 - Foundation & Governance Setup..."
gh milestone create "M1 - Foundation & Governance Setup" \
  --description "Ziel: Projektstruktur, Regeln, Standards und Quality Gates etablieren.

Deliverables:
- Architektur-Kodex finalisiert (KODEX – Claire de Binaire)
- Issue-Templates erstellt (Bug Report, Feature Request, Risk-Event Report, Enhancement)
- Label-System definiert (risk-layer, infra, execution, critical, research, good first issue)
- Branch-Konventionen + Naming-Regeln (ADR-Style)
- CONTRIBUTING.md ergänzt
- Kanonisches Event-Schema als Referenz verlinkt

Definition of Done:
- Alle Templates produktiv im .github/ISSUE_TEMPLATE
- Labels vollständig angelegt
- Roadmap-Matrix mit Themen-Clustern steht"

# M2 - N1 Architektur Finalisierung
echo "🏗️ Erstelle M2 - N1 Architektur Finalisierung..."
gh milestone create "M2 - N1 Architektur Finalisierung" \
  --description "Ziel: Komplette logische Systemarchitektur als Issues abbilden.

Deliverables:
- Issue-Paket: Market Data Ingestion (MDI)
- Issue-Paket: Strategy Engine
- Issue-Paket: Risk Engine (7-Layer)
- Issue-Paket: Execution Simulator
- Issue-Paket: Portfolio State Manager
- Issue-Paket: Logging & Analytics
- Issue-Paket: Event-Validator + Schema-Checker

Definition of Done:
Jedes Modul besitzt:
- 1 Epic-Issue
- 3–10 Sub-Issues
- Klar definierte Acceptance Criteria
- Abhängigkeiten via Issue-Links dokumentiert"

# M3 - Risk-Layer Hardening & Guards
echo "🛡️ Erstelle M3 - Risk-Layer Hardening & Guards..."
gh milestone create "M3 - Risk-Layer Hardening & Guards" \
  --description "Ziel: Alle Risk-Parameter, ENV-Variablen, Konfigs und Validierungs-Workflows.

Deliverables:
- Parameter-Range-Checks
- Test-Suite für alle Guards
- Daily-Drawdown Lock Workflow
- Alert-System (CRITICAL, WARNING)
- Recovery-Logic (Cooldown, Reset)
- Dokumentation: Entscheidungsbaum Risk Engine

Definition of Done:
- Mind. 80% Test-Coverage für Risk-Layer
- Alert-Codes dokumentiert und getestet
- ENV-Ranges maschinell validiert"

# M4 - Event-Driven Core
echo "📡 Erstelle M4 - Event-Driven Core (Redis Pub/Sub)..."
gh milestone create "M4 - Event-Driven Core (Redis Pub/Sub)" \
  --description "Ziel: Vollständiges Event-Gerüst operationalisieren.

Deliverables:
- market_data Flow implementiert
- signals Flow implementiert
- orders Flow implementiert
- order_results Flow implementiert
- alerts Flow implementiert
- Event-Schema-Validator + Contracts-Testing

Definition of Done:
- Alle Topic-Spezifikationen in /docs abgelegt
- Jede Message-Art hat ein eigenes QA-Issue
- Replay-Test auf Basis historischer Candles läuft durch"

# M5 - Persistenz + Analytics Layer
echo "💾 Erstelle M5 - Persistenz + Analytics Layer..."
gh milestone create "M5 - Persistenz + Analytics Layer" \
  --description "Ziel: Datenhaltung, Logging und Backtest-Auswertungen.

Deliverables:
- PostgreSQL-Schema validiert + konsolidiert
- Storage für: Signals, Orders, Trades, RiskEvents, Snapshots
- Backtest-Run-Tracking (Lauf-ID, Params, Ergebnisse)
- Export-Funktionen für Analytics
- Grund-UI für Equity & Drawdown

Definition of Done:
- Persistenz-Tests laufen
- Backtest-Daten vollständig reproduzierbar
- UI zeigt Equity, DD, Trades"

# M6 - Dockerized Runtime
echo "🐳 Erstelle M6 - Dockerized Runtime (Local Environment)..."
gh milestone create "M6 - Dockerized Runtime (Local Environment)" \
  --description "Ziel: Produktionsnahe lokale Umgebung.

Deliverables:
- Docker Compose finalisiert
- Health-Checks für jeden Service
- Grafana Dashboards
- Prometheus Scraping-Regeln
- .env.template final

Definition of Done:
- docker compose up -d → alle Container healthy
- Metriken sichtbar
- Alerts erscheinen in UI"

# M7 - Initial Live-Test
echo "🧪 Erstelle M7 - Initial Live-Test (MEXC Testnet)..."
gh milestone create "M7 - Initial Live-Test (MEXC Testnet)" \
  --description "Ziel: Expeditionelle Phase mit Issues absichern.

Deliverables:
- Testnet-Integration
- Testnet Execution Service
- Testnet Order Reconciliation
- Manual-Override Interface
- Monitoring: Live Trades

Definition of Done:
- 100 Trades im Testnet erfolgreich durchgelaufen
- Keine CRITICAL Alerts
- Vergleich Live-Eingaben ↔ Systemlog konsistent"

# M8 - Production Hardening
echo "🔒 Erstelle M8 - Production Hardening & Security Review..."
gh milestone create "M8 - Production Hardening & Security Review" \
  --description "Ziel: Finale Absicherung vor Produktivbetrieb.

Deliverables:
- Full Security Review (SR-001 bis SR-009)
- Vault- oder Secret-Rotation Workflow
- Production-Compose ohne Mounts
- Logging-Hardening
- Backup-Policies

Definition of Done:
- Security-Score ≥ 95%
- Risk-Level LOW
- Production-Compose → immutable"

# M9 - Production Release 1.0
echo "🚀 Erstelle M9 - Production Release 1.0..."
gh milestone create "M9 - Production Release 1.0" \
  --description "Ziel: Abschluss-Meilenstein.

Deliverables:
- Release Notes
- Fixierte ENV-Parameter
- Systemdiagramme final
- CI/CD-Pipeline
- Documentation Pack (PDF + Markdown)

Definition of Done:
- System läuft 72h stabil
- Alle Backtests + Livetests konsistent
- Documentation Score: 100% vollständig"

echo ""
echo "✅ Alle 9 Milestones erstellt!"
echo ""
echo "📊 Übersicht:"
gh milestone list
