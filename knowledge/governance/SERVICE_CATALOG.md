# SERVICE_CATALOG.md - Vollständige Service-Inventarisierung

**Erstellt:** 2025-12-28
**Verantwortlich:** Claude (Session Lead)
**Prüfintervall:** Bei jedem Stack-Start, mindestens wöchentlich

---

## Status-Definitionen

| Status | Bedeutung |
|--------|-----------|
| **AKTIV** | Service läuft in Production/Dev Stack (compose.blue.yml oder compose.red.yml) |
| **OVERLAY** | Service in separatem Compose-Overlay (z.B. logging.yml), nicht Teil des Standard-BLUE/RED-Starts |
| **BEREIT** | Code vollständig, Dockerfile vorhanden, Compose deaktiviert |
| **GEPLANT** | Architektur definiert, Implementierung ausstehend |
| **LEGACY** | Deprecated, wird nicht mehr verwendet |
| **GAP** | Diskrepanz zwischen Code und Deployment |

---

## Applikations-Services

### BLUE Stack (compose.blue.yml) — Core, always-on

| Service | Container | Port | Code | Status | Funktion |
|---------|-----------|------|------|--------|----------|
| **Market** | cdb_market | 8009 | services/market/ | **AKTIV** | market_state:{symbol} Owner (Issue #1201) |
| **Candles** | cdb_candles | 8007 | services/candles/ | **AKTIV** | Tick→1-min Candle Aggregation |
| **Regime** | cdb_regime | 8008 | services/regime/ | **AKTIV** | ADX/ATR Regime Classification |
| **Allocation** | cdb_allocation | 8006 | services/allocation/ | **AKTIV** | Regime→Allocation Mapping |
| **Risk** | cdb_risk | 8002 | services/risk/ | **AKTIV** | Zentrale Decision-/Run-Mode-/Policy-Grenze (Risk Gate, Circuit Breaker, Kill-Switch) |
| **Execution** | cdb_execution | 8003 | services/execution/ | **AKTIV** | Order Execution ueber statische Adapter-Selektion (`mock_builtin`/`mexc_builtin`) |
| **DB Writer** | cdb_db_writer | — | services/db_writer/ | **AKTIV** | Kanonische Redis→PostgreSQL Persistenz (`signals`/`orders`/`order_results`/`portfolio_snapshots`) |
| **Paper Runner** | cdb_paper_runner | 8004 | tools/paper_trading/ | **AKTIV** | Paper Trading Orchestrator |

### RED Stack (compose.red.yml) — Signal + Monitoring, failure-isolated from BLUE

| Service | Container | Port | Code | Status | Funktion |
|---------|-----------|------|------|--------|----------|
| **WebSocket** | cdb_ws | 8000 | services/ws/ | **AKTIV** | MEXC Market Data Stream (protobuf) |
| **Signal** | cdb_signal | 8005 | services/signal/ | **AKTIV** | Signal Generation mit minimalem `primary_breakout_v1`-Footprint und `momentum_builtin` ueber statische Adapter-Grenze |
| **Reports** | cdb_reports | — | services/reports/ | **AKTIV** | Daily Order Summary + Email |

---

## Validation / Replay Surface (current main)

| Surface | Code | Status | Funktion |
|---------|------|--------|----------|
| **Replay Historical Bridge** | core/replay/historical_bridge.py | **BEREIT** | Deterministischer 1m-BTCUSDT Input-Bridge fuer `primary_breakout_v1` |
| **Strategy Backtest Runner** | services/validation/strategy_backtest_runner.py | **BEREIT** | Deterministischer Validation-Runner mit schema-basiertem Gate-Report |

Hinweis: Diese Surfaces sind im Code nutzbar, werden aber nicht als eigenstaendige Compose-Services deployed. Sie sind Validation-/Replay-Pfade und keine Runtime-Publisher fuer die Persistenzkanaele des DB Writers.

---

## Service Ownership Boundaries (current main, kanonisch)

- **Signal**: erzeugt Signalkandidaten (`primary_breakout_v1` + `momentum_builtin`) ueber statische, repo-owned Adapterwahl; keine Plugin-Discovery.
- **Execution**: fuehrt nur bereits risk-gegate-te Orders aus; Adapter-Selektion statisch/fail-closed (`EXECUTION_ADAPTER_ID`).
- **Risk**: bleibt zentrale Entscheidungsgrenze fuer Run-Mode, Decision, Thresholds und Policy-Kontext.
- **DB Writer**: bleibt reine Persistenzschicht; keine Vermischung mit Validation- oder Replay-Gating.
- **Replay/Validation**: historischer Bridge + Backtest-Runner als separater deterministischer Validationspfad.
- **Unit-/Scale-Canon**: aktive Surfaces nutzen Prozentpunkt-Semantik fuer die betroffenen Return-/Pct- und Schwellenfelder (`3.0 == 3%`).

---

## Infrastruktur-Services

### BLUE Stack (compose.blue.yml)

| Service | Container | Image | Port | Status | Funktion |
|---------|-----------|-------|------|--------|----------|
| **PostgreSQL** | cdb_postgres | postgres:15.17-alpine | 5432 | **AKTIV** | Persistenz |
| **Redis** | cdb_redis | redis:7.4.8-alpine | 6379 | **AKTIV** | Cache, Pub/Sub, Streams |

### RED Stack (compose.red.yml) — Monitoring

| Service | Container | Image | Port | Status | Funktion |
|---------|-----------|-------|------|--------|----------|
| **Prometheus** | cdb_prometheus | prom/prometheus:v3.10.0 | 19090→9090 | **AKTIV** | Metrics Collection |
| **Grafana** | cdb_grafana | grafana/grafana:11.4.7 | 3000 | **AKTIV** | Dashboards |
| **Postgres Exporter** | cdb_postgres_exporter | prometheuscommunity/postgres-exporter | 9187 | **AKTIV** | PG Metrics |
| **Redis Exporter** | cdb_redis_exporter | bitnami/redis-exporter | 9121 | **AKTIV** | Redis Metrics |
| **cAdvisor** | cdb_cadvisor | gcr.io/cadvisor/cadvisor:v0.49.2 | — | **AKTIV** | Container Metrics |

### Logging Overlay (logging.yml) — separates Overlay, nicht Teil des Standard-BLUE/RED-Starts

Aktivierung: `docker compose -f infrastructure/compose/compose.blue.yml -f infrastructure/compose/logging.yml up -d`

| Service | Container | Image | Status | Funktion |
|---------|-----------|-------|--------|----------|
| **Loki** | cdb_loki | grafana/loki:2.9.3 | **OVERLAY** | Log Aggregation |
| **Promtail** | cdb_promtail | grafana/promtail:2.9.3 | **OVERLAY** | Log Shipping |
| **Alertmanager** | cdb_alertmanager | prom/alertmanager:v0.27.0 | **OVERLAY** | Alert Routing + Email |

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

## GAP-Analyse

### Aktuell keine kritischen GAPs

Alle Services aus compose.blue.yml und compose.red.yml sind AKTIV und vollständig konfiguriert.

### Historisch (behoben)

- **2025-12-28:** Signal Service war als `cdb_core` fehlbenannt → umbenannt zu `cdb_signal` (Port 8005)
- **~März 2026:** allocation, regime, market waren in dev.yml auskommentiert → in compose.blue.yml aktiv mit Env-Vars und Healthchecks
- **~März 2026:** BLUE/RED-Split eingeführt → base.yml/dev.yml-Kette durch compose.blue.yml + compose.red.yml ersetzt

---

## Compose-Architektur (kanonisch seit BLUE/RED-Split)

```
compose.blue.yml   → BLUE: Data Layer + Control Layer + Core Trading  [kanonisch]
compose.red.yml    → RED: Signal Generation + Monitoring               [kanonisch]
logging.yml        → Logging Overlay (Loki + Promtail + Alertmanager)  [separates Overlay, nicht Standard-Start]
```

Legacy-Layer (base.yml, dev.yml, tls.yml, etc.) existieren noch im Repo, sind aber nicht mehr kanonisch für den Betrieb.

---

## Stack-Start Befehl (kanonisch)

```bash
# Netzwerk (einmalig)
docker network create cdb_network

# BLUE + RED starten
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d

# PowerShell Front Door
.\tools\cdb.ps1 runtime up
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
| 2025-12-28 | Signal Service aktiviert: cdb_core → cdb_signal (Port 8005) | Claude |
| 2026-03-29 | BLUE/RED-Split reconciliation: market/candles/regime/allocation→AKTIV, Exporter/Reports/Alertmanager ergänzt, Image-Versionen aktualisiert, Compose-Referenzen auf compose.blue/red.yml (#1302) | Claude |
| 2026-04-01 | Logging Overlay: Status AKTIV→OVERLAY für Loki/Promtail/Alertmanager; Status-Definition OVERLAY ergänzt; Aktivierungsbefehl explizit; Compose-Architektur-Notation präzisiert (#1409) | Claude |
| 2026-04-11 | Strategy-v1 Drift-Batch nach #1598/#1600/#1602/#1613: Service-Boundaries fuer Signal/Execution/Risk/DB Writer sowie Replay-/Validation-Surfaces current-main-wahr nachgezogen | Codex |
