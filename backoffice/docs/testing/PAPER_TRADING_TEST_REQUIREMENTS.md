# Paper Trading Test Requirements - Claire de Binare
**Dokumentation für vollständige Paper Trading Test-Suite**

---

## 📋 1. Trading Events Flow (market_data → trades)

### Event-Pipeline

```
┌─────────────┐
│ MEXC API    │
└──────┬──────┘
       ↓ market_data (WebSocket)
┌─────────────┐
│ Screener WS │ (cdb_ws:8000)
└──────┬──────┘
       ↓ market_data (Redis Channel)
┌─────────────┐
│ Signal Eng. │ (cdb_core:8001)
└──────┬──────┘
       ↓ signals (Redis Channel)
┌─────────────┐
│ Risk Mgr.   │ (cdb_risk:8002)
└──────┬──────┘
       ↓ orders (Redis Channel)
┌─────────────┐
│ Execution   │ (cdb_execution:8003)
└──────┬──────┘
       ↓ order_results (Redis Channel)
┌─────────────┐
│ DB Writer   │ (cdb_db_writer)
└──────┬──────┘
       ↓ PostgreSQL
┌─────────────┐
│ Portfolio   │ (cdb_portfolio)
└─────────────┘
```

### Event-Types & Channels

| Event Type | Redis Channel | Producer | Consumer | PostgreSQL Table |
|-----------|---------------|----------|----------|------------------|
| `market_data` | `market_data` | cdb_ws | cdb_core | - |
| `signals` | `signals` | cdb_core | cdb_risk | `signals` |
| `orders` | `orders` | cdb_risk | cdb_execution | `orders` |
| `order_results` | `order_results` | cdb_execution | cdb_db_writer | `trades` |
| `portfolio_snapshots` | `portfolio_snapshots` | cdb_portfolio | cdb_db_writer | `portfolio_snapshots` |
| `alerts` | `alerts` | risk/system | - | - |

### Event-Schema (Beispiele)

**market_data Event**:
```json
{
  "type": "market_data",
  "symbol": "BTCUSDT",
  "price": 50000.0,
  "volume": 1000.0,
  "timestamp": "2025-11-20T21:00:00Z",
  "bid": 49995.0,
  "ask": 50005.0
}
```

**signals Event**:
```json
{
  "type": "signal",
  "symbol": "BTCUSDT",
  "signal_type": "buy",
  "price": 50000.0,
  "confidence": 0.85,
  "timestamp": "2025-11-20T21:00:01Z",
  "strategy": "momentum"
}
```

**orders Event**:
```json
{
  "type": "order",
  "symbol": "BTCUSDT",
  "side": "buy",
  "quantity": 0.1,
  "price": 50000.0,
  "approved": true,
  "signal_id": 123,
  "timestamp": "2025-11-20T21:00:02Z"
}
```

**order_results Event**:
```json
{
  "type": "order_result",
  "symbol": "BTCUSDT",
  "side": "buy",
  "quantity": 0.1,
  "price": 50010.0,
  "status": "filled",
  "slippage": 0.02,
  "order_id": 456,
  "timestamp": "2025-11-20T21:00:03Z"
}
```

---

## 🗃️ 2. PostgreSQL Schema (persistierte Daten)

### Tabellen-Übersicht

| Tabelle | Zweck | Event-Source | Retention |
|---------|-------|--------------|-----------|
| `signals` | Trading-Signale | `signals` channel | 30 Tage |
| `orders` | Genehmigte Orders | `orders` channel | 90 Tage |
| `trades` | Ausgeführte Trades | `order_results` channel | Permanent |
| `positions` | Aktuelle Positionen | Portfolio Manager | Live |
| `portfolio_snapshots` | Portfolio-Historie | `portfolio_snapshots` channel | Permanent |

### Tabellen-Details

#### `signals` Table
```sql
CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    signal_type VARCHAR(10) NOT NULL,  -- 'buy', 'sell'
    price DECIMAL(18, 8) NOT NULL,
    confidence DECIMAL(5, 4),          -- 0.0-1.0
    strategy VARCHAR(50),
    timestamp TIMESTAMP NOT NULL,
    metadata JSONB,
    INDEX idx_signals_timestamp (timestamp),
    INDEX idx_signals_symbol (symbol),
    INDEX idx_signals_signal_type (signal_type)
);
```

#### `orders` Table
```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES signals(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,         -- 'buy', 'sell'
    quantity DECIMAL(18, 8) NOT NULL,
    price DECIMAL(18, 8) NOT NULL,
    status VARCHAR(20) NOT NULL,       -- 'pending', 'approved', 'rejected'
    created_at TIMESTAMP NOT NULL,
    metadata JSONB,
    INDEX idx_orders_created_at (created_at),
    INDEX idx_orders_signal_id (signal_id),
    INDEX idx_orders_status (status),
    INDEX idx_orders_symbol (symbol)
);
```

#### `trades` Table
```sql
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(18, 8) NOT NULL,
    price DECIMAL(18, 8) NOT NULL,
    status VARCHAR(20) NOT NULL,       -- 'filled', 'partial', 'failed'
    slippage DECIMAL(10, 6),
    timestamp TIMESTAMP NOT NULL,
    metadata JSONB,
    INDEX idx_trades_timestamp (timestamp),
    INDEX idx_trades_order_id (order_id),
    INDEX idx_trades_status (status),
    INDEX idx_trades_symbol (symbol)
);
```

#### `positions` Table
```sql
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    side VARCHAR(10) NOT NULL,         -- 'long', 'short', 'none'
    size DECIMAL(18, 8) NOT NULL,
    entry_price DECIMAL(18, 8),
    current_price DECIMAL(18, 8),
    unrealized_pnl DECIMAL(18, 8),
    opened_at TIMESTAMP,
    updated_at TIMESTAMP NOT NULL,
    INDEX idx_positions_symbol (symbol),
    INDEX idx_positions_side (side),
    INDEX idx_positions_updated_at (updated_at)
);
```

#### `portfolio_snapshots` Table
```sql
CREATE TABLE portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    equity DECIMAL(18, 8) NOT NULL,
    cash DECIMAL(18, 8) NOT NULL,
    total_unrealized_pnl DECIMAL(18, 8),
    total_realized_pnl DECIMAL(18, 8),
    daily_pnl DECIMAL(18, 8),
    total_exposure_pct DECIMAL(10, 6),
    num_positions INTEGER,
    metadata JSONB,
    INDEX idx_portfolio_snapshots_timestamp (timestamp)
);
```

---

## 🐳 3. Docker Container Dependencies

### Container-Übersicht

| Container | Port | Service | Dependencies | Health-Check |
|-----------|------|---------|--------------|--------------|
| `cdb_postgres` | 5432 | PostgreSQL | - | `pg_isready` |
| `cdb_redis` | 6379 | Message Bus | - | `redis-cli ping` |
| `cdb_ws` | 8000 | WebSocket Screener | redis | `/health` |
| `cdb_core` | 8001 | Signal Engine | redis, postgres | `/health` |
| `cdb_risk` | 8002 | Risk Manager | redis, postgres | `/health` |
| `cdb_execution` | 8003 | Execution | redis, postgres | `/health` |
| `cdb_db_writer` | - | DB Writer | redis, postgres | - |
| `cdb_portfolio` | - | Portfolio Manager | redis, postgres | - |
| `cdb_grafana` | 3000 | Monitoring | prometheus | HTTP 200 |
| `cdb_prometheus` | 9090 | Metrics | - | HTTP 200 |

### Start-Reihenfolge (Dependencies)

```
Level 1: Infrastructure
├─ cdb_postgres  (keine Dependencies)
└─ cdb_redis     (keine Dependencies)

Level 2: Core Services
├─ cdb_ws        (depends: redis)
├─ cdb_core      (depends: redis, postgres)
└─ cdb_risk      (depends: redis, postgres)

Level 3: Execution & Persistence
├─ cdb_execution (depends: redis, postgres)
├─ cdb_db_writer (depends: redis, postgres)
└─ cdb_portfolio (depends: redis, postgres)

Level 4: Monitoring (optional)
├─ cdb_prometheus (keine Dependencies)
└─ cdb_grafana    (depends: prometheus)
```

### Network Configuration

```yaml
networks:
  claire_network:
    driver: bridge

# Alle Services im gleichen Netzwerk:
# - Hostname = Container-Name (z.B. cdb_postgres, cdb_redis)
# - Intern: cdb_postgres:5432
# - Host-Zugriff: localhost:5432
```

---

## 📊 4. Risk-Engine Limits & Test-Cases

### ENV-Konfigurierte Limits

| Parameter | ENV-Variable | Default | Beschreibung |
|-----------|--------------|---------|--------------|
| Max Position | `MAX_POSITION_PCT` | 0.10 (10%) | Max Positionsgröße pro Symbol |
| Daily Drawdown | `MAX_DAILY_DRAWDOWN_PCT` | 0.05 (5%) | Max Tagesverlust |
| Total Exposure | `MAX_TOTAL_EXPOSURE_PCT` | 0.30 (30%) | Max Gesamt-Exposition |
| Circuit Breaker | `CIRCUIT_BREAKER_THRESHOLD_PCT` | 0.10 (10%) | Emergency Stop |
| Max Slippage | `MAX_SLIPPAGE_PCT` | 0.02 (2%) | Max Slippage pro Trade |
| Data Timeout | `DATA_STALE_TIMEOUT_SEC` | 60 | Max Alter von Market-Data |

### Risk-Check Reihenfolge

1. **Data Quality Check** - Stale/Invalid Data
2. **Position Limits** - Max Position Size
3. **Daily Drawdown** - Max Loss per Day
4. **Total Exposure** - Gesamt-Exposure
5. **Circuit Breaker** - Emergency Stop
6. **Spread Check** - Bid-Ask-Spread
7. **Timeout Check** - Data Freshness

### Test-Case Matrix

| Szenario | Limit | Erwartetes Verhalten | Test-ID |
|----------|-------|---------------------|---------|
| Position zu groß | 10% | Signal blockiert | TC-001 |
| Daily Drawdown > 5% | 5% | Trading gestoppt | TC-002 |
| Total Exposure > 30% | 30% | Neue Orders blockiert | TC-003 |
| Circuit Breaker | 10% Loss | System-Shutdown | TC-004 |
| Slippage > 2% | 2% | Order abgelehnt | TC-005 |
| Stale Data (>60s) | 60s | Signal ignoriert | TC-006 |
| Spread zu hoch | Dynamisch | Order verzögert | TC-007 |

---

## ⚡ 5. Performance-Metriken (Baselines)

### Latency-Targets

| Metrik | Target | Max Acceptable | Measurement |
|--------|--------|----------------|-------------|
| Market Data → Signal | <100ms | 500ms | Event timestamp diff |
| Signal → Risk Approval | <50ms | 200ms | Event timestamp diff |
| Order → Execution | <100ms | 500ms | Event timestamp diff |
| End-to-End (market_data → trade) | <300ms | 1000ms | Full pipeline |
| Database Query (SELECT) | <50ms | 500ms | Query execution time |
| Database Query (AGGREGATION) | <200ms | 1000ms | Query execution time |

### Throughput-Targets

| Metrik | Target | Max Acceptable | Test |
|--------|--------|----------------|------|
| Market Data Events/sec | 100 | 50 | Stress test |
| Signals/sec | 50 | 20 | Signal generation |
| Orders/sec | 20 | 10 | Risk validation |
| Trades/sec | 20 | 10 | Execution |
| Database Writes/sec | 100 | 50 | Batch inserts |

### Memory & CPU Baselines

| Service | Memory (Idle) | Memory (Load) | CPU (Idle) | CPU (Load) |
|---------|---------------|---------------|------------|------------|
| cdb_postgres | 100MB | 500MB | <5% | <50% |
| cdb_redis | 50MB | 200MB | <5% | <30% |
| cdb_core | 100MB | 300MB | <10% | <40% |
| cdb_risk | 100MB | 300MB | <10% | <40% |
| cdb_execution | 100MB | 300MB | <10% | <40% |

---

## 🎯 6. Kritische Test-Szenarien (Priorität)

### High Priority (P0)

1. **Happy Path** - Vollständiger Flow: market_data → trade
2. **Risk Blockierung** - Position-Limit überschritten
3. **Daily Drawdown** - Trading gestoppt bei 5% Verlust
4. **Circuit Breaker** - System-Shutdown bei 10% Verlust
5. **Data Persistence** - Alle Events in PostgreSQL

### Medium Priority (P1)

6. **Service-Ausfall Recovery** - cdb_core crasht und startet neu
7. **Database Disconnect** - PostgreSQL-Verbindung verloren
8. **Redis Disconnect** - Message Bus Verbindung verloren
9. **Concurrent Orders** - Mehrere Orders gleichzeitig
10. **Stress Test** - 100+ Events in 10 Sekunden

### Low Priority (P2)

11. **Volume Persistence** - Container-Neustart, Daten bleiben
12. **Performance Degradation** - Langsame Queries identifizieren
13. **Error Propagation** - Fehler durch Pipeline tracken
14. **Monitoring Integration** - Grafana zeigt Metriken
15. **Backup & Restore** - PostgreSQL Backup funktioniert

---

## 🧪 7. Test-Infrastruktur Requirements

### Für E2E Paper Trading Tests benötigt:

- [ ] **Docker Compose** - Alle 9 Services running
- [ ] **Test-Daten Generator** - Realistische market_data Events
- [ ] **Event-Validation** - Prüfe Event-Struktur
- [ ] **Timing-Framework** - Messe Latency
- [ ] **Database Fixtures** - Seed-Daten für Tests
- [ ] **Cleanup-Mechanismus** - Teardown nach Tests
- [ ] **Parallel Test Execution** - Pytest-xdist
- [ ] **Performance Profiling** - cProfile Integration

### Tools & Libraries

```python
# requirements-dev.txt (zusätzlich)
pytest-benchmark  # Performance-Messungen
pytest-timeout    # Timeout-Handling
faker            # Test-Daten generieren
freezegun        # Zeit-Mocking
```

---

## 📝 Nächste Schritte

1. ✅ **Dokumentation erstellt** (dieses File)
2. ⏳ **Issue #43** - query_analytics.py Bug beheben
3. ⏳ **E2E Paper Trading Tests** - Implementierung starten
4. ⏳ **Performance Baselines** - Messungen durchführen
5. ⏳ **Resilience Tests** - Fehlerfall-Szenarien

---

**Status**: 🚧 Work in Progress
**Erstellt**: 2025-11-20
**Autor**: Claude (via Claude Code)
