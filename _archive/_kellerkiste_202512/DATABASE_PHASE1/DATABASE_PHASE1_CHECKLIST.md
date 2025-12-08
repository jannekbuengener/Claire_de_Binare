# Phase 1 Validation Checklist - Claire de Binare
**Start**: Tag 0 (Jetzt)
**Dauer**: 1-2 Stunden
**Ziel**: Bestehende 5 Tabellen validieren

---

## ✅ PRE-FLIGHT CHECKS

### 1. ENV-Variablen prüfen
```bash
# Prüfe ob .env existiert
ls -la .env

# Wichtige Variablen checken (ohne Werte anzuzeigen!)
grep -E "^(POSTGRES|REDIS)" .env | cut -d= -f1
```

**Erwartung**:
```
POSTGRES_HOST
POSTGRES_PORT
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_DB
REDIS_HOST
REDIS_PORT
REDIS_PASSWORD
REDIS_DB
```

---

### 2. Container starten
```bash
# Alle Container starten
docker compose up -d

# Warten bis healthy
sleep 30

# Status prüfen
docker compose ps
```

**Erwartung**: Alle Container `healthy` (besonders postgres + redis)

---

### 3. PostgreSQL Schema validieren
```bash
# Tabellen auflisten
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "\dt"
```

**Erwartung - 6 Tabellen**:
```
 public | orders              | table | claire_user
 public | portfolio_snapshots | table | claire_user
 public | positions           | table | claire_user
 public | schema_version      | table | claire_user
 public | signals             | table | claire_user
 public | trades              | table | claire_user
```

---

### 4. Schema-Version prüfen
```bash
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c \
  "SELECT * FROM schema_version;"
```

**Erwartung**:
```
 version |        applied_at         |              description
---------+---------------------------+----------------------------------------
 1.0.0   | 2025-11-20 XX:XX:XX+00    | Initial schema: signals, orders, ...
```

---

### 5. Initial Portfolio validieren
```bash
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c \
  "SELECT total_equity, available_balance, open_positions FROM portfolio_snapshots ORDER BY timestamp DESC LIMIT 1;"
```

**Erwartung**:
```
 total_equity | available_balance | open_positions
--------------+-------------------+----------------
    100000.00 |         100000.00 |              0
```

---

### 6. Redis Connectivity prüfen
```bash
# Ping-Test
docker exec cdb_redis redis-cli -a "$REDIS_PASSWORD" ping

# Topic-Listen-Test (Ctrl+C nach 5 Sekunden)
docker exec cdb_redis redis-cli -a "$REDIS_PASSWORD" SUBSCRIBE market_data
```

**Erwartung**: `PONG` + Topic subscribable

---

## 🧪 WRITE-TESTS (Manuell oder via Script)

### Test 1: Signal INSERT
```sql
-- Via psql:
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "
INSERT INTO signals (symbol, signal_type, price, confidence, metadata) 
VALUES ('BTCUSDT', 'buy', 50000.00, 0.85, '{\"test\": true}'::jsonb)
RETURNING id, symbol, signal_type;
"
```

**Erwartung**: Row inserted, ID returned

---

### Test 2: Order INSERT
```sql
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "
INSERT INTO orders (signal_id, symbol, side, order_type, price, size, approved) 
VALUES (1, 'BTCUSDT', 'buy', 'market', 50000.00, 0.001, true)
RETURNING id, symbol, approved;
"
```

**Erwartung**: Order inserted mit signal_id foreign key

---

### Test 3: Trade INSERT
```sql
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "
INSERT INTO trades (order_id, symbol, side, price, size, execution_price, slippage_bps, fees) 
VALUES (1, 'BTCUSDT', 'buy', 50000.00, 0.001, 50005.00, 10, 0.50)
RETURNING id, symbol, slippage_bps;
"
```

**Erwartung**: Trade inserted

---

### Test 4: Position UPSERT
```sql
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "
INSERT INTO positions (symbol, side, size, entry_price, current_price, unrealized_pnl)
VALUES ('BTCUSDT', 'long', 0.001, 50000.00, 50005.00, 0.05)
ON CONFLICT (symbol) DO UPDATE 
SET size = positions.size + EXCLUDED.size,
    unrealized_pnl = EXCLUDED.unrealized_pnl,
    updated_at = CURRENT_TIMESTAMP
RETURNING id, symbol, side, unrealized_pnl;
"
```

**Erwartung**: Position inserted or updated

---

### Test 5: Portfolio Snapshot INSERT
```sql
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "
INSERT INTO portfolio_snapshots 
(total_equity, available_balance, daily_pnl, total_exposure_pct, open_positions)
VALUES (100050.00, 99950.00, 50.00, 0.05, 1)
RETURNING id, total_equity, daily_pnl;
"
```

**Erwartung**: Snapshot inserted

---

## 📊 VALIDATE DATA

### Count Test-Data
```bash
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "
SELECT 
  'signals' AS table_name, COUNT(*) AS count FROM signals
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'trades', COUNT(*) FROM trades
UNION ALL
SELECT 'positions', COUNT(*) FROM positions
UNION ALL
SELECT 'portfolio_snapshots', COUNT(*) FROM portfolio_snapshots
ORDER BY table_name;
"
```

**Erwartung nach Tests**:
```
 table_name          | count
---------------------+-------
 orders              |     1
 portfolio_snapshots |     2  (initial + test)
 positions           |     1
 signals             |     1
 trades              |     1
```

---

## 🎯 SUCCESS CRITERIA

✅ **Phase 1 gilt als erfolgreich wenn**:

- [ ] Alle 6 Tabellen existieren
- [ ] Schema-Version = 1.0.0
- [ ] Initial Portfolio vorhanden (100k USDT)
- [ ] Redis pingable
- [ ] Alle 5 INSERT-Tests erfolgreich
- [ ] Keine Foreign-Key-Errors
- [ ] Performance <1ms pro INSERT
- [ ] Container bleiben healthy

---

## 🚨 TROUBLESHOOTING

### Problem: Schema nicht geladen
```bash
# Volume löschen und neu erstellen
docker compose down -v
docker compose up -d cdb_postgres
# Warten 30 Sekunden, dann nochmal prüfen
```

### Problem: Redis AUTH failed
```bash
# Password prüfen
echo $REDIS_PASSWORD

# Wenn leer, .env laden:
source .env  # Linux/Mac
# Oder .env.example kopieren zu .env
```

### Problem: PostgreSQL nicht erreichbar
```bash
# Logs prüfen
docker compose logs cdb_postgres | grep "ready to accept"

# Sollte zeigen: "database system is ready to accept connections"
```

---

## ⏭️ NEXT STEPS

### Nach erfolgreicher Validierung:

1. **Cleanup Test-Data** (optional):
```sql
DELETE FROM trades WHERE id = 1;
DELETE FROM orders WHERE id = 1;
DELETE FROM signals WHERE id = 1;
DELETE FROM positions WHERE symbol = 'BTCUSDT';
DELETE FROM portfolio_snapshots WHERE id > 1;
```

2. **Entscheidung: Phase 2?**
   - ✅ JA → Starte Phase 2 Implementation (risk_events + execution_analysis)
   - ⏸️ ERST PAPER-TRADING → Sammle 1-2 Tage Daten, dann Phase 2

3. **Dokumentiere Ergebnis**:
   - Update `DATABASE_ENHANCEMENT_ROADMAP.md` Phase 1 Status
   - Notiere Probleme/Learnings

---

**Status**: 📋 Checklist ready - Zeit für Validation! ⏱️
