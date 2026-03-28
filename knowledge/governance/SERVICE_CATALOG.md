# SERVICE_CATALOG.md - Vollständige Service-Inventarisierung

**Erstellt:** 2025-12-28
**Letzte Aktualisierung:** 2026-03-28 (Drift-Fix #1304 — auf BLUE/RED-Realität gebracht)
**Verantwortlich:** Claude (Session Lead)
**Prüfintervall:** Bei jedem Stack-Start, mindestens wöchentlich

**Primärquellen für dieses Dokument:**
- `infrastructure/compose/compose.blue.yml`
- `infrastructure/compose/compose.red.yml`
- `infrastructure/compose/logging.yml`

---

## Status-Definitionen

| Status | Bedeutung |
|--------|-----------|
| **AKTIV** | Service in compose.blue.yml oder compose.red.yml definiert und aktiv deployt |
| **OPTIONAL** | Service vorhanden, nur bei explizitem Start aktiv (z. B. logging.yml) |
| **BEREIT** | Code vollständig, Dockerfile vorhanden, aber nicht in aktivem Compose-Stack |
| **GEPLANT** | Architektur definiert, Implementierung ausstehend |
| **LEGACY** | Deprecated, nicht mehr verwendet |
| **GAP** | Verifizierte Diskrepanz zwischen Code und Deployment |

---

## BLUE Stack — Core Trading Infrastructure

Stets aktiv. Voraussetzung für Trading.

| Service | Container | Port (extern) | Code-Pfad | Funktion |
|---------|-----------|--------------|-----------|----------|
| **PostgreSQL** | cdb_postgres | 5432 | `postgres:15.17-alpine` | Persistenz |
| **Redis** | cdb_redis | 6379 | `redis:7.4.8-alpine` | Cache, Pub/Sub, Streams |
| **Market** | cdb_market | 8009 | `services/market/` | Besitzt `market_state:{symbol}` in Redis (nach Cutover #1201) |
| **Candles** | cdb_candles | 8007 | `services/candles/` | Aggregiert Ticks → 1-min-Candles auf `stream.candles_1m` |
| **Regime** | cdb_regime | 8008 | `services/regime/` | Liest Candles, klassifiziert Marktregime (ADX/ATR) |
| **Allocation** | cdb_allocation | 8006 | `services/allocation/` | Mappt Regime → Allokationsprozentsatz pro Modus |
| **Risk** | cdb_risk | 8002 | `services/risk/` | Zentrales Gate: blockiert Orders wenn `allocation_pct <= 0`; hält Kill-Switch |
| **Execution** | cdb_execution | 8003 | `services/execution/` | Sendet Orders; `MOCK_TRADING=true` per Default |
| **DB Writer** | cdb_db_writer | — | `services/db_writer/` | Persistiert Redis-Stream-Events nach PostgreSQL |
| **Paper Runner** | cdb_paper_runner | 8004 | `tools/paper_trading/` | 14-Tage-Paper-Trading-Runner; publiziert Portfolio-Snapshots stündlich |

---

## RED Stack — Signal Generation + Monitoring

Restartbar ohne BLUE zu beeinflussen.

| Service | Container | Port (extern) | Quelle | Funktion |
|---------|-----------|--------------|--------|----------|
| **WebSocket** | cdb_ws | 8000 | `services/ws/` | MEXC-Marktdaten-Feed (Protobuf) |
| **Signal** | cdb_signal | 8005 | `services/signal/` | Konsumiert Candles/Regime, generiert Trade-Signale |
| **Prometheus** | cdb_prometheus | 19090 | `prom/prometheus:v3.10.0` | Metrics-Collection |
| **Grafana** | cdb_grafana | 3000 | `grafana/grafana:11.4.7-ubuntu` | Dashboards, Alerting |
| **Postgres Exporter** | cdb_postgres_exporter | 9187 | `prometheuscommunity/postgres-exporter:latest` | PostgreSQL-Metriken für Prometheus |
| **Redis Exporter** | cdb_redis_exporter | 9121 | `bitnami/redis-exporter:latest` | Redis-Metriken für Prometheus |
| **cAdvisor** | cdb_cadvisor | — | `gcr.io/cadvisor/cadvisor:v0.49.2` | Container-Ressourcenmetriken |
| **Reports** | cdb_reports | — | `services/reports/` | Tägliche Order-Summary per E-Mail (cron-Prozess) |

---

## Optionaler Logging-Stack (logging.yml)

Separat startbar. Nicht in compose.red.yml enthalten.

| Service | Container | Quelle | Funktion |
|---------|-----------|--------|----------|
| **Alertmanager** | cdb_alertmanager | `prom/alertmanager:v0.27.0` | Alert-Routing (E-Mail, Webhooks) |
| **Loki** | cdb_loki | `grafana/loki:2.9.3` | Log-Aggregation |
| **Promtail** | cdb_promtail | `grafana/promtail:2.9.3` | Log-Shipping zu Loki |

Start: `docker compose -f infrastructure/compose/compose.blue.yml -f infrastructure/compose/compose.red.yml -f infrastructure/compose/logging.yml up -d`

---

## Test-Services (test.yml)

Isolierte Instanzen für CI-Läufe.

| Service | Container | Zweck |
|---------|-----------|-------|
| cdb_redis_test | Redis (Test) | Isolierte Test-DB |
| cdb_postgres_test | PostgreSQL (Test) | Isolierte Test-DB |
| cdb_risk_test | Risk Service (Test) | Integration Tests |
| cdb_execution_test | Execution Service (Test) | Integration Tests |
| cdb_test_runner | pytest Container | Test-Orchestration |

---

## Compose-Architektur

### Aktive Operator-Runtime (kanonisch)

```
compose.blue.yml    → BLUE Stack: Core Trading (Daten + Control + Trading)
compose.red.yml     → RED Stack: Signal Generation + Monitoring
logging.yml         → Optional: Alertmanager + Loki + Promtail
```

Startbefehl (kanonisch):
```powershell
.\tools\cdb.ps1 runtime up
```

Oder direkt:
```bash
docker network create cdb_network
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
```

### CI-Lab-Baseline (431B, isoliert)

```
base.yml + test.yml → kanonische Docker-CI-Lab-Baseline für isolierte Test-/E2E-Labs
```

```bash
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/test.yml up --abort-on-container-exit
```

### Legacy/Sekundärpfad

`base.yml + dev.yml` — sekundärer Dev-/Kompatibilitätspfad; kein kanonischer Operator-Runtime-Stack.

---

## Prüf-Checkliste (bei jedem Stack-Start)

- [ ] Alle BLUE-Services laufen (`docker ps`)
- [ ] PostgreSQL und Redis healthy
- [ ] cdb_market, cdb_candles, cdb_regime, cdb_allocation healthy
- [ ] cdb_risk, cdb_execution gestartet
- [ ] cdb_paper_runner healthy
- [ ] RED-Services nach Bedarf gestartet

---

## Änderungshistorie

| Datum | Änderung | Durch |
|-------|----------|-------|
| 2025-12-28 | Initiale Erstellung nach Governance-Review | Claude |
| 2026-03-28 | Vollständiges Update auf BLUE/RED-Realität (#1304): cdb_candles ergänzt, cdb_market/regime/allocation als AKTIV korrigiert, RED-Stack-Services (Reports, Exporter, cAdvisor) ergänzt, logging.yml-Abschnitt ergänzt, Compose-Architektur auf BLUE/RED umgestellt | Claude |
