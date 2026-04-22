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
| **Market** | cdb_market | 8009 | services/market/ | **AKTIV** | market_state:{symbol} Owner (Issue #1201); Redis retry/reconnect bis verfügbar, /health fail-closed; Email-Alerter ohne Empfaenger-Klartext-Logging |
| **Candles** | cdb_candles | 8007 | services/candles/ | **AKTIV** | Tick→1-min Candle Aggregation |
| **Regime** | cdb_regime | 8008 | services/regime/ | **AKTIV** | ADX/ATR Regime Classification |
| **Allocation** | cdb_allocation | 8006 | services/allocation/ | **AKTIV** | Regime→Allocation Mapping |
| **Risk** | cdb_risk | 8002 | services/risk/ | **AKTIV** | Risk Gate, Circuit Breaker, Kill-Switch; `/kill-switch` Fehlerantworten fail-closed ohne Exception-Details |
| **Execution** | cdb_execution | 8003 | services/execution/ | **AKTIV** | Order Execution (MOCK_TRADING=true default); `/orders` Fehlerantworten nur mit sicherem Fehlercode |
| **DB Writer** | cdb_db_writer | — | services/db_writer/ | **AKTIV** | Redis→PostgreSQL Persistenz; `db_writer.py` schreibt `stream.candles_1m` in `candles_1m` (Postgres), `candle_normalizer.py` normalisiert die Stream-Payloads auf dem Write-Pfad (PR #1856) |
| **Paper Runner** | cdb_paper_runner | 8004 | tools/paper_trading/ | **AKTIV** | Paper Trading Orchestrator |

### RED Stack (compose.red.yml) — Signal + Monitoring, failure-isolated from BLUE

| Service | Container | Port | Code | Status | Funktion |
|---------|-----------|------|------|--------|----------|
| **WebSocket** | cdb_ws | 8000 | services/ws/ | **AKTIV** | MEXC Market Data Stream (protobuf) |
| **Signal** | cdb_signal | 8005 (Runtime) | services/signal/ | **AKTIV** | Signal Generation (`primary_breakout_v1` default, `momentum_builtin` statische Adapter-Grenze) |
| **Reports** | cdb_reports | — | services/reports/ | **AKTIV** | Daily Order Summary + Email |

Hinweis: Der Config-Default fuer `SIGNAL_PORT` liegt in `services/signal/config.py` bei `8001`; im kanonischen RED-Runtime-Pfad wird fuer `cdb_signal` in `infrastructure/compose/compose.red.yml` explizit `SIGNAL_PORT=8005` gesetzt.

---

## Core Libraries (nicht runtime-services)

### Replay Infrastructure (LR-021, PR #1808)

**Pfad:** `core/replay/`, `services/validation/` (reporter + CLI)

**Funktion:** Deterministic shadow replay stack für accelerated backtesting, validation und gate evaluation offline, ohne live/paper/Redis-Runtime-Integration; ARVP §4.2 datasets können über `DBBackedDatasetProvider` aus `candles_1m` (Postgres) bezogen werden.

| Module/Component | Code-Pfad | Status | Beschreibung |
|---|---|---|---|
| **Replay Contracts** | `core/replay/replay_contracts.py` | **AKTIV** (PR #1808) | Frozen dataclasses für deterministic input/output tracking |
| **Replay Determinism** | `core/replay/determinism.py` | **AKTIV** (PR #1808) | Canonical JSON hashing, integrity verification |
| **Replay Clock Context** | `core/replay/clock_context.py` | **AKTIV** (PR #1808) | Deterministic, wall-clock-free time handling |
| **Replay Execution** | `core/replay/execution.py` | **AKTIV** (PR #1808) | Envelope chain emission, order/fill wrapping |
| **Deterministic Loop** | `core/replay/deterministic_loop.py` | **AKTIV** (PR #1808) | Tick-by-tick replay orchestration mit integrity gate |
| **Envelopes** | `core/replay/envelopes.py` | **AKTIV** (PR #1808) | Decision/Order/Fill envelope types + replay metadata |
| **Replay Reporter** | `services/validation/replay_reporter.py` | **AKTIV** (PR #1808) | Artifact bundle writer (report.json, manifest.json, audit.log) |
| **Replay CLI** | `services/validation/strategy_replay_runner.py` | **AKTIV** (PR #1808) | Thin operator entry-point, config validation, exit codes 0/1/2 |
| **Dataset Spec** | `core/replay/dataset_spec.py` | **AKTIV** (PR #1856) | Frozen request-spec für historische Replay-Datasets (ARVP §4.2); Fingerprint via canonical_hash |
| **Dataset Provider** | `core/replay/dataset_provider.py` | **AKTIV** (PR #1856) | FileBackedDatasetProvider (JSON/JSONL) + DBBackedDatasetProvider (candles_1m Postgres); ARVP §4.2 |

**Interne Abhängigkeiten:** Nutzen `core/replay/canonical_json.py` (deterministic serialization), `core/replay/envelopes.py` (envelope tracking).

**Externe Abhängigkeiten:** `core/domain/` (models, events), `core/clients/` (MEXC API), `core/indicators/` (technical indicators), `core/contracts/` (decision contracts).

**Tests:** 453 unit tests (core/replay/ + services/validation/ replay-specific tests), alle grün.

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
| **Prometheus** | cdb_prometheus | prom/prometheus:v3.11.2 | 19090→9090 | **AKTIV** | Metrics Collection |
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
| 2026-04-11 | Signal-Port-Semantik präzisiert: Config-Default `SIGNAL_PORT=8001`, kanonischer Runtime-Port `8005` via `compose.red.yml` | Codex |
| 2026-04-11 | Signal/Risk Runtime-Drift bereinigt: Signal-Strategie-/Stream-Semantik und Risk-Input-/Metric-Semantik auf current-main präzisiert | Codex |
| 2026-04-18 | PR #1752 Nachzug: Market Email-Alerter-Init ohne Empfaenger-Klartext-Logging in Katalogfunktion nachgezogen | Codex |
| 2026-04-18 | PR #1755 Nachzug: Risk-/Execution-Fehlerantworten und Kill-Switch-Fallback auf stacktrace-freie Fehlercodes/Safemessages dokumentiert | Codex |
| 2026-04-19 | Prometheus-Image-Version nachgezogen: v3.10.0 → v3.11.2 (PR #1767, Issue #1771); enger Katalog-Nachzug gegen current-main | Codex |
| 2026-04-20 | PR #1808 Nachzug: LR-021 deterministic replay infrastructure (core/replay/ + services/validation/) als Core Libraries dokumentiert; 6 Modules + 2 Components + 453 Tests (Issue #1809) | Codex |
| 2026-04-22 | PR #1856 Nachzug: ARVP §4.2 DatasetSpec + DatasetProvider (FileBackedDatasetProvider + DBBackedDatasetProvider) in Core Libraries ergänzt; DB-Writer Candle-Persistence (candle_normalizer.py → candles_1m) nachgezogen (Issue #1857) | Codex |
