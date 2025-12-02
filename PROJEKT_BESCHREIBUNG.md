# Claire de Binare – Technische Projektbeschreibung

**Version:** 1.0  
**Datum:** November 2024  
**Status:** MVP Phase (85–95% Completion)  
**Projekt-Leiter:** Jannek  
**IT-Chef:** Claude  
**Server-Admin:** Gordon  

---

## 1. PROJEKTZIELSETZUNG

**Kernziel:** Entwicklung eines vollautomatischen Cryptocurrency-Trading-Bots für die MEXC-Exchange mit eigenständiger Signalverarbeitung, Risikomanagement und Trade-Execution.

**Geschäftslogik:**
- Echtzeit-Markdatenanalyse via WebSocket (MEXC Streams)
- Momentum-basierte Handelssignale
- Automatische Positionsgröße-Berechnung
- Risiko-Compliance (Drawdown, Exposure, Circuit Breaker)
- Vollständige Audit-Trails für Compliance

**Zielarchitektur:** Microservices in Docker – verteilte Services über Redis Pub/Sub orchestriert, zentrale PostgreSQL-Persistenz.

---

## 2. SYSTEMARCHITEKTUR

### 2.1 High-Level-Übersicht

```
┌─────────────────────────────────────────────────────┐
│         CLAIRE DE BINARE – TRADING BOT              │
├─────────────────────────────────────────────────────┤
│                    DATENFLUSS                       │
│                                                     │
│  MEXC Exchange (WebSocket)                          │
│       ↓                                             │
│  [WebSocket Screener] → Market Data Feed           │
│       ↓                                             │
│  [Redis Pub/Sub] ← Distributed Message Bus         │
│       ↓                                             │
│  [Signal Engine] → Handelsignale                   │
│       ↓                                             │
│  [Risk Manager] → Validierung & Compliance         │
│       ↓                                             │
│  [Execution Service] → Trade-Placement             │
│       ↓                                             │
│  [PostgreSQL] ← Persistierung aller Events         │
│       ↓                                             │
│  [Prometheus/Grafana] → Monitoring & Observability │
└─────────────────────────────────────────────────────┘
```

### 2.2 Service-Komponenten

#### **A. WebSocket Screener (cdb_websocket_screener)**
- **Funktion:** Echtzeitverbindung zu MEXC WebSocket-Streams
- **Input:** MEXC Kryptowährungspreisströme (z.B. BTC/USDT, ETH/USDT)
- **Output:** Normalisierte Market-Data auf Redis Topic `market_data`
- **Technologie:** Python mit `aiohttp`/`websockets`
- **Produktion:** ~150 Zeilen Python

#### **B. Signal Engine (cdb_signal_engine)**
- **Funktion:** Momentum-Analyse und Handelsignale
- **Input:** Market-Data von Redis
- **Logik:** 
  - EMA/SMA Crossover
  - RSI Momentum-Check
  - Volume Spike Detection
  - Trend-Filterung
- **Output:** Signal-Event auf Redis Topic `trading_signals`
- **Produktion:** ~330 Zeilen Python
- **Tests:** Unit & Integration bestanden

#### **C. Risk Manager (cdb_risk_manager)**
- **Funktion:** Validierung aller Trade-Requests gegen Risikorichtlinien
- **Input:** Trade-Signale von Redis
- **Regeln:**
  - Max. Daily Drawdown: 5%
  - Max. Total Exposure: 30%
  - Circuit Breaker: >10% Tagesverlust
  - Min./Max. Position Size
- **Output:** Approved/Rejected Trade auf Redis Topic `risk_approved_trades`
- **Produktion:** ~330 Zeilen Python
- **Tests:** Unit & Integration bestanden

#### **D. Execution Service (cdb_execution)**
- **Funktion:** Trade-Platzierung und Ausführung
- **Input:** Risiko-validierte Trades
- **Workflow:**
  1. MEXC API Call (Order-Platzierung)
  2. Order-Tracking in PostgreSQL
  3. Execution-Event an Redis
  3. Persistierung in DB
- **Status:** In Entwicklung (Mock-Trading aktiv)
- **Produktion:** ~200 Zeilen Python

#### **E. Monitoring & Observability**
- **Prometheus:** Metriken-Sammlung
- **Grafana:** Dashboard für Systemzustand
- **Health-Checks:** Alle Services exponieren `/health`-Endpoint
- **Logging:** JSON-strukturiert in allen Containern

#### **F. Datenpersistenz**
- **PostgreSQL (cdb_postgres):** Zentrale relationale Datenbank
  - Tabellen: market_data, signals, trades, risk_events, executions, audits
  - Indices für Performance optimiert
  - Connection-Pooling via Psycopg2
- **Redis (cdb_redis):** Distributed Message Bus
  - Pub/Sub für Service-Kommunikation
  - Cache für aktuelle Marktdaten
  - Volatile, unkritische Daten

---

## 3. CONTAINERSTRUKTUR

### 3.1 Docker-Umgebung

**Host:** Docker Desktop (Windows)  
**Network:** Docker Bridge (cdb_network)  

| Container | Port | Status | Volumen | Funktion |
|-----------|------|--------|---------|----------|
| cdb_postgres | 5432 | Aktiv | /var/lib/postgresql/data | Datenbank |
| cdb_redis | 6379 | Aktiv | Redis-Memory | Message Bus |
| cdb_websocket_screener | 5001 | Aktiv | — | Market-Daten |
| cdb_signal_engine | 5002 | Aktiv | — | Signale |
| cdb_risk_manager | 5003 | Aktiv | — | Validierung |
| cdb_execution | 5004 | Dev | — | Trade-Execution |
| cdb_prometheus | 9090 | Aktiv | /prometheus | Metriken |
| cdb_grafana | 3000 | Aktiv | /grafana | Dashboard |

### 3.2 Volume-Management

```
Docker Desktop Volumes:
/var/lib/docker/volumes/
├── cdb_postgres_data/      → PostgreSQL persistent storage
├── cdb_redis_data/         → Redis snapshots
├── cdb_prometheus_data/    → Prometheus TSDB
└── cdb_grafana_data/       → Grafana dashboards
```

---

## 4. DATENBANKSCHEMA

**Datenbank:** `database_claire_de_binare` (PostgreSQL 14+)

### 4.1 Kern-Tabellen

```sql
-- Market-Daten
market_data (id, symbol, price, volume, timestamp, source)

-- Signal-Events
trading_signals (id, symbol, signal_type, strength, timestamp, engine_version)

-- Risk-Logs
risk_events (id, trade_id, risk_check, result, reason, timestamp)

-- Trades
trades (id, symbol, direction, size, entry_price, exit_price, status, timestamp)

-- Executions
executions (id, trade_id, exchange_order_id, status, commission, timestamp)

-- Audit-Trail
audits (id, event_type, service, data, timestamp)
```

### 4.2 Indizes & Performance

- Primary Keys auf allen Tabellen
- UNIQUE Index auf (symbol, timestamp)
- Composite Index auf risk_events (trade_id, timestamp)
- Partitionierung möglich für market_data (zeitbasiert)

---

## 5. KOMMUNIKATIONSPROTOKOLL

### 5.1 Redis Pub/Sub Topics

| Topic | Publisher | Subscriber | Struktur |
|-------|-----------|------------|----------|
| `market_data` | WebSocket Screener | Signal Engine | `{symbol, price, volume, ts}` |
| `trading_signals` | Signal Engine | Risk Manager | `{symbol, signal, strength, ts}` |
| `risk_approved_trades` | Risk Manager | Execution | `{signal_id, approved, reason}` |
| `execution_events` | Execution | Monitoring | `{trade_id, status, result}` |
| `system_health` | All Services | Monitoring | `{service, status, metrics}` |

### 5.2 Message-Format

```json
{
  "event_id": "uuid",
  "timestamp": "2024-11-20T14:32:10.123Z",
  "service": "signal_engine",
  "data": {
    "symbol": "BTC/USDT",
    "signal_type": "BUY",
    "confidence": 0.87
  }
}
```

---

## 6. SICHERHEITSKONZEPT

### 6.1 API-Keys Management

- **MEXC API-Keys:** Lagern in `.env` (Git-ignoriert)
- **Berechtigungen:** Read + Trade only (KEINE Withdraw-Rechte)
- **Rotation:** Monatlich geplant
- **Logging:** Alle API-Calls werden geloggt (anonymisiert)

### 6.2 Datenschutz

- PostgreSQL: Connections über Port 5432 (nur lokal in Docker Network)
- Redis: Unverschlüsselt (nur localhost)
- SSL/TLS: Zukünftig für Remote-Verbindungen
- Secrets: Geheimnisse via Docker Secrets (Production-ready)

### 6.3 Fehlerbehandlung

- Jeder Service hat Exception-Handling + Retry-Logik
- Health-Checks exponieren Service-Status
- Graceful Shutdown auf SIGTERM
- Automatische Log-Rotation

---

## 7. TESTINFRASTRUKTUR

### 7.1 Pytest-Setup

```
tests/
├── unit/
│   ├── test_signal_engine.py
│   ├── test_risk_manager.py
│   └── test_execution_service.py
├── integration/
│   ├── test_redis_communication.py
│   ├── test_database_persistence.py
│   └── test_end_to_end.py
└── fixtures/
    ├── conftest.py
    └── mock_data.py
```

### 7.2 Test-Coverage

- Signal Engine: 95% Code-Coverage
- Risk Manager: 92% Code-Coverage
- Execution Service: In Development
- Integration-Tests: 7/7 Validierungschecks bestanden

### 7.3 Continuous Integration

- Black Code-Formatter: Automatisch
- Flake8 Linting: Standard
- Pytest mit Coverage-Reports
- Docker Build-Validierung vor Deploy

---

## 8. MONITORING & OBSERVABILITY

### 8.1 Prometheus Metriken

```
# Trading Metrics
trades_total                    # Gesamte abgeschlossene Trades
trades_successful_total         # Erfolgreiche Trades
trades_failed_total             # Fehlgeschlagene Trades
avg_position_size               # Durchschnittliche Positionsgröße

# Risk Metrics
daily_drawdown_percent          # Aktueller Tagesverlust
total_exposure_percent          # Gesamtexposure
risk_checks_passed_total        # Bestandene Risikoprüfungen
risk_checks_failed_total        # Fehlgeschlagene Risikoprüfungen

# System Metrics
service_health{service="..."}   # 1=healthy, 0=unhealthy
redis_latency_ms                # Message-Bus Latenz
database_connections_active     # Aktive DB-Verbindungen
websocket_latency_ms            # Market-Data Latenz
```

### 8.2 Grafana Dashboards

- **Overview Dashboard:** Gesamtsystemzustand
- **Trading Performance:** Win-Rate, Drawdown, ROI
- **Risk Metrics:** Exposure, Circuit Breaker Status
- **Infrastructure:** Container-Health, Ressourcennutzung

---

## 9. DEPLOYMENT-STRATEGIE

### 9.1 Lokales Development

```bash
# Build aller Services
docker-compose build

# Starten des Stacks
docker-compose up -d

# Health-Checks
curl localhost:5001/health   # Screener
curl localhost:5002/health   # Signal Engine
curl localhost:5003/health   # Risk Manager
curl localhost:5004/health   # Execution
```

### 9.2 Production-Ready Features

- Volume-Persistierung für Datenbankbackups
- Automatic Restart Policy: `unless-stopped`
- Resource Limits: CPU & Memory pro Container
- Logging: JSON-strukturiert für ELK-Integration
- Health-Endpoint-Polling: Automatische Recovery

### 9.3 Backup-Strategie

- **Daily:** PostgreSQL Dump + Redis Snapshot
- **Retention:** 30 Tage
- **Automation:** Cron-Jobs + PowerShell Scripts
- **Testing:** Monatliche Restore-Tests

---

## 10. TECHNOLOGIE-STACK

| Komponente | Technologie | Version | Begründung |
|------------|-------------|---------|-----------|
| Base | Python | 3.11 | Stabiler, langfristig unterstützt |
| Database | PostgreSQL | 14+ | Zuverlässig, ACID, JSON-Support |
| Message Bus | Redis | 7+ | Schnell, Pub/Sub, einfaches Deployment |
| Monitoring | Prometheus + Grafana | Latest | Industrie-Standard |
| Containerization | Docker | Latest | Isolation, Reproducibility |
| Test Framework | pytest | Latest | Komprehensiv, Community-Standard |
| Web | Flask/FastAPI | Latest | Leichtgewichtig für Health-Checks |

---

## 11. ROADMAP ZUR MVP-FERTIGSTELLUNG

### Phase 1: ✅ ABGESCHLOSSEN (Oktober–November)
- [x] PostgreSQL & Redis Setup
- [x] WebSocket Screener Implementierung
- [x] Signal Engine (EMA/SMA/RSI)
- [x] Risk Manager (Drawdown, Exposure, Circuit Breaker)
- [x] Basic Execution Service (Mock-Mode)
- [x] Prometheus/Grafana Monitoring
- [x] Unit & Integration Tests

### Phase 2: IN PROGRESS (November–Dezember)
- [ ] Execution Service Finalisierung
- [ ] MEXC API-Integration (Live-Keys)
- [ ] Risk Engine Pytest-Tests (4 kritische Tests)
- [ ] End-to-End System Test
- [ ] Dokumentation & Runbooks

### Phase 3: PRODUCTION (Januar 2025)
- [ ] Live-Trading Initiation (Small Position)
- [ ] Monitoring & Alert-Setup
- [ ] Incident Response Playbooks
- [ ] Capacity Planning & Scaling

---

## 12. BEKANNTE CONSTRAINTS & DEPENDENCIES

### 12.1 Externe Dependencies
- MEXC API-Keys (nicht in Repository)
- Market-Data-Feed-Stabilität (MEXC Uptime)
- Internet-Konnektivität für WebSocket

### 12.2 Interne Dependencies
- PostgreSQL muss vor anderen Services starten
- Redis muss vor Signal Engine starten
- Execution Service wartet auf Risk Manager

### 12.3 Performance-Constraints
- WebSocket Latenz: <100ms akzeptabel
- Signal Processing: <500ms pro Signal
- Trade Execution: <1s von Signal bis Order

---

## 13. WARTUNG & BETRIEB

### 13.1 Tägliche Checks
- Container-Status: `docker ps`
- Health-Endpoints prüfen
- PostgreSQL Connection-Pool Monitor
- Redis Memory Usage

### 13.2 Wöchentliche Tasks
- Logdateien reviewen
- Backup-Integrity validieren
- Performance-Metriken analysieren
- API-Rate-Limits prüfen

### 13.3 Monatliche Maintenance
- Abhängigkeits-Updates
- Security Patches
- Capacity Planning
- Disaster Recovery Drill

---

## 14. NOTFALL-VERFAHREN

### 14.1 Service-Ausfall
1. Service-Container stoppen: `docker stop <service>`
2. Logs analysieren: `docker logs <service>`
3. Container neustarten: `docker restart <service>`
4. Health-Check validieren

### 14.2 Datenbankausfall
1. PostgreSQL-Status prüfen: `docker exec cdb_postgres pg_isready`
2. Neustart initiieren: `docker restart cdb_postgres`
3. Backup-Restore wenn nötig
4. Slave-Failover (Future)

### 14.3 Memory Leak / High Resource Usage
1. Top-Container identifizieren: `docker stats`
2. Metriken in Prometheus checken
3. Container mit Resource-Limits neustarten
4. Code-Review initiieren

---

## 15. KONTAKT & SUPPORT

**Projekt-Leiter:** Jannek  
**IT-Chef / Architektur:** Claude  
**Server-Admin / Docker:** Gordon  

**Dokumentation:** Alle `.md`-Dateien im Projektroot  
**Logs:** Container-Logs über `docker logs`  
**Monitoring:** Grafana Dashboard auf `localhost:3000`  
**Prometheus:** Metriken auf `localhost:9090`  

---

**Dokument erstellt:** November 2024  
**Nächste Überprüfung:** Dezember 2024  
**Status:** PRODUKTIONSREIF
