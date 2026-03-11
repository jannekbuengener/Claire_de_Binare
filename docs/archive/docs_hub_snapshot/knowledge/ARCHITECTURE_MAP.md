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

### Services (AKTIV)

| Service | Container | Port | Funktion |
|---------|-----------|------|----------|
| WebSocket | cdb_ws | 8000 | Market Data Stream |
| Signal | cdb_signal | 8005 | Signal Generation |
| Risk | cdb_risk | 8002 | Risk Management, Circuit Breaker |
| Execution | cdb_execution | 8003 | Order Execution |
| DB Writer | cdb_db_writer | - | Event Persistenz |
| Paper Runner | cdb_paper_runner | 8004 | Paper Trading Orchestrator |

### Infrastruktur (AKTIV)

| Service | Container | Port | Funktion |
|---------|-----------|------|----------|
| Redis | cdb_redis | 6379 | Cache, Pub/Sub |
| PostgreSQL | cdb_postgres | 5432 | Persistenz |
| Prometheus | cdb_prometheus | 19090 | Metrics |
| Grafana | cdb_grafana | 3000 | Dashboards |

### Optional (Logging Stack)

| Service | Container | Aktivierung |
|---------|-----------|-------------|
| Loki | cdb_loki | `-Logging` Flag |
| Promtail | cdb_promtail | `-Logging` Flag |

### Deaktiviert (Code vorhanden)

| Service | Grund | Action Required |
|---------|-------|-----------------|
| cdb_allocation | Fehlende Env-Vars | ALLOCATION_* definieren |
| cdb_regime | Fehlende Env-Vars | REGIME_* definieren |
| cdb_market | Nicht implementiert | service.py verifizieren |

---

## 3. Runtime Reality (IST)

### Verification Command
```powershell
# Stack starten
.\infrastructure\scripts\stack_up.ps1 -Profile dev

# Vollstaendigkeitspruefung
.\infrastructure\scripts\stack_verify.ps1

# Schnellcheck
docker ps --filter "name=cdb_" --format "table {{.Names}}\t{{.Status}}"
```

### Erwarteter Output (healthy)
```
cdb_redis         Up X minutes (healthy)
cdb_postgres      Up X minutes (healthy)
cdb_prometheus    Up X minutes (healthy)
cdb_grafana       Up X minutes (healthy)
cdb_ws            Up X minutes (healthy)
cdb_signal        Up X minutes (healthy)
cdb_risk          Up X minutes
cdb_execution     Up X minutes
cdb_db_writer     Up X minutes (healthy)
cdb_paper_runner  Up X minutes (healthy)
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
base.yml          -> Infrastruktur
  |
dev.yml           -> App-Services + Port-Bindings
  |
logging.yml       -> Loki + Promtail (optional)
  |
tls.yml           -> TLS Encryption (optional)
  |
healthchecks-strict.yml -> Strikte Checks (optional)
  |
network-prod.yml  -> Network Isolation (optional)
```

---

## Changelog

| Datum | Aenderung | Durch |
|-------|-----------|-------|
| 2025-12-28 | Initiale Erstellung via Context Build Sprint | Claude (Orchestrator) |
