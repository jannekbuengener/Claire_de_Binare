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
| Candles | cdb_candles | 8007 | Tick→Candle Aggregation |
| Regime | cdb_regime | 8008 | Marktregime-Klassifikation (ADX/ATR) |
| Allocation | cdb_allocation | 8006 | Regime→Allokations-Mapping |
| Market | cdb_market | 8009 | Market-State Redis-Key Owner (post-#1201) |
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

### Redis Pub/Sub Channels

| Channel | Publisher | Subscriber(s) |
|---------|-----------|---------------|
| `market_data` | cdb_ws (ws/service.py:143) | cdb_candles (candles/service.py:321), cdb_signal (signal/service.py:191), cdb_market (market/service.py:359) |
| `signals` | cdb_signal (signal/service.py:316) | cdb_risk (risk/service.py:758), cdb_db_writer (db_writer.py:278) |
| `orders` | cdb_risk (risk/service.py:1991) | cdb_execution (execution/service.py:224), cdb_db_writer (db_writer.py:278) |
| `order_results` | cdb_execution (execution/service.py:273) | cdb_risk (risk/service.py:762), cdb_db_writer (db_writer.py:278) |
| `alerts` | cdb_risk (risk/service.py:2011) | kein Subscriber im Repo verifiziert |
| `portfolio_snapshots` | cdb_paper_runner (tools/paper_trading/service.py:433-434) | cdb_db_writer (db_writer.py:278) |

### Redis Streams

| Stream | Publisher (XADD) | Consumer (XREAD/XREVRANGE) | Status |
|--------|-----------------|---------------------------|--------|
| `stream.candles_1m` | cdb_candles (candles/service.py:91) | cdb_regime (regime/service.py:198 xread), cdb_market (market/service.py:214 xrevrange) | aktiv |
| `stream.regime_signals` | cdb_regime (regime/service.py:101) | cdb_allocation (allocation/service.py:353 xread, :329 xrevrange bootstrap), cdb_risk (risk/service.py:1278 xread), cdb_market (market/service.py:154 xrevrange), cdb_candles (candles/service.py:129,215 xrevrange) | aktiv |
| `stream.allocation_decisions` | cdb_allocation (allocation/service.py:240) | cdb_risk (risk/service.py:1331 xread, :1304 xrevrange bootstrap) | aktiv |
| `stream.fills` | cdb_execution (execution/service.py:291) | cdb_allocation (allocation/service.py, main loop via config.fills_stream) | aktiv |
| `stream.bot_shutdown` | cdb_risk (risk/service.py:2033) | cdb_execution (execution/service.py:656 xread), cdb_allocation (allocation/service.py, main loop via config.shutdown_stream) | aktiv |
| `stream.signals` | cdb_signal (signal/service.py:318) | kein xread-Consumer im Repo | write-only Audit-Log |
| `stream.orders` | cdb_risk (risk/service.py:1993) | kein xread-Consumer im Repo | write-only Audit-Log |
| `stream.orders_blocked` | cdb_risk (risk/service.py:1659) | kein xread-Consumer im Repo | write-only Audit-Log |

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
| services/signal/README.md Port | README dokumentiert Port 8001, tatsaechlicher Port ist 8005 | LOW |
| CLAUDE.md Dataflow-Terminologie | Nennt `risk_requests`/`approved_orders` statt realer Channel-Namen `signals`/`orders` | LOW |

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
| 2026-03-29 | Section 2 aktive Services ergaenzt (candles/regime/allocation/market); Deaktiviert-Abschnitt entfernt; Section 4 Redis Channels vervollstaendigt, Redis Streams Tabelle hinzugefuegt; Section 6 Known Drifts auf verifizierten IST-Stand (Issue #1307) | Claude (Code) |
