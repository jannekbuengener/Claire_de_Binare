# Test Data Scripts - Quick Reference

**Zweck**: Testdaten für Grafana Dashboard Entwicklung und Testing
**Erstellt**: 2025-11-24

---

## Verfügbare Scripts

### 1. `test_data_fresh_24h.sql` ✅ EMPFOHLEN
**Verwendung**: Frische Daten für die letzten 24 Stunden generieren

**Features**:
- ✅ Schema-konform (matched aktuelle DB-Struktur)
- ✅ Verwendet `NOW() - INTERVAL` für relative Timestamps
- ✅ Inkludiert `available_balance` für portfolio_snapshots
- ✅ Realistische Trading-Szenarien

**Daten**:
- 13 Signals (letzte 24h)
- 13 Orders (12 approved, 1 rejected)
- 12 Trades
- 2 Offene Positionen (ETH +$1.36, MATIC -$1.18)
- 4 Portfolio Snapshots (Equity: $100k → $100.5k)

**Ausführen**:
```bash
docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare < test_data_fresh_24h.sql
```

---

### 2. `test_data_corrected.sql`
**Verwendung**: Schema-korrigierte Version der ursprünglichen Testdaten

**Unterschied zu `test_data_fresh_24h.sql`**:
- Weniger Daten (8 signals, 8 orders, 8 trades)
- Verwendet feste Timestamps statt `NOW()`
- Für reproduzierbare Tests

**Ausführen**:
```bash
docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare < test_data_corrected.sql
```

---

### 3. `test_data_paper_trading.sql` ⚠️ VERALTET
**Status**: Schema nicht mehr aktuell

**Probleme**:
- Verwendet `quantity` statt `size`
- Fehlt `available_balance` in portfolio_snapshots
- Wird **NICHT EMPFOHLEN**

---

## Schema-Anforderungen

### Kritische Felder (NOT NULL)

**orders**:
```sql
size             numeric(18,8) NOT NULL  -- NICHT quantity!
approved         boolean       NOT NULL
filled_size      numeric(18,8)
avg_fill_price   numeric(18,8)
```

**trades**:
```sql
size             numeric(18,8) NOT NULL  -- NICHT quantity!
execution_price  numeric(18,8) NOT NULL
fees             numeric(18,8)
slippage_bps     integer                 -- KEIN pnl Feld!
```

**positions**:
```sql
size             numeric(18,8) NOT NULL  -- NICHT quantity!
side             varchar(10)   NOT NULL  -- 'long' oder 'short'
realized_pnl     numeric(18,8)
unrealized_pnl   numeric(18,8)
```

**portfolio_snapshots**:
```sql
available_balance    numeric(18,8) NOT NULL  -- KRITISCH!
total_equity         numeric(18,8) NOT NULL
total_realized_pnl   numeric(18,8) NOT NULL
total_unrealized_pnl numeric(18,8) NOT NULL
max_drawdown_pct     numeric(5,2)  NOT NULL
total_exposure_pct   numeric(5,2)  NOT NULL
```

---

## Datenbank-Wartung

### Alte Daten löschen
```bash
docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare -c "
TRUNCATE signals, orders, trades, positions, portfolio_snapshots CASCADE;
"
```

### Aktuelle Daten prüfen
```bash
docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare -c "
SELECT 'Signals' as table, COUNT(*) as count, MAX(timestamp) as latest FROM signals
UNION ALL SELECT 'Orders', COUNT(*), MAX(created_at) FROM orders
UNION ALL SELECT 'Trades', COUNT(*), MAX(timestamp) FROM trades
UNION ALL SELECT 'Positions (open)', COUNT(*), MAX(updated_at) FROM positions WHERE size > 0
UNION ALL SELECT 'Portfolio Snapshots', COUNT(*), MAX(timestamp) FROM portfolio_snapshots;
"
```

### Datenqualität prüfen
```bash
# Trades nach Datum
docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare -c "
SELECT DATE(timestamp) as date, COUNT(*) as trades
FROM trades
GROUP BY DATE(timestamp)
ORDER BY date DESC
LIMIT 5;
"

# Order Approval Rate
docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare -c "
SELECT
    COUNT(*) as total,
    COUNT(CASE WHEN approved THEN 1 END) as approved,
    ROUND(100.0 * COUNT(CASE WHEN approved THEN 1 END) / COUNT(*), 1) as rate_pct
FROM orders
WHERE DATE(created_at) >= CURRENT_DATE - INTERVAL '7 days';
"
```

---

## Grafana Integration

### Dashboard-Queries erwarten

**Zeitbereich**: Last 7 days (standard)
```sql
WHERE DATE(timestamp) >= CURRENT_DATE - INTERVAL '7 days'
```

**Minimale Daten für alle Panels**:
- ≥1 Order (approved=true) für Order Approval Rate
- ≥1 Portfolio Snapshot für Total PnL
- ≥1 Trade für Trades per Hour
- ≥1 Position (size > 0) für Open Positions

### Troubleshooting "No data"

1. **Zeitbereich prüfen**: Sind Daten innerhalb der letzten 7 Tage?
```bash
docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare -c "
SELECT NOW() as server_time, CURRENT_DATE as current_date;
"
```

2. **Daten-Alter prüfen**: Wann wurden Daten erstellt?
```bash
docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare -c "
SELECT
    'Orders' as table,
    MIN(created_at) as oldest,
    MAX(created_at) as newest,
    COUNT(*) as total
FROM orders;
"
```

3. **Schema-Compliance prüfen**: Haben alle Felder Werte?
```bash
docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare -c "
SELECT
    COUNT(*) as total_snapshots,
    COUNT(available_balance) as with_balance,
    COUNT(total_realized_pnl) as with_realized_pnl
FROM portfolio_snapshots;
"
```

---

## Häufige Fehler

### Error: "null value in column 'available_balance' violates not-null constraint"
**Ursache**: `available_balance` fehlt im INSERT

**Fix**:
```sql
INSERT INTO portfolio_snapshots (
    total_equity,
    available_balance,  -- ← Hinzufügen
    total_realized_pnl,
    total_unrealized_pnl,
    ...
) VALUES (
    100000.00,
    99990.00,  -- ← Wert setzen
    ...
);
```

### Error: "column 'quantity' does not exist"
**Ursache**: Alte Schema-Version, nutzt `quantity` statt `size`

**Fix**: Nutze `test_data_fresh_24h.sql` statt veraltete Scripts

### Warning: "No data" in Grafana trotz Daten in DB
**Ursache**: Zeitbereich-Filter findet Daten nicht

**Fix**:
1. Prüfen: `SELECT MAX(timestamp) FROM trades;`
2. Falls älter als 7 Tage → Neue Daten laden mit `test_data_fresh_24h.sql`
3. Oder Dashboard auf "Last 365 days" umstellen

---

## Best Practices

1. **Immer `test_data_fresh_24h.sql` nutzen** für neue Test-Sessions
2. **Alte Daten löschen** vor neuem Import (TRUNCATE)
3. **Schema prüfen** mit `\d table_name` vor SQL-Anpassungen
4. **Datum in UTC halten** - Server läuft in UTC
5. **Dashboard nach Import refreshen** (Strg+R in Grafana)

---

## Siehe auch

- `GRAFANA_DASHBOARD_SETUP.md` - Vollständige Dashboard-Dokumentation
- `backoffice/docs/schema/` - Kanonische Schema-Definitionen
- `verify_dashboard_data.sql` - Datenverifikations-Script
