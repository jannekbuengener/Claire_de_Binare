# Analytics Query Tool
**Claire de Binare - PostgreSQL Auswertungen**

## 📊 Übersicht

Das Analytics Query Tool ermöglicht einfache Abfragen der Trading-Daten aus PostgreSQL.

## 🚀 Installation

```bash
# Dependencies
pip install psycopg2-binary tabulate

# ENV setzen (optional, wenn nicht bereits in .env)
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=claire_de_binare
export POSTGRES_USER=claire_user
export POSTGRES_PASSWORD=your_password
```

## 📝 Verwendung

### Letzte Signale anzeigen

```bash
python backoffice/scripts/query_analytics.py --last-signals 10
```

**Output**:
```
📊 Last 10 Signals:

+----+----------+-------------+---------+------------+---------------------------+
| id | symbol   | signal_type |   price | confidence | timestamp                 |
+====+==========+=============+=========+============+===========================+
|  5 | BTCUSDT  | buy         |   50000 |       0.85 | 2025-11-20 19:00:00+00:00 |
|  4 | ETHUSDT  | sell        |    3000 |       0.78 | 2025-11-20 18:55:00+00:00 |
+----+----------+-------------+---------+------------+---------------------------+
```

### Letzte Trades anzeigen

```bash
python backoffice/scripts/query_analytics.py --last-trades 20
```

**Output**:
```
💼 Last 20 Trades:

+----+----------+------+---------+------+--------+--------------+---------------------------+
| id | symbol   | side |   price | size | status | slippage_bps | timestamp                 |
+====+==========+======+=========+======+========+==============+===========================+
|  1 | BTCUSDT  | buy  | 50012.5 |  0.1 | filled |         2.50 | 2025-11-20 19:00:15+00:00 |
+----+----------+------+---------+------+--------+--------------+---------------------------+
```

### Portfolio-Snapshot anzeigen

```bash
python backoffice/scripts/query_analytics.py --portfolio-summary
```

**Output**:
```
💰 Portfolio Summary (Latest Snapshot):

  timestamp                :  2025-11-20 19:05:00+00:00
  total_equity             :        100,000.00
  available_balance        :         95,000.00
  daily_pnl                :            500.00
  total_realized_pnl       :          1,200.00
  total_unrealized_pnl     :            300.00
  open_positions           :                 2
  total_exposure_pct       :              0.05  (5%)
```

### Tägl icher P&L (letzte 7 Tage)

```bash
python backoffice/scripts/query_analytics.py --daily-pnl 7
```

**Output**:
```
📈 Daily P&L (Last 7 days):

+------------+---------------+----------------+-------------+-------------+
| date       | num_snapshots | avg_daily_pnl  | max_equity  | min_equity  |
+============+===============+================+=============+=============+
| 2025-11-20 |            12 |         500.00 | 100,500.00  |  99,800.00  |
| 2025-11-19 |            24 |         -50.00 |  99,950.00  |  99,700.00  |
+------------+---------------+----------------+-------------+-------------+
```

### Trade-Statistiken anzeigen

```bash
python backoffice/scripts/query_analytics.py --trade-statistics
```

**Output**:
```
📊 Trade Statistics:

  total_trades             :              25
  buy_trades               :              13
  sell_trades              :              12
  avg_slippage_bps         :            2.45  (0.0245%)
  total_fees               :           12.50
  unique_symbols           :               3
```

### Offene Positionen anzeigen

```bash
python backoffice/scripts/query_analytics.py --open-positions
```

**Output**:
```
📌 Open Positions (2):

+----------+------+------+-------------+---------------+----------------+---------------------------+
| symbol   | side | size | entry_price | current_price | unrealized_pnl | opened_at                 |
+==========+======+======+=============+===============+================+===========================+
| BTCUSDT  | long | 0.10 |     50000.0 |       50500.0 |           50.0 | 2025-11-20 18:00:00+00:00 |
| ETHUSDT  | long | 1.50 |      3000.0 |        3050.0 |           75.0 | 2025-11-20 19:00:00+00:00 |
+----------+------+------+-------------+---------------+----------------+---------------------------+
```

## 🔗 Kombinierte Abfragen

Mehrere Queries gleichzeitig:

```bash
python backoffice/scripts/query_analytics.py \
  --portfolio-summary \
  --last-trades 10 \
  --open-positions
```

## 📚 Verfügbare Queries

| Query | Beschreibung | Verwendung |
|-------|-------------|-----------|
| `--last-signals N` | Zeigt letzte N Signale | `--last-signals 10` |
| `--last-trades N` | Zeigt letzte N Trades | `--last-trades 20` |
| `--portfolio-summary` | Aktueller Portfolio-Snapshot | `--portfolio-summary` |
| `--daily-pnl DAYS` | Täglicher P&L (letzte N Tage) | `--daily-pnl 7` |
| `--trade-statistics` | Gesamt-Trade-Statistiken | `--trade-statistics` |
| `--open-positions` | Aktuelle offene Positionen | `--open-positions` |

## 🗄️ Datenbank-Tabellen

Das Tool greift auf folgende Tabellen zu:

- **signals**: Trading-Signale vom Signal-Engine
- **orders**: Validierte Orders vom Risk-Manager
- **trades**: Ausgeführte Trades vom Execution-Service
- **positions**: Aktuelle Positionen (aggregiert)
- **portfolio_snapshots**: Portfolio-Performance-Tracking

## 🔧 Erweiterte Queries

Für Custom-Queries direkt in PostgreSQL:

```bash
# PostgreSQL Shell öffnen
docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare

# Beispiel-Query
SELECT symbol, COUNT(*) as num_trades, SUM(size) as total_volume
FROM trades
GROUP BY symbol
ORDER BY total_volume DESC;
```

## 📝 Query-Beispiele (SQL)

### Top-Traded Symbols (letzte 7 Tage)

```sql
SELECT
    symbol,
    COUNT(*) as num_trades,
    SUM(size) as total_volume,
    AVG(slippage_bps) as avg_slippage
FROM trades
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY symbol
ORDER BY total_volume DESC
LIMIT 10;
```

### Win-Rate Analyse (Profitable Trades)

```sql
WITH trade_pnl AS (
    SELECT
        t.id,
        t.symbol,
        t.side,
        t.price,
        t.size,
        CASE
            WHEN t.side = 'buy' THEN (p.current_price - t.price) * t.size
            WHEN t.side = 'sell' THEN (t.price - p.current_price) * t.size
        END as pnl
    FROM trades t
    LEFT JOIN positions p ON t.symbol = p.symbol
)
SELECT
    COUNT(*) as total_trades,
    COUNT(CASE WHEN pnl > 0 THEN 1 END) as winning_trades,
    COUNT(CASE WHEN pnl < 0 THEN 1 END) as losing_trades,
    ROUND(COUNT(CASE WHEN pnl > 0 THEN 1 END)::NUMERIC / COUNT(*)::NUMERIC * 100, 2) as win_rate_pct
FROM trade_pnl;
```

### Exposure-Entwicklung (Daily)

```sql
SELECT
    DATE(timestamp) as date,
    AVG(total_exposure_pct) * 100 as avg_exposure_pct,
    MAX(total_exposure_pct) * 100 as max_exposure_pct,
    AVG(open_positions) as avg_positions
FROM portfolio_snapshots
WHERE timestamp >= NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp)
ORDER BY date DESC;
```

## 🚨 Troubleshooting

### Connection refused

**Problem**: `psycopg2.OperationalError: connection refused`

**Lösung**:
```bash
# Prüfen, ob PostgreSQL läuft
docker compose ps cdb_postgres

# ENV-Variablen setzen
export POSTGRES_HOST=localhost  # oder cdb_postgres im Docker-Netzwerk
export POSTGRES_PORT=5432
```

### No data found

**Problem**: Alle Queries geben "No data found" zurück

**Lösung**:
```bash
# Prüfen, ob DB-Writer läuft
docker compose ps cdb_db_writer

# Logs prüfen
docker compose logs cdb_db_writer --tail=50

# DB-Writer neu starten
docker compose restart cdb_db_writer
```

### Permission denied

**Problem**: `permission denied for table signals`

**Lösung**:
```bash
# In PostgreSQL Shell
docker exec -it cdb_postgres psql -U postgres -d claire_de_binare

# Rechte vergeben
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO claire_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO claire_user;
```

## 📈 Next Steps

1. **Grafana-Dashboards**: Visualisierung der Queries in Grafana (Issue #31)
2. **Custom-Alerts**: Benachrichtigungen bei bestimmten Metriken
3. **Export-Funktion**: CSV/JSON-Export für externe Analyse
4. **Backtest-Replay**: Historical Data Analysis

---

**Status**: ✅ Operational
**Letzte Aktualisierung**: 2025-11-20
