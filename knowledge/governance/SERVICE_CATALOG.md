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

### BLUE Stack (core / always-on — compose.blue.yml)

| Service | Container | Code | Port | Status | Funktion |
|---------|-----------|------|------|--------|----------|
| **Market** | cdb_market | services/market/ | 8009 | **AKTIV** | Market state service |
| **Candles** | cdb_candles | services/candles/ | 8007 | **AKTIV** | Candle aggregation |
| **Regime** | cdb_regime | services/regime/ | 8008 | **AKTIV** | Regime classification |
| **Allocation** | cdb_allocation | services/allocation/ | 8006 | **AKTIV** | Allocation control |
| **Risk** | cdb_risk | services/risk/ | 8002 | **AKTIV** | Risk management |
| **Execution** | cdb_execution | services/execution/ | 8003 | **AKTIV** | Order execution |
| **DB Writer** | cdb_db_writer | services/db_writer/ | — | **AKTIV** | PostgreSQL persistence |
| **Paper Runner** | cdb_paper_runner | tools/paper_trading/ | 8004 | **AKTIV** | Paper trading orchestration |

### RED Stack (standardmäßig mit BLUE aktiv; failure-isolated und separat restartbar — compose.red.yml)

BLUE-only ist degradierter Betrieb / Maintenance-Fall, nicht der Sollzustand.

| Service | Container | Code | Port | Status | Funktion |
|---------|-----------|------|------|--------|----------|
| **WebSocket** | cdb_ws | services/ws/ | 8000 | **AKTIV** | Market data ingest |
| **Signal** | cdb_signal | services/signal/ | 8005 | **AKTIV** | Signal generation |

---

## Infrastruktur-Services

### BLUE Stack (compose.blue.yml)

| Service | Container | Port | Status | Funktion |
|---------|-----------|------|--------|----------|
| **Redis** | cdb_redis | 6379 | **AKTIV** | Cache, Pub/Sub |
| **PostgreSQL** | cdb_postgres | 5432 | **AKTIV** | Persistenz |

### RED Stack (compose.red.yml)

| Service | Container | Port | Status | Funktion |
|---------|-----------|------|--------|----------|
| **Prometheus** | cdb_prometheus | 19090 | **AKTIV** | Metrics collection |
| **Grafana** | cdb_grafana | 3000 | **AKTIV** | Dashboards |
| **Postgres Exporter** | cdb_postgres_exporter | 9187 | **AKTIV** | PostgreSQL metrics |
| **Redis Exporter** | cdb_redis_exporter | 9121 | **AKTIV** | Redis metrics |
| **cAdvisor** | cdb_cadvisor | — | **AKTIV** | Container metrics |
| **Reports** | cdb_reports | — | **AKTIV** | Daily order summary |

### Logging-Stack (logging.yml — nicht in compose.red.yml, separat opt-in)

| Service | Container | Layer | Funktion |
|---------|-----------|-------|----------|
| **Loki** | cdb_loki | logging.yml | Log aggregation |
| **Promtail** | cdb_promtail | logging.yml | Log shipping |
| **Alertmanager** | cdb_alertmanager | logging.yml | Alert routing (SMTP) |

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

## Compose Layer Architektur

```
compose.blue.yml  → BLUE core (Redis, Postgres, market, candles, regime, allocation,
                    risk, execution, db_writer, paper_runner)
compose.red.yml   → RED co-run (ws, signal, prometheus, grafana, exporters, reports)
logging.yml       → Logging-Stack opt-in (Loki, Promtail, Alertmanager)
tls.yml           → TLS (opt-in)
healthchecks-strict.yml → Strikte Health Checks (opt-in)
```

---

## Stack-Start Befehl (kanonisch)

```bash
# Einmalig
docker network create cdb_network

# BLUE + RED (Sollbetrieb)
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d

# Oder via Makefile
make docker-up
```

---

## Prüf-Checkliste (bei jedem Stack-Start)

- [ ] Alle AKTIV-Services laufen (`docker ps`)
- [ ] Alle Services "healthy" (keine "unhealthy" oder "starting")
- [ ] Keine unbekannten Container im Stack

---

## Änderungshistorie

| Datum | Änderung | Durch |
|-------|----------|-------|
| 2025-12-28 | Initiale Erstellung nach Governance-Review | Claude |
| 2025-12-28 | GAP identifiziert: Signal Service fehlt in Compose | Claude |
| 2025-12-28 | Signal Service aktiviert: cdb_core → cdb_signal (Port 8005) | Claude |
