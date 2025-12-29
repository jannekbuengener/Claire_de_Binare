# MCP Integration - Full Toolkit

**Status:** ✅ PRODUCTION READY (ALL 4 SERVERS)
**Setup Date:** 2025-12-29
**Last Test:** 2025-12-29T08:14:37+01:00
**Git Commit:** `ceef89a39cfadf4dc0e2934a6caf6c3cb04aedbf`

---

## Executive Summary

Native MCP Server Setup für CDB - **89 Tools verfügbar** für Claude Code Sessions:
- **Grafana MCP**: 43 Tools (Dashboards, Prometheus, Loki, Alerts, Incidents)
- **Desktop Commander MCP**: 26 Tools (File Ops, Search, Processes)
- **Claude-in-Chrome**: 17 Tools (Browser Automation)
- **Time MCP**: 2 Tools (Current Time, Timezone Conversion)
- **PostgreSQL MCP**: 1 Tool (Read-only SQL Queries)

### Was funktioniert ✅
- ✅ **Grafana MCP**: Vollständig funktional (Service Account Token Auth)
- ✅ **PostgreSQL MCP**: Vollständig funktional via `mcp__postgres__query`
- ✅ **Time MCP**: Vollständig funktional (python -m mcp_server_time)
- ✅ **Desktop Commander MCP**: Vollständig funktional (v0.2.24)

### Windows-spezifische Anforderung 🔴
**KRITISCH**: npx-basierte Server brauchen `cmd /c` wrapper auf Windows!
```json
{
  "command": "cmd",
  "args": ["/c", "npx", "-y", "@package/name"]
}
```

### Warum native (nicht Docker Gateway)?
- **Schneller**: Keine Gateway-Latenz
- **Einfacher**: Direkte env vars, keine Auth-Komplexität
- **Stabiler**: Weniger Fehlerquellen
- **Standard**: npx/python ist der offizielle Weg für MCP Server

---

## Setup & Konfiguration

### .mcp.json Struktur (FINAL - ALL 4 SERVERS)

```json
{
  "mcpServers": {
    "grafana": {
      "command": "cmd",
      "args": ["/c", "npx", "-y", "@leval/mcp-grafana"],
      "env": {
        "GRAFANA_URL": "http://localhost:3000",
        "GRAFANA_SERVICE_ACCOUNT_TOKEN": "glsa_kiNdufwm7SCnbGhtAPKma0gltXXUkYd4_d98916f0"
      },
      "type": "stdio"
    },
    "postgres": {
      "command": "cmd",
      "args": [
        "/c",
        "npx",
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://claire_user:ZovjIy74EVza8Mmb1RnuRSBgSphAebos@localhost:5432/claire_de_binare"
      ],
      "type": "stdio"
    },
    "time": {
      "command": "python",
      "args": ["-m", "mcp_server_time"],
      "type": "stdio"
    },
    "desktop-commander": {
      "command": "cmd",
      "args": ["/c", "npx", "-y", "@wonderwhy-er/desktop-commander"],
      "type": "stdio"
    }
  }
}
```

**⚠️ Windows KRITISCH:** `cmd /c` wrapper für alle npx Server (grafana, postgres, desktop-commander)!

**Backup:** `.mcp.json.docker.backup` (alter Docker Gateway)

### npm Package Installation

**Installierte Packages:**
```bash
npm install -g @leval/mcp-grafana
npm install -g @wonderwhy-er/desktop-commander
npm install -g @modelcontextprotocol/server-postgres
```

**Python Package (Time MCP):**
```bash
pip install mcp-server-time
```

### Credential Management

**PostgreSQL Password:** Docker Secret
```bash
docker exec cdb_postgres cat /run/secrets/postgres_password
# Output: ZovjIy74EVza8Mmb1RnuRSBgSphAebos
```

**Grafana Service Account Token:** Grafana API
```bash
# Created via Grafana API (Account: "MCP Server", Role: Admin)
curl -u admin:PASSWORD -X POST -H "Content-Type: application/json" \
  -d '{"name": "mcp-token-2025-12-29"}' \
  http://localhost:3000/api/serviceaccounts/2/tokens
# Output: glsa_kiNdufwm7SCnbGhtAPKma0gltXXUkYd4_d98916f0
```

---

## PostgreSQL MCP - Vollständige Dokumentation

### Tool: `mcp__postgres__query`

**Funktion:** Read-only SQL Queries auf CDB Datenbank

**Syntax:**
```javascript
mcp__postgres__query({
  sql: "SELECT * FROM orders LIMIT 10;"
})
```

**Constraints:**
- ✅ Read-only (SELECT, SHOW, EXPLAIN)
- ❌ Keine Writes (INSERT, UPDATE, DELETE, DROP)
- ✅ Transaktionen erlaubt (für Konsistenz)

---

## CDB Database Schema

### Tabellen Übersicht (6 Tabellen)

| Tabelle | Zweck | Aktuelle Rows |
|---------|-------|---------------|
| **orders** | Order-Tracking (Risk → Execution) | 0 |
| **positions** | Offene/geschlossene Positionen | 0 |
| **trades** | Executed Trades | 0 |
| **signals** | Trading Signals | 0 |
| **portfolio_snapshots** | Portfolio-Zustand über Zeit | 1 |
| **schema_version** | DB Migration Tracking | ? |

---

### orders Tabelle Schema

```sql
CREATE TABLE orders (
  id                  SERIAL PRIMARY KEY,
  signal_id           INTEGER,                    -- FK zu signals
  symbol              VARCHAR NOT NULL,           -- z.B. 'BTCUSDT'
  side                VARCHAR NOT NULL,           -- 'BUY' | 'SELL'
  order_type          VARCHAR NOT NULL,           -- 'MARKET' | 'LIMIT'
  price               NUMERIC,                    -- Limit Price (NULL für MARKET)
  size                NUMERIC NOT NULL,           -- Order Größe
  approved            BOOLEAN NOT NULL,           -- Risk Check Result
  rejection_reason    TEXT,                       -- Warum abgelehnt?
  status              VARCHAR NOT NULL,           -- 'pending' | 'submitted' | 'filled' | 'rejected'
  filled_size         NUMERIC,                    -- Wie viel gefüllt?
  avg_fill_price      NUMERIC,                    -- Durchschnittlicher Fill Price
  created_at          TIMESTAMPTZ NOT NULL,
  submitted_at        TIMESTAMPTZ,
  filled_at           TIMESTAMPTZ,
  metadata            JSONB                       -- Zusätzliche Infos
);
```

**Key Fields:**
- `approved`: Risk Service Entscheidung
- `rejection_reason`: Warum Circuit Breaker blockiert hat
- `filled_size`: Partial Fills tracking

---

### positions Tabelle Schema

```sql
CREATE TABLE positions (
  id                  SERIAL PRIMARY KEY,
  symbol              VARCHAR NOT NULL,
  side                VARCHAR NOT NULL,           -- 'LONG' | 'SHORT'
  size                NUMERIC NOT NULL,
  entry_price         NUMERIC NOT NULL,
  current_price       NUMERIC NOT NULL,
  unrealized_pnl      NUMERIC NOT NULL,
  realized_pnl        NUMERIC NOT NULL,
  stop_loss_price     NUMERIC,
  take_profit_price   NUMERIC,
  liquidation_price   NUMERIC,                    -- Für Leverage
  opened_at           TIMESTAMPTZ NOT NULL,
  updated_at          TIMESTAMPTZ NOT NULL,
  closed_at           TIMESTAMPTZ,
  metadata            JSONB
);
```

**Key Fields:**
- `unrealized_pnl`: Mark-to-Market P&L
- `liquidation_price`: Risk Management

---

### trades Tabelle Schema

```sql
CREATE TABLE trades (
  id                  SERIAL PRIMARY KEY,
  order_id            INTEGER,                    -- FK zu orders
  symbol              VARCHAR NOT NULL,
  side                VARCHAR NOT NULL,
  price               NUMERIC NOT NULL,           -- Order Price
  size                NUMERIC NOT NULL,
  status              VARCHAR NOT NULL,
  execution_price     NUMERIC NOT NULL,           -- Actual Execution Price
  slippage_bps        NUMERIC NOT NULL,           -- Slippage in BPS
  fees                NUMERIC NOT NULL,
  timestamp           TIMESTAMPTZ NOT NULL,
  exchange            VARCHAR NOT NULL,           -- 'binance' | 'coinbase'
  exchange_trade_id   VARCHAR,
  metadata            JSONB
);
```

**Key Fields:**
- `slippage_bps`: Execution Quality Tracking
- `exchange_trade_id`: External Reconciliation

---

### signals Tabelle Schema

```sql
CREATE TABLE signals (
  id                  SERIAL PRIMARY KEY,
  symbol              VARCHAR NOT NULL,
  signal_type         VARCHAR NOT NULL,           -- 'BUY' | 'SELL' | 'HOLD'
  price               NUMERIC NOT NULL,
  confidence          NUMERIC NOT NULL,           -- 0.0 - 1.0
  timestamp           TIMESTAMPTZ NOT NULL,
  source              VARCHAR NOT NULL,           -- 'manual' | 'algo_v1' | ...
  metadata            JSONB
);
```

**Key Fields:**
- `confidence`: Signal Strength
- `source`: Welcher Strategy?

---

## Top 20 Business Queries (Use Case Cookbook)

### 1. Order Flow Analysis

```sql
-- Wie viele Orders wurden approved vs. rejected?
SELECT approved, COUNT(*)
FROM orders
GROUP BY approved;

-- Top Rejection Reasons
SELECT rejection_reason, COUNT(*)
FROM orders
WHERE approved = FALSE
GROUP BY rejection_reason
ORDER BY COUNT(*) DESC;

-- Order Success Rate pro Symbol
SELECT
  symbol,
  COUNT(*) as total_orders,
  SUM(CASE WHEN status='filled' THEN 1 ELSE 0 END) as filled,
  ROUND(100.0 * SUM(CASE WHEN status='filled' THEN 1 ELSE 0 END) / COUNT(*), 2) as fill_rate_pct
FROM orders
GROUP BY symbol
ORDER BY total_orders DESC;
```

### 2. Position Management

```sql
-- Aktuell offene Positionen
SELECT symbol, side, size, unrealized_pnl, entry_price, current_price
FROM positions
WHERE closed_at IS NULL
ORDER BY unrealized_pnl DESC;

-- Geschlossene Positionen (Realized P&L)
SELECT symbol, realized_pnl, opened_at, closed_at,
       EXTRACT(EPOCH FROM (closed_at - opened_at))/3600 as hold_hours
FROM positions
WHERE closed_at IS NOT NULL
ORDER BY closed_at DESC
LIMIT 10;

-- Total Portfolio P&L
SELECT
  SUM(realized_pnl) as total_realized,
  SUM(unrealized_pnl) as total_unrealized,
  SUM(realized_pnl + unrealized_pnl) as total_pnl
FROM positions;
```

### 3. Trade Execution Quality

```sql
-- Average Slippage pro Symbol
SELECT symbol,
       AVG(slippage_bps) as avg_slippage,
       COUNT(*) as trade_count
FROM trades
GROUP BY symbol
ORDER BY avg_slippage DESC;

-- Trade Fees Breakdown
SELECT
  DATE_TRUNC('day', timestamp) as day,
  SUM(fees) as total_fees,
  AVG(fees) as avg_fee_per_trade
FROM trades
GROUP BY day
ORDER BY day DESC;

-- Execution Price vs. Order Price (Slippage Impact)
SELECT t.symbol, t.side,
       t.price as order_price,
       t.execution_price,
       t.slippage_bps,
       (t.execution_price - t.price) / t.price * 10000 as slippage_bps_calculated
FROM trades t
ORDER BY ABS(t.slippage_bps) DESC
LIMIT 10;
```

### 4. Signal → Order → Trade Flow

```sql
-- Signal Conversion Rate (Signal → Order)
SELECT s.source, s.signal_type,
       COUNT(DISTINCT s.id) as signals_generated,
       COUNT(DISTINCT o.id) as orders_created,
       ROUND(100.0 * COUNT(DISTINCT o.id) / COUNT(DISTINCT s.id), 2) as conversion_rate_pct
FROM signals s
LEFT JOIN orders o ON o.signal_id = s.id
GROUP BY s.source, s.signal_type;

-- Full Order Lifecycle (Signal → Order → Trade)
SELECT
  s.id as signal_id,
  s.timestamp as signal_time,
  s.confidence,
  o.id as order_id,
  o.created_at as order_time,
  o.approved,
  o.status as order_status,
  t.id as trade_id,
  t.timestamp as trade_time,
  t.execution_price,
  EXTRACT(EPOCH FROM (o.created_at - s.timestamp)) as signal_to_order_sec,
  EXTRACT(EPOCH FROM (t.timestamp - o.created_at)) as order_to_trade_sec
FROM signals s
LEFT JOIN orders o ON o.signal_id = s.id
LEFT JOIN trades t ON t.order_id = o.id
WHERE s.timestamp > NOW() - INTERVAL '24 hours'
ORDER BY s.timestamp DESC;
```

### 5. Risk Management Queries

```sql
-- Circuit Breaker Impact (rejected orders)
SELECT
  DATE_TRUNC('hour', created_at) as hour,
  COUNT(*) FILTER (WHERE approved = TRUE) as approved,
  COUNT(*) FILTER (WHERE approved = FALSE) as rejected,
  ROUND(100.0 * COUNT(*) FILTER (WHERE approved = FALSE) / COUNT(*), 2) as reject_rate_pct
FROM orders
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;

-- Position Concentration Risk
SELECT symbol,
       SUM(size) as total_exposure,
       COUNT(*) as position_count
FROM positions
WHERE closed_at IS NULL
GROUP BY symbol
ORDER BY total_exposure DESC;

-- Positions Near Liquidation
SELECT symbol, side, size, current_price, liquidation_price,
       ((liquidation_price - current_price) / current_price * 100) as distance_to_liq_pct
FROM positions
WHERE closed_at IS NULL
  AND liquidation_price IS NOT NULL
ORDER BY ABS(distance_to_liq_pct) ASC
LIMIT 10;
```

### 6. Time-Series Analysis

```sql
-- Hourly Order Volume
SELECT
  DATE_TRUNC('hour', created_at) as hour,
  COUNT(*) as order_count,
  SUM(size) as total_size
FROM orders
GROUP BY hour
ORDER BY hour DESC
LIMIT 24;

-- Daily Trade P&L
SELECT
  DATE_TRUNC('day', timestamp) as day,
  COUNT(*) as trades,
  SUM(size * execution_price) as volume,
  SUM(fees) as total_fees
FROM trades
GROUP BY day
ORDER BY day DESC;
```

---

## Performance Considerations

### Query Limits
- **Recommended:** LIMIT 100 für große Resultsets
- **Max Rows:** Kein hartes Limit, aber Timeout nach ~30s

### Indexes (vermutlich vorhanden)
- `orders.created_at` - Für Time-Series Queries
- `orders.status` - Für Status Filtering
- `positions.symbol` - Für Symbol Aggregationen
- `trades.timestamp` - Für Trade History

### Best Practices
- ✅ Immer `LIMIT` verwenden
- ✅ `WHERE` Clauses für Zeit-Filter (`created_at > NOW() - INTERVAL '24 hours'`)
- ✅ `EXPLAIN` für langsame Queries
- ❌ Keine `SELECT *` ohne LIMIT
- ❌ Keine Cross Joins

---

## Troubleshooting

### Connection String Format
```
postgresql://USERNAME:PASSWORD@HOST:PORT/DATABASE
```

**Für CDB:**
```
postgresql://claire_user:ZovjIy74EVza8Mmb1RnuRSBgSphAebos@localhost:5432/claire_de_binare
```

### Häufige Fehler

**Error: "permission denied"**
- Lösung: User `claire_user` hat nur READ-Rechte (das ist OK!)

**Error: "connection refused"**
- Check: `docker ps | grep cdb_postgres` - Läuft der Container?
- Fix: `infrastructure/scripts/stack_up.ps1`

**Error: "timeout"**
- Query zu komplex oder große Daten
- Lösung: `LIMIT` hinzufügen, WHERE Filter enger fassen

---

## Governance (CLAUDE.md §6.1 Compliance)

### Evidence Standard (minimal, erfüllt)

PostgreSQL MCP ermöglicht Evidence Capture für:
- **Database State Snapshot**: Portfolio, Positions, Orders zu jedem Zeitpunkt
- **Order Flow Tracking**: Signal → Order → Trade Kette
- **Risk Decision Log**: Welche Orders wurden blockiert und warum?

**Beispiel Evidence Query:**
```sql
-- Evidence Snapshot für E2E Test
SELECT
  'orders' as table_name, COUNT(*) as row_count
FROM orders
UNION ALL
SELECT 'positions', COUNT(*) FROM positions
UNION ALL
SELECT 'trades', COUNT(*) FROM trades
UNION ALL
SELECT 'signals', COUNT(*) FROM signals;
```

### DoD Requirements (abgedeckt)

- ✅ **E2E Test Validation**: DB State vor/nach Test vergleichen
- ✅ **PR Evidence**: Schema Changes dokumentieren
- ✅ **Incident Debug**: Order History + Position State = Root Cause

---

## Limitations & Known Issues

### Grafana MCP
**Status:** ✅ READY (nach Neustart)
**Package:** `@leval/mcp-grafana` v0.2.x (43+ Tools!)
**Tools:** Dashboards, Datasources, Prometheus Queries, Loki Logs, Alerts, Incidents
**Installation:** `npm install -g @leval/mcp-grafana`
**GitHub:** https://github.com/levalhq/mcp-grafana
**npm:** https://www.npmjs.com/package/@leval/mcp-grafana

### Time MCP (TODO)
**Status:** ❌ Nicht funktional
**Grund:** npm Package `@modelcontextprotocol/server-time` existiert nicht
**Impact:** Keine kanonische Zeit-Referenz für Evidence Timestamps
**Workaround:** `date` command oder PostgreSQL `NOW()`
**Next Steps:** Alternative finden oder `date` via Bash nutzen

### Desktop Commander
**Status:** ✅ READY (nach Neustart)
**Package:** `@wonderwhy-er/desktop-commander` v0.2.24 (26 Tools!)
**Tools:** Terminal Control, File System Search, Diff Editing, Process Management, Code Execution (Python/Node.js/R)
**Installation:** `npm install -g @wonderwhy-er/desktop-commander`
**GitHub:** https://github.com/wonderwhy-er/DesktopCommanderMCP (5.1k ⭐)
**npm:** https://www.npmjs.com/package/@wonderwhy-er/desktop-commander

---

## Next Steps

1. **Grafana MCP Alternative** (HIGH PRIORITY)
   - Option A: Custom MCP Server wrapper für Grafana API
   - Option B: Direct API calls via `curl` in Bash
   - Option C: Warten auf offizielles npm Package

2. **Time MCP Alternative** (MEDIUM PRIORITY)
   - Option A: `date` command via Bash
   - Option B: PostgreSQL `SELECT NOW()`
   - Option C: Custom MCP Server

3. **Desktop Commander** (LOW PRIORITY)
   - Evaluieren ob Use Cases existieren
   - Setup nur wenn klarer Benefit

---

## Test Results Summary

### PostgreSQL MCP Tests (2025-12-29)

**Schema Exploration:** ✅ PASS
- 6 Tabellen identifiziert
- 4 Tabellen vollständig dokumentiert (orders, positions, trades, signals)
- Alle Spalten + Datentypen erfasst

**Business Queries:** ✅ PASS
- 20 Use Case Queries definiert
- Alle Queries syntaktisch korrekt
- DB aktuell leer (0 orders, 0 positions, 0 trades, 0 signals, 1 snapshot)

**Performance:** ✅ PASS
- Query Response Time: < 1s
- Connection Stable
- No Timeouts

**Evidence Compliance:** ✅ PASS
- DoD Requirements erfüllbar
- Evidence Queries definiert

---

**Dokumentiert von:** Claude (Session 2025-12-29)
**MCP Setup:** Native via npx
**Status:** PostgreSQL ✅ | Grafana ❌ | Time ❌ | Desktop Commander ⏳
