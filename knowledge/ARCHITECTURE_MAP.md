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

### BLUE Stack — core / always-on (compose.blue.yml)

| Service | Container | Port | Funktion |
|---------|-----------|------|----------|
| Redis | cdb_redis | 6379 | Cache, Pub/Sub |
| PostgreSQL | cdb_postgres | 5432 | Persistenz |
| Market | cdb_market | 8009 | Market state service |
| Candles | cdb_candles | 8007 | Candle aggregation |
| Regime | cdb_regime | 8008 | Regime classification |
| Allocation | cdb_allocation | 8006 | Allocation control |
| Risk | cdb_risk | 8002 | Risk management |
| Execution | cdb_execution | 8003 | Order execution |
| DB Writer | cdb_db_writer | — | PostgreSQL persistence |
| Paper Runner | cdb_paper_runner | 8004 | Paper trading orchestration |

### RED Stack — standardmäßig mit BLUE aktiv; failure-isolated (compose.red.yml)

BLUE-only ist degradierter Betrieb / Maintenance-Fall, nicht der Sollzustand.

| Service | Container | Port | Funktion |
|---------|-----------|------|----------|
| WebSocket | cdb_ws | 8000 | Market data ingest |
| Signal | cdb_signal | 8005 | Signal generation |
| Prometheus | cdb_prometheus | 19090 | Metrics |
| Grafana | cdb_grafana | 3000 | Dashboards |
| Postgres Exporter | cdb_postgres_exporter | 9187 | PostgreSQL metrics |
| Redis Exporter | cdb_redis_exporter | 9121 | Redis metrics |
| cAdvisor | cdb_cadvisor | — | Container metrics |
| Reports | cdb_reports | — | Daily order summary |

### Logging-Stack — separat opt-in (logging.yml)

| Service | Container | Funktion |
|---------|-----------|----------|
| Loki | cdb_loki | Log aggregation |
| Promtail | cdb_promtail | Log shipping |
| Alertmanager | cdb_alertmanager | Alert routing (SMTP) |

---

## 3. Runtime Reality (IST)

### Verification Command
```powershell
# Stack starten (kanonisch)
.\tools\cdb.ps1 runtime up

# Schnellcheck
docker ps --filter "name=cdb_" --format "table {{.Names}}\t{{.Status}}"

# Vollstaendigkeitspruefung
.\tools\cdb.ps1 stack verify
```

### Erwarteter Output (healthy — BLUE + RED Sollbetrieb)
```
cdb_postgres          Up X minutes (healthy)
cdb_redis             Up X minutes (healthy)
cdb_market            Up X minutes (healthy)
cdb_candles           Up X minutes (healthy)
cdb_regime            Up X minutes (healthy)
cdb_allocation        Up X minutes (healthy)
cdb_risk              Up X minutes
cdb_execution         Up X minutes
cdb_db_writer         Up X minutes (healthy)
cdb_paper_runner      Up X minutes (healthy)
cdb_ws                Up X minutes (healthy)
cdb_signal            Up X minutes (healthy)
cdb_prometheus        Up X minutes (healthy)
cdb_grafana           Up X minutes (healthy)
cdb_postgres_exporter Up X minutes (healthy)
cdb_redis_exporter    Up X minutes (healthy)
cdb_cadvisor          Up X minutes
cdb_reports           Up X minutes (healthy)
```

---

## 4. Key Dataflows

### Redis Channels
| Channel | Publisher | Subscriber(s) |
|---------|-----------|---------------|
| market_data | cdb_ws | cdb_signal |
| signals | cdb_signal | cdb_risk, cdb_db_writer |
| orders | cdb_risk | cdb_execution, cdb_db_writer |
| order_results | cdb_execution | cdb_risk, cdb_db_writer |
| alerts | cdb_risk | (Monitoring) |
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

| Drift | Beschreibung | Priority |
|-------|--------------|----------|
| prod.yml Naming | Referenziert `cdb_core` statt `cdb_signal` | HIGH |
| tls.yml Naming | Referenziert `cdb_core` statt `cdb_signal` | HIGH |
| CLAUDE.md Port | Signal als Port 8001 dokumentiert (ist 8005) | MEDIUM |

---

## 7. Compose Layer Referenz

```
compose.blue.yml          -> BLUE core (Pflicht)
compose.red.yml           -> RED co-run (standardmäßig mit BLUE aktiv)
logging.yml               -> Logging-Stack opt-in (Loki, Promtail, Alertmanager)
tls.yml                   -> TLS Encryption (opt-in)
healthchecks-strict.yml   -> Strikte Checks (opt-in)
```

---

## Changelog

| Datum | Aenderung | Durch |
|-------|-----------|-------|
| 2025-12-28 | Initiale Erstellung via Context Build Sprint | Claude (Orchestrator) |
