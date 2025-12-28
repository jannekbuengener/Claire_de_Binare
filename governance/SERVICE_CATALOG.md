# SERVICE_CATALOG.md - Vollständige Service-Inventarisierung

**Erstellt:** 2025-12-28
**Verantwortlich:** Claude (Session Lead)
**Prüfintervall:** Bei jedem Stack-Start, mindestens wöchentlich

---

## Status-Definitionen

| Status | Bedeutung |
|--------|-----------|
| **AKTIV** | Service läuft in Production/Dev Stack |
| **BEREIT** | Code vollständig, Dockerfile vorhanden, Compose deaktiviert |
| **GEPLANT** | Architektur definiert, Implementierung ausstehend |
| **LEGACY** | Deprecated, wird nicht mehr verwendet |
| **GAP** | Diskrepanz zwischen Code und Deployment |

---

## Applikations-Services

| Service | Container | Code | Dockerfile | Compose | Status | Begründung |
|---------|-----------|------|------------|---------|--------|------------|
| **Core** | cdb_core | core/ | via dev.yml | ✅ aktiv | **AKTIV** | Hauptapplikation, FastAPI Gateway |
| **Risk** | cdb_risk | services/risk/ (11 files, service.py) | ✅ | ✅ aktiv | **AKTIV** | Risk Management, Circuit Breaker |
| **Execution** | cdb_execution | services/execution/ (11 files, service.py) | ✅ | ✅ aktiv | **AKTIV** | Order Execution, MEXC Integration |
| **DB Writer** | cdb_db_writer | services/db_writer/ (db_writer.py) | ✅ | ✅ aktiv | **AKTIV** | PostgreSQL Persistenz |
| **WebSocket** | cdb_ws | services/ws/ (service.py) | ✅ | ✅ aktiv | **AKTIV** | Market Data Stream |
| **Paper Runner** | cdb_paper_runner | tools/paper_trading/ (service.py, 15k lines) | ✅ | ✅ aktiv | **AKTIV** | Paper Trading Orchestrator |
| **Signal** | - | services/signal/ (6 files, 280 LOC service.py) | ✅ | ❌ FEHLT | **GAP** | **KRITISCH: Vollständige Implementierung, kein Compose-Eintrag** |
| **Allocation** | cdb_allocation | services/allocation/ (3 files, 378 LOC) | ✅ | ❌ auskommentiert | **BEREIT** | Deaktiviert: fehlende Env-Vars (ALLOCATION_*) |
| **Regime** | cdb_regime | services/regime/ (4 files, 213 LOC) | ✅ | ❌ auskommentiert | **BEREIT** | Deaktiviert: fehlende Env-Vars (REGIME_*) |
| **Market** | cdb_market | services/market/ (2 files, 82 LOC) | ✅ | ❌ auskommentiert | **BEREIT** | Deaktiviert laut stack_up.ps1: "not implemented" |

---

## Infrastruktur-Services

| Service | Container | Image | Compose | Status | Begründung |
|---------|-----------|-------|---------|--------|------------|
| **Redis** | cdb_redis | redis:7-alpine | ✅ aktiv | **AKTIV** | Cache, Pub/Sub |
| **PostgreSQL** | cdb_postgres | postgres:15-alpine | ✅ aktiv | **AKTIV** | Persistenz |
| **Prometheus** | cdb_prometheus | prom/prometheus:v2.51.0 | ✅ aktiv | **AKTIV** | Metrics Collection |
| **Grafana** | cdb_grafana | grafana/grafana:11.4.0 | ✅ aktiv | **AKTIV** | Dashboards |
| **Loki** | cdb_loki | grafana/loki:2.9.0 | ✅ logging.yml | **AKTIV** | Log Aggregation |
| **Promtail** | cdb_promtail | grafana/promtail:2.9.0 | ✅ logging.yml | **AKTIV** | Log Shipping |

---

## Test-Services (test.yml)

| Service | Container | Zweck |
|---------|-----------|-------|
| cdb_redis_test | Redis für Tests | Isolierte Test-DB |
| cdb_postgres_test | PostgreSQL für Tests | Isolierte Test-DB |
| cdb_risk_test | Risk Service Test | Integration Tests |
| cdb_execution_test | Execution Service Test | Integration Tests |
| cdb_test_runner | pytest Container | Test Orchestration |

---

## GAP-Analyse (KRITISCH)

### 1. Signal Service - NICHT DEPLOYED

**Problem:** `services/signal/` enthält vollständige Implementierung:
- `service.py` (280 LOC) - FastAPI Service
- `market_classifier.py` - Market Regime Classification
- `optimizer.py` - Strategy Optimization
- `models.py` - Data Models
- `config.py` - Configuration
- `Dockerfile` - Build Definition

**Aber:** Kein Eintrag in irgendeiner Compose-Datei gefunden.

**Risiko:** Kernkomponente eines Trading-Systems fehlt im Stack.

**Action Required:**
- [ ] Klären: Warum wurde Signal nie in Compose aufgenommen?
- [ ] Entscheidung: Aktivieren oder explizit als "GEPLANT" markieren?

### 2. Allocation/Regime/Market - BEREIT aber deaktiviert

Diese Services haben vollständigen Code, sind aber in `dev.yml` auskommentiert.

**Begründung laut Code-Kommentare:**
- allocation: "missing env vars"
- regime: "missing env vars"
- market: "not implemented" (widersprüchlich - service.py existiert!)

**Action Required:**
- [ ] Env-Vars für allocation/regime definieren
- [ ] market Status klären (Code existiert!)

---

## Compose Layer Architektur

```
base.yml          → Infrastruktur (Redis, Postgres, Prometheus, Grafana)
  ↓
dev.yml           → Applikations-Services (Core, Risk, Execution, etc.)
  ↓
logging.yml       → Loki + Promtail
  ↓
tls.yml           → TLS Certificates (optional)
  ↓
healthchecks-strict.yml → Strikte Health Checks
  ↓
network-prod.yml  → Production Network Isolation
```

---

## Stack-Start Befehl (vollständig)

```bash
# Development mit Logging
docker compose \
  --env-file ".cdb_local/.secrets/.env.compose" \
  -f infrastructure/compose/base.yml \
  -f infrastructure/compose/dev.yml \
  -f infrastructure/compose/logging.yml \
  up -d

# Production (mit TLS + strict healthchecks)
docker compose \
  --env-file ".cdb_local/.secrets/.env.compose" \
  -f infrastructure/compose/base.yml \
  -f infrastructure/compose/dev.yml \
  -f infrastructure/compose/logging.yml \
  -f infrastructure/compose/tls.yml \
  -f infrastructure/compose/healthchecks-strict.yml \
  up -d
```

---

## Prüf-Checkliste (bei jedem Stack-Start)

- [ ] Alle AKTIV-Services laufen (`docker ps`)
- [ ] Alle Services "healthy" (keine "unhealthy" oder "starting")
- [ ] GAP-Services bewusst nicht gestartet (dokumentiert)
- [ ] BEREIT-Services bewusst deaktiviert (Begründung aktuell)
- [ ] Keine unbekannten Container im Stack

---

## Änderungshistorie

| Datum | Änderung | Durch |
|-------|----------|-------|
| 2025-12-28 | Initiale Erstellung nach Governance-Review | Claude |
| 2025-12-28 | GAP identifiziert: Signal Service fehlt in Compose | Claude |
