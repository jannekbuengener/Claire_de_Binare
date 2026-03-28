# ARCHITECTURE_MAP - Claire de Binare

**Version:** 2.0
**Erstellt:** 2025-12-28
**Letzte Aktualisierung:** 2026-03-28 (Drift-Fix #1304 — auf BLUE/RED-Realität gebracht)
**Status:** Kanonisch
**Pruefintervall:** Bei jedem Session-Start

**Primärquellen:**
- `infrastructure/compose/compose.blue.yml`
- `infrastructure/compose/compose.red.yml`
- `infrastructure/compose/logging.yml`
- `knowledge/governance/SERVICE_CATALOG.md`

---

## 1. System Overview

Claire de Binare ist ein **event-getriebenes Krypto-Trading-System** mit:
- Redis Pub/Sub und Streams für Inter-Service-Kommunikation
- PostgreSQL für Event-Persistenz
- Docker Compose für Orchestrierung (BLUE/RED-Split)
- Paper Trading als Default-Modus (`MOCK_TRADING=true`; Live Trading erfordert explizites Human Gate)

**Operatives Service-Inventar:** `knowledge/governance/SERVICE_CATALOG.md`

---

## 2. BLUE/RED Stack-Split

### BLUE — Core Trading (compose.blue.yml)

Always-on. Voraussetzung für Trading-Betrieb.

| Service | Container | Port | Funktion |
|---------|-----------|------|----------|
| PostgreSQL | cdb_postgres | 5432 | Persistenz |
| Redis | cdb_redis | 6379 | Cache, Pub/Sub, Streams |
| Market | cdb_market | 8009 | Konsumiert `market_data`; schreibt `market_state:{symbol}` (post-Cutover #1201) |
| Candles | cdb_candles | 8007 | Konsumiert `market_data`; aggregiert → `stream.candles_1m` |
| Regime | cdb_regime | 8008 | Konsumiert `stream.candles_1m`; klassifiziert Marktregime → `stream.regime_signals` |
| Allocation | cdb_allocation | 8006 | Konsumiert `stream.regime_signals`; mappt → `stream.allocation_decisions` |
| Risk | cdb_risk | 8002 | Zentrales Gate; liest Streams + `market_state`; publiziert `orders`; hält Kill-Switch |
| Execution | cdb_execution | 8003 | Konsumiert `orders`; publiziert `order_results` (`MOCK_TRADING=true` per Default) |
| DB Writer | cdb_db_writer | — | Konsumiert `signals`, `orders`, `order_results`, `portfolio_snapshots` → PostgreSQL |
| Paper Runner | cdb_paper_runner | 8004 | Paper-Trading-Runner; publiziert `portfolio_snapshots` stündlich |

### RED — Signal Generation + Monitoring (compose.red.yml)

Restartbar ohne BLUE zu beeinflussen.

| Service | Container | Port | Funktion |
|---------|-----------|------|----------|
| WebSocket | cdb_ws | 8000 | MEXC-Marktdaten-Feed → publiziert `market_data` |
| Signal | cdb_signal | 8005 | Konsumiert `market_data`; publiziert `signals` |
| Prometheus | cdb_prometheus | 19090 | Metrics-Collection |
| Grafana | cdb_grafana | 3000 | Dashboards, Alerting |
| Postgres Exporter | cdb_postgres_exporter | 9187 | PostgreSQL-Metriken für Prometheus |
| Redis Exporter | cdb_redis_exporter | 9121 | Redis-Metriken für Prometheus |
| cAdvisor | cdb_cadvisor | — | Container-Ressourcenmetriken |
| Reports | cdb_reports | — | Tägliche Order-Summary per E-Mail (cron-Prozess) |

### Optional — Logging-Stack (logging.yml)

Separat startbar.

| Service | Container | Funktion |
|---------|-----------|----------|
| Alertmanager | cdb_alertmanager | Alert-Routing |
| Loki | cdb_loki | Log-Aggregation |
| Promtail | cdb_promtail | Log-Shipping |

---

## 3. Core Pipeline (Datenfluss)

```
cdb_ws
  │
  └─→ market_data (pub/sub)
         │
         ├─→ cdb_market
         │      └─→ market_state:{symbol}  (post-Cutover #1201;
         │               MARKET_STATE_KEY_PREFIX=market_state in compose.blue.yml;
         │               cdb_candles schreibt market_state nicht mehr:
         │               CANDLE_WRITE_MARKET_STATE=false)
         │
         ├─→ cdb_candles
         │      └─→ stream.candles_1m
         │               └─→ cdb_regime
         │                      └─→ stream.regime_signals
         │                               ├─→ cdb_allocation
         │                               │      └─→ stream.allocation_decisions
         │                               └─→ cdb_risk (liest Regime + Allocation + market_state)
         │
         └─→ cdb_signal
                └─→ signals (pub/sub)
                         ├─→ cdb_risk
                         │      └─→ orders (pub/sub)
                         │               ├─→ cdb_execution
                         │               │      └─→ order_results (pub/sub)
                         │               │               ├─→ cdb_risk
                         │               │               └─→ cdb_db_writer → PostgreSQL
                         │               └─→ cdb_db_writer → PostgreSQL
                         └─→ cdb_db_writer → PostgreSQL

cdb_paper_runner → portfolio_snapshots (pub/sub) → cdb_db_writer → PostgreSQL
```

---

## 4. Redis Channels / Streams

Nur belegte Einträge. Publisher und Subscriber aus Service-Config und Service-Code verifiziert.

| Channel / Stream | Typ | Publisher | Subscriber(s) |
|-----------------|-----|-----------|---------------|
| `market_data` | pub/sub | cdb_ws | cdb_market, cdb_candles, cdb_signal |
| `market_state:{symbol}` | Redis-Key | cdb_market | cdb_risk |
| `stream.candles_1m` | stream | cdb_candles | cdb_regime |
| `stream.regime_signals` | stream | cdb_regime | cdb_allocation, cdb_risk |
| `stream.allocation_decisions` | stream | cdb_allocation | cdb_risk |
| `signals` | pub/sub | cdb_signal | cdb_risk, cdb_db_writer |
| `orders` | pub/sub | cdb_risk | cdb_execution, cdb_db_writer |
| `order_results` | pub/sub | cdb_execution | cdb_risk, cdb_db_writer |
| `portfolio_snapshots` | pub/sub | cdb_paper_runner | cdb_db_writer |
| `alerts` | pub/sub | cdb_risk | — (Monitoring) |
| `stream.bot_shutdown` | stream | cdb_risk | cdb_execution |

Hinweis: Weitere interne Streams (`stream.signals`, `stream.orders`, `stream.orders_blocked`, `stream.fills`) sind in Service-Configs referenziert, aber nicht vollständig kartiert. Sie sind hier weggelassen, bis ihre Subscriber verifiziert sind.

---

## 5. Compose-Architektur

### Aktive Operator-Runtime (kanonisch)

```
compose.blue.yml    → BLUE Stack: Core Trading
compose.red.yml     → RED Stack: Signal + Monitoring
logging.yml         → Optional: Alertmanager + Loki + Promtail
```

Startbefehl (kanonischer PowerShell-Einstieg):
```powershell
.\tools\cdb.ps1 runtime up
```

Oder direkt:
```bash
docker network create cdb_network
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
```

### CI-Lab-Baseline (431B)

```
base.yml + test.yml → kanonische CI-Lab-Baseline für isolierte Test-/E2E-Labs
```

### Legacy/Sekundärpfad

`base.yml + dev.yml` — sekundärer Dev-/Kompatibilitätspfad; kein kanonischer Operator-Runtime-Stack.

---

## 6. Invariants (nicht verhandelbar)

1. **Paper Trading Default**: `MOCK_TRADING=true`; Live Trading erfordert explizites Human Gate
2. **Event Sourcing**: Alle State-Änderungen über Events (Replay-fähig)
3. **Circuit Breaker**: Risk Service gated alle Order-Ausführung
4. **Determinismus**: Reproduzierbare Ergebnisse via Event Replay
5. **Localhost Binding**: Alle Ports auf `127.0.0.1` (keine externe Exposition)
6. **Kill-Switch**: Shared State-Datei zwischen cdb_risk und cdb_execution (Volume `kill_switch_state`)

---

## 7. Verification Commands

```powershell
# Kanonischer Stack-Start
.\tools\cdb.ps1 runtime up

# Stack verifizieren
.\tools\cdb.ps1 stack verify

# Smoke-Test (BLUE core path)
.\tools\cdb.ps1 runtime smoke

# Schnellcheck Container-Status
docker ps --filter "name=cdb_" --format "table {{.Names}}\t{{.Status}}"
```

Erwarteter Status (BLUE healthy):
```
cdb_postgres      Up X minutes (healthy)
cdb_redis         Up X minutes (healthy)
cdb_market        Up X minutes (healthy)
cdb_candles       Up X minutes (healthy)
cdb_regime        Up X minutes (healthy)
cdb_allocation    Up X minutes (healthy)
cdb_risk          Up X minutes
cdb_execution     Up X minutes
cdb_db_writer     Up X minutes (healthy)
cdb_paper_runner  Up X minutes (healthy)
```

---

## Changelog

| Datum | Änderung | Durch |
|-------|----------|-------|
| 2025-12-28 | Initiale Erstellung via Context Build Sprint | Claude (Orchestrator) |
| 2026-03-28 | Vollständiges Update auf BLUE/RED-Realität (#1304): cdb_candles ergänzt; cdb_market/regime/allocation als AKTIV mit Port korrigiert; Core-Pipeline-Diagramm auf echte Redis-Channel-Namen und candles→regime→allocation→risk-Flow aktualisiert; market_state-Ownership post-Cutover #1201 dokumentiert; Redis-Tabelle auf belegte Einträge beschränkt; RED-Stack komplett (Reports, Exporter, cAdvisor, Logging-Stack); Compose-Layer auf BLUE/RED umgestellt; alte Drifts-Sektion und veraltete Stack-Start-Referenzen entfernt | Claude |
