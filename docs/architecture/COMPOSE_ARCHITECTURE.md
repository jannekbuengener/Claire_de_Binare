# Compose Architecture (Issue #292)

Vollständige Dokumentation der Docker Compose Infrastruktur.

## Stack-Übersicht

```
┌─────────────────────────────────────────────────────────────────┐
│                        cdb_network                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Market   │→ │ Signal   │→ │ Risk     │→ │ Execution│        │
│  │ Data     │  │ Engine   │  │ Manager  │  │ Service  │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│       ↓             ↓             ↓             ↓               │
│  ┌──────────────────────────────────────────────────┐           │
│  │                   cdb_redis                       │           │
│  │              (Pub/Sub + Cache)                   │           │
│  └──────────────────────────────────────────────────┘           │
│                          ↓                                       │
│  ┌──────────────────────────────────────────────────┐           │
│  │                  cdb_postgres                     │           │
│  │            (Event Store + State)                 │           │
│  └──────────────────────────────────────────────────┘           │
│                          ↓                                       │
│  ┌──────────────────────────────────────────────────┐           │
│  │      cdb_prometheus  →  cdb_grafana              │           │
│  │         (Metrics)        (Dashboards)            │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Services

### Core Infrastructure

| Service | Container | Port (internal) | Persistent Volume |
|---------|-----------|-----------------|-------------------|
| Redis | cdb_redis | 6379 | redis_data |
| PostgreSQL | cdb_postgres | 5432 | postgres_data |
| Prometheus | cdb_prometheus | 9090 | prom_data |
| Alertmanager | cdb_alertmanager | 9093 | alertmanager_data |
| Grafana | cdb_grafana | 3000 | grafana_data |

### Trading Services

| Service | Beschreibung | Dependencies |
|---------|--------------|--------------|
| Market Data | WebSocket-Daten von MEXC | Redis |
| Signal Engine | RL-basierte Signal-Generierung | Redis |
| Risk Manager | Position Sizing, Circuit Breaker | Redis, Postgres |
| Execution | Order-Routing zu MEXC | Redis, Postgres |
| DB Writer | Event Persistence | Postgres |

## Netzwerk

```yaml
networks:
  cdb_network:
    driver: bridge
```

Alle Services kommunizieren über `cdb_network`. Keine externen Port-Bindings in base.yml (Security).

## Volumes

### Persistent (NIEMALS löschen)

| Volume | Inhalt | Backup-Priorität |
|--------|--------|------------------|
| postgres_data | Trading-Events, Positions, Orders | KRITISCH |
| redis_data | Cache, aktive Streams | HOCH |
| grafana_data | Dashboard-Definitionen | MITTEL |
| prom_data | Metriken-History | NIEDRIG |

### Ephemeral (löschbar)

- Build Cache
- Unnamed Volumes
- Stopped Container Data

## Environment Variables

### Erforderlich (.env)

```bash
# Stack
STACK_NAME=cdb
NETWORK=cdb_network

# Credentials (via Docker Secrets)
REDIS_PASSWORD=<path-to-secret>
POSTGRES_PASSWORD=<path-to-secret>
GRAFANA_PASSWORD=<path-to-secret>

# MEXC API
MEXC_API_SECRET=<path-to-secret>
MEXC_TESTNET=true

# Trading Mode
DRY_RUN=true
SIGNAL_STRATEGY_ID=paper
```

## Data Flow

### Signal → Trade Pipeline

```
1. Market Data Service
   └─ WebSocket: MEXC → Redis Stream (market:btcusdt)

2. Signal Engine
   └─ Redis Sub → RL Policy → Redis Pub (signals)

3. Risk Manager
   └─ Redis Sub → Position Check → Postgres Query
   └─ Approved? → Redis Pub (orders)

4. Execution Service
   └─ Redis Sub → MEXC API → Redis Pub (order_results)

5. DB Writer
   └─ Redis Sub → Postgres Insert (trades, positions)
```

### Metrics Flow

```
Services → Prometheus (/metrics) → Grafana (Dashboards)
                ↓
         Alertmanager → Slack/Email
```

## Canonical Commands

### Stack starten

```powershell
cd infrastructure/compose
docker compose -f base.yml -f dev.yml up -d
```

### Health prüfen

```powershell
docker compose -f base.yml ps
docker compose -f base.yml logs -f cdb_postgres
```

### Stack stoppen

```powershell
docker compose -f base.yml down  # Volumes behalten
# NIEMALS: docker compose down -v  # Löscht Volumes!
```

### Konfiguration validieren

```powershell
docker compose -f base.yml -f dev.yml config
```

## Troubleshooting

### Container startet nicht

```powershell
# Logs prüfen
docker logs cdb_postgres

# Häufige Ursachen:
# - Missing .env file
# - Wrong secret path
# - Port already in use
```

### Redis Connection Refused

```powershell
# Redis läuft?
docker exec cdb_redis redis-cli -a $REDIS_PASSWORD ping

# Häufige Ursachen:
# - Wrong password
# - Container not ready
```

### Postgres Auth Failed

```powershell
# Credentials prüfen
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "SELECT 1"

# Häufige Ursachen:
# - Wrong password in .env
# - User not created
```

## Verwandte Dokumente

- [Health Contract](../services/HEALTH_CONTRACT.md)
- [Monthly Maintenance](../ops/MONTHLY_MAINTENANCE.md)
- [Audit Trail](../security/AUDIT_TRAIL.md)
