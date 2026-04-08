# ARCHITECTURE_MAP - Claire de Binare

**Version:** 1.0
**Erstellt:** 2025-12-28
**Status:** Kanonisch
**Pruefintervall:** Bei jedem Session-Start

---

## 1. System Overview

Claire de Binare ist ein **event-getriebenes Krypto-Trading-System** mit:
- Redis Pub/Sub fuer Inter-Service-Kommunikation
- PostgreSQL fuer Event-Persistenz
- Docker Compose fuer Orchestrierung
- Paper Trading als Default-Modus (Live Trading erfordert explizites Gate)

**Operatives Inventar:** `governance/SERVICE_CATALOG.md` (Working Repo)

---

## 2. Service Map (SOLL)

### Core Pipeline
```
[Market] --> [WS] --> [Signal] --> [Risk] --> [Execution]
   |           |          |          |            |
   v           v          v          v            v
             Redis     Redis      Redis        Redis
             pub/sub   pub/sub    pub/sub      pub/sub
                                    |            |
                                    +-----<------+
                                    (order_results)
                                          |
                                          v
                                    [DB Writer] --> [PostgreSQL]
```

### BLUE Stack (compose.blue.yml) — Core, always-on

| Service | Container | Port | Funktion |
|---------|-----------|------|----------|
| PostgreSQL | cdb_postgres | 5432 | Persistenz |
| Redis | cdb_redis | 6379 | Cache, Pub/Sub, Streams |
| Market | cdb_market | 8009 | market_state:{symbol} Owner |
| Candles | cdb_candles | 8007 | Tick→1-min Candle Aggregation |
| Regime | cdb_regime | 8008 | ADX/ATR Regime Classification |
| Allocation | cdb_allocation | 8006 | Regime→Allocation Mapping |
| Risk | cdb_risk | 8002 | Risk Gate, Circuit Breaker, Kill-Switch |
| Execution | cdb_execution | 8003 | Order Execution (MOCK_TRADING=true) |
| DB Writer | cdb_db_writer | — | Redis→PostgreSQL Persistenz |
| Paper Runner | cdb_paper_runner | 8004 | Paper Trading Orchestrator |

### RED Stack (compose.red.yml) — Signal + Monitoring, failure-isolated

| Service | Container | Port | Funktion |
|---------|-----------|------|----------|
| WebSocket | cdb_ws | 8000 | MEXC Market Data Stream |
| Signal | cdb_signal | 8005 | Signal Generation |
| Prometheus | cdb_prometheus | 19090→9090 | Metrics |
| Grafana | cdb_grafana | 3000 | Dashboards |
| Postgres Exporter | cdb_postgres_exporter | 9187 | PG Metrics |
| Redis Exporter | cdb_redis_exporter | 9121 | Redis Metrics |
| cAdvisor | cdb_cadvisor | — | Container Metrics |
| Reports | cdb_reports | — | Daily Order Summary |

### Logging Overlay (logging.yml) — separates Overlay, nicht Teil des Standard-BLUE/RED-Starts

Aktivierung: `docker compose -f compose.blue.yml -f logging.yml up -d`

| Service | Container | Compose-Datei |
|---------|-----------|---------------|
| Loki | cdb_loki | logging.yml |
| Promtail | cdb_promtail | logging.yml |
| Alertmanager | cdb_alertmanager | logging.yml |

---

## 3. Runtime Reality (IST)

### Verification Command
```bash
# Kanonischer Start
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d

# Oder via PowerShell
.\tools\cdb.ps1 runtime up

# Schnellcheck
docker ps --filter "name=cdb_" --format "table {{.Names}}\t{{.Status}}"
```

### Erwarteter Output (BLUE + RED healthy)
```
cdb_postgres          Up (healthy)
cdb_redis             Up (healthy)
cdb_market            Up (healthy)
cdb_candles           Up (healthy)
cdb_regime            Up (healthy)
cdb_allocation        Up (healthy)
cdb_risk              Up
cdb_execution         Up
cdb_db_writer         Up (healthy)
cdb_paper_runner      Up (healthy)
cdb_ws                Up (healthy)
cdb_signal            Up (healthy)
cdb_prometheus        Up (healthy)
cdb_grafana           Up (healthy)
cdb_postgres_exporter Up (healthy)
cdb_redis_exporter    Up (healthy)
cdb_cadvisor          Up
cdb_reports           Up (healthy)
```

---

## 4. Key Dataflows

### Redis Channels
| Channel | Publisher | Subscriber(s) |
|---------|-----------|---------------|
| market_data | cdb_ws | cdb_market, cdb_candles, cdb_signal, cdb_paper_runner |
| signals | cdb_signal | cdb_risk, cdb_db_writer |
| orders | cdb_risk | cdb_execution, cdb_db_writer |
| order_results | cdb_execution | cdb_risk, cdb_db_writer |
| alerts | cdb_risk | — (kein verifizierter Subscriber; Fire-and-forget) |
| portfolio_snapshots | cdb_paper_runner | cdb_db_writer |

### Event Types
- `SIGNAL_GENERATED` - Handelssignal erzeugt
- `ORDER_PLACED` - Order an Exchange gesendet
- `POSITION_OPENED` - Position eroeffnet

---

## 5. Invariants (nicht verhandelbar)

1. **Paper Trading Default**: Live Trading erfordert explizites Delivery Gate
2. **Event Sourcing**: Alle State-Aenderungen ueber Events (Replay-faehig)
3. **Circuit Breaker**: Risk Service gated alle Order Execution
4. **Determinismus**: Reproduzierbare Ergebnisse via Event Replay
5. **TLS Optional**: Aktivierbar via `-TLS` Flag (Redis + PostgreSQL)
6. **Localhost Binding**: Alle Ports auf 127.0.0.1 (keine externe Exposition)

---

## 6. Known Drifts (zu beheben)

Keine offenen Drifts.

Historisch behoben:
- prod.yml/tls.yml referenzierten `cdb_core` statt `cdb_signal` → behoben
- CLAUDE.md hatte Signal als Port 8001 → korrigiert auf 8005

---

## 7. Compose Layer Referenz (kanonisch)

```
compose.blue.yml   -> BLUE: Data + Control + Core Trading  [kanonisch]
compose.red.yml    -> RED: Signal + Monitoring             [kanonisch]
logging.yml        -> Logging Overlay (Loki + Promtail + Alertmanager) [separates Overlay, nicht Standard-Start]
```

Legacy-Layer (base.yml, dev.yml, tls.yml, etc.) existieren noch, sind nicht mehr kanonisch.

---

## Changelog

| Datum | Aenderung | Durch |
|-------|-----------|-------|
| 2025-12-28 | Initiale Erstellung via Context Build Sprint | Claude (Orchestrator) |
| 2026-03-29 | market_data Subscriber-Liste: cdb_market, cdb_candles, cdb_paper_runner ergaenzt (#1323) | Claude |
| 2026-03-29 | BLUE/RED reconciliation: alle Services nach Compose-Realitaet, Known Drifts bereinigt, Compose-Referenzen aktualisiert (#1302) | Claude |
| 2026-04-01 | Logging Overlay: Aktivierungsspalte auf compose-Datei-Referenz umgestellt (war: -Logging Flag); Compose-Referenzblock präzisiert (#1409) | Claude |
