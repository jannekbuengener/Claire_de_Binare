# 🧪 PostgreSQL Persistence Test Guide

**Zweck**: End-to-End-Validierung der db_writer Fixes (Timestamp, Case-Mismatch, Division)

---

## 📦 **Test-Suite Übersicht**

| Datei | Zweck |
|-------|-------|
| `test_events.json` | 18 Test-Events (signals, orders, order_results, portfolio_snapshots) |
| `publish_test_events.py` | Publishes Events zu Redis |
| `validate_persistence.py` | Validiert PostgreSQL Persistenz |

---

## 🚀 **Schnellstart (5 Minuten)**

```bash
# 1. Docker Container neu starten (mit Fixes)
docker compose down
docker compose up -d --build

# 2. Warten bis alle Services healthy sind (30s)
docker compose ps

# 3. Test-Events publishen
cd /home/user/Claire_de_Binare_Cleanroom
python tests/publish_test_events.py

# 4. Persistenz validieren
python tests/validate_persistence.py
```

**Erwartung**: Alle ✅ grün, keine ❌ Fehler

---

## 📋 **Detaillierte Schritt-für-Schritt-Anleitung**

### **Schritt 1: Docker neu bauen**

```bash
# Alte Container stoppen
docker compose down

# Neu bauen (mit db_writer Fixes)
docker compose up -d --build

# Status prüfen
docker compose ps
```

**Erwartung**: Alle Services `healthy`
- ✅ cdb_postgres
- ✅ cdb_redis
- ✅ cdb_db_writer (oder cdb_execution, je nach Setup)

---

### **Schritt 2: Logs prüfen (optional)**

```bash
# db_writer Logs
docker compose logs cdb_db_writer --tail=20 -f

# Erwartung:
# ✅ "Connected to Redis"
# ✅ "Connected to PostgreSQL"
# ✅ "Subscribed to channels: signals, orders, ..."
```

**Tipp**: `Ctrl+C` zum Beenden

---

### **Schritt 3: ENV-Variablen setzen**

```bash
# Falls .env nicht existiert, aus .env.example kopieren
cp .env.example .env

# ENV-Variablen laden (für Python-Scripts)
export $(cat .env | grep -v '^#' | xargs)

# Oder für diese Session:
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=claire_redis_secret_2024
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=claire_de_binare
export POSTGRES_USER=claire_user
export POSTGRES_PASSWORD=<your_postgres_password>
```

---

### **Schritt 4: Test-Events publishen**

```bash
cd /home/user/Claire_de_Binare_Cleanroom
python tests/publish_test_events.py
```

**Output (Beispiel)**:
```
============================================================
🧪 Claire de Binare - Test Event Publisher
============================================================

📂 Loading test events...
✅ Loaded 18 test events:
   - signals: 5
   - orders: 5
   - order_results: 5
   - portfolio_snapshots: 3

🔌 Connecting to Redis...
✅ Connected to Redis at localhost:6379

🔍 Checking if db_writer is listening...
  ✅ Channel 'signals': 1 subscriber(s)
  ✅ Channel 'orders': 1 subscriber(s)
  ✅ Channel 'order_results': 1 subscriber(s)
  ✅ Channel 'portfolio_snapshots': 1 subscriber(s)

============================================================
📤 Publish events to Redis? [y/N]: y

🚀 Publishing events...

📤 Publishing 5 signals to channel 'signals'...
  ✅ [1/5] Published: BTCUSDT BUY
  ✅ [2/5] Published: ETHUSDT SELL
  ...

✅ Published 18/18 events successfully!
```

**Hinweis**: Falls "No subscribers" → db_writer läuft nicht!

---

### **Schritt 5: PostgreSQL validieren**

```bash
python tests/validate_persistence.py
```

**Output (Beispiel - ERFOLG)**:
```
============================================================
📊 VALIDATING: orders
============================================================
✅ Total orders: 5

📋 Latest 5 orders:
ID    Symbol     Side   Approved   Status     Created At
--------------------------------------------------------------------------------
✅ 5     ETHUSDT    long   ❌ No       rejected   2024-11-22 14:15:30
✅ 4     BTCUSDT    buy    ❌ No       rejected   2024-11-22 14:15:20
✅ 3     SOLUSDT    buy    ✅ Yes      submitted  2024-11-22 14:15:10
✅ 2     ETHUSDT    sell   ✅ Yes      pending    2024-11-22 14:15:00
✅ 1     BTCUSDT    buy    ✅ Yes      pending    2024-11-22 14:14:50

✅ All orders have lowercase side ← FIX WORKING!

============================================================
📊 VALIDATING: portfolio_snapshots
============================================================
✅ Total snapshots: 3

📋 Latest 5 snapshots:
ID    Equity       Exposure %   Daily PnL    Timestamp
----------------------------------------------------------------------
✅ 3     98500.00     0.3000       -1500.00     2024-11-22 14:16:40
✅ 2     102500.00    0.0800       2500.00      2024-11-22 14:15:00
✅ 1     100000.00    0.0500       0.00         2024-11-22 14:13:20

✅ All exposure values look correct ← FIX WORKING!
```

**Output (Beispiel - FEHLER)**:
```
❌ CRITICAL: Found 5 orders with UPPERCASE side!
   This means the fix didn't work - check db_writer.py line 200

⚠️  3     98500.00     0.0005       ← SUSPICIOUS!
❌ WARNING: Found 1 snapshots with suspicious exposure values!
   Expected: 0.05 (5%), 0.30 (30%)
   Found:    0.0005 (too small!)
   This indicates the double-division bug might still exist!
```

---

## 📊 **Test-Matrix (was wird getestet)**

| Test-Case | Event-Type | Feature | Expected Result |
|-----------|-----------|---------|-----------------|
| **TC-01** | signal | UPPERCASE side ("BUY") | DB: side='buy' (lowercase) ✅ |
| **TC-02** | signal | lowercase side ("buy") | DB: side='buy' ✅ |
| **TC-03** | signal | Min confidence (0.01) | DB: 0.01 ✅ |
| **TC-04** | signal | Max confidence (0.99) | DB: 0.99 ✅ |
| **TC-05** | order | UPPERCASE side ("BUY") | DB: side='buy' ✅ |
| **TC-06** | order | Alias side ("LONG") | DB: side='long' ✅ |
| **TC-07** | order | Rejected order | DB: approved=false ✅ |
| **TC-08** | order | Alternative field ("size") | DB: accepts both "size" and "quantity" ✅ |
| **TC-09** | trade | lowercase side ("buy") | DB: side='buy' ✅ |
| **TC-10** | trade | Slippage calculation | DB: slippage_bps calculated ✅ |
| **TC-11** | trade | UPPERCASE status ("FILLED") | DB: status='filled' ✅ |
| **TC-12** | snapshot | Exposure 5% (0.05) | DB: 0.05 (NOT 0.0005!) ✅ |
| **TC-13** | snapshot | High exposure 30% (0.30) | DB: 0.30 ✅ |
| **TC-14** | snapshot | Alternative field ("open_positions") | DB: accepts both ✅ |
| **TC-15** | All | Unix timestamp (int) | DB: TIMESTAMPTZ ✅ |

---

## 🔍 **Manuelle PostgreSQL-Prüfung**

Falls du direkt in PostgreSQL schauen willst:

```bash
# In PostgreSQL einloggen
docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare
```

```sql
-- Alle Tabellen zählen
SELECT
    'signals' AS table_name, COUNT(*) AS rows FROM signals
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'trades', COUNT(*) FROM trades
UNION ALL
SELECT 'portfolio_snapshots', COUNT(*) FROM portfolio_snapshots;

-- Orders prüfen (side sollte lowercase sein!)
SELECT id, symbol, side, approved, status
FROM orders
ORDER BY id DESC
LIMIT 5;

-- Erwartung: side = 'buy', 'sell', 'long', 'short' (lowercase!)

-- Portfolio Snapshots prüfen (exposure sollte 0.0-1.0 sein!)
SELECT id, total_equity, total_exposure_pct, daily_pnl
FROM portfolio_snapshots
ORDER BY id DESC
LIMIT 5;

-- Erwartung: total_exposure_pct = 0.05, 0.08, 0.30 (NICHT 0.0005!)

-- Signals prüfen (timestamps sollten TIMESTAMPTZ sein!)
SELECT id, symbol, signal_type, timestamp
FROM signals
ORDER BY id DESC
LIMIT 5;

-- Erwartung: timestamp = '2024-11-22 14:14:50+00' (nicht Unix int!)

-- PostgreSQL verlassen
\q
```

---

## ✅ **Success Criteria (alle müssen erfüllt sein)**

Nach erfolgreichen Tests sollten folgende Bedingungen gelten:

1. ✅ **Signals**: Mindestens 5 Rows, `signal_type` lowercase ('buy'/'sell')
2. ✅ **Orders**: Mindestens 5 Rows, `side` lowercase ('buy'/'sell'/'long'/'short')
3. ✅ **Trades**: Mindestens 4 Rows (1 rejected), `side` lowercase
4. ✅ **Portfolio Snapshots**: Mindestens 3 Rows, `total_exposure_pct` zwischen 0.0-1.0 (z.B. 0.05, 0.30)
5. ✅ **Timestamps**: Alle als TIMESTAMPTZ gespeichert (nicht Unix int)
6. ✅ **Keine Constraint-Violations** in db_writer Logs

---

## ❌ **Troubleshooting**

### **Problem 1: "No subscribers" beim Publishen**

**Ursache**: db_writer Service läuft nicht oder ist nicht subscribed

**Lösung**:
```bash
# Prüfe ob db_writer läuft
docker compose ps cdb_db_writer

# Logs prüfen
docker compose logs cdb_db_writer --tail=50

# Erwartung:
# "Subscribed to channels: signals, orders, ..."
```

---

### **Problem 2: Orders/Trades mit UPPERCASE side in DB**

**Ursache**: Fix wurde nicht deployed oder überschrieben

**Lösung**:
```bash
# Prüfe ob Fix im Container ist
docker exec -it cdb_db_writer cat /app/db_writer.py | grep -A2 'data.get("side"'

# Sollte zeigen:
# data.get("side", "").lower(),  # Convert to lowercase

# Falls nicht: Container neu bauen
docker compose up -d --build cdb_db_writer
```

---

### **Problem 3: total_exposure_pct = 0.0005 (zu klein)**

**Ursache**: Doppelte Division bug nicht gefixt

**Lösung**:
```bash
# Prüfe Fix in db_writer.py
docker exec -it cdb_db_writer cat /app/db_writer.py | grep -A1 'total_exposure_pct'

# Sollte zeigen:
# data.get("total_exposure_pct", 0.0),  # Event already sends decimal

# NICHT:
# data.get("total_exposure_pct", 0) / 100.0

# Falls falsch: Container neu bauen
docker compose up -d --build cdb_db_writer
```

---

### **Problem 4: Keine Events in DB**

**Ursache**: Events wurden nicht gepublisht oder db_writer crashed

**Lösung**:
```bash
# 1. Prüfe Redis
docker compose logs cdb_redis --tail=20

# 2. Prüfe db_writer
docker compose logs cdb_db_writer --tail=50

# Suche nach Fehlern:
# - "Failed to persist"
# - "Connection refused"
# - "violates check constraint"

# 3. Events nochmal publishen
python tests/publish_test_events.py
```

---

## 📚 **Weiterführende Infos**

- **db_writer.py**: `/home/user/Claire_de_Binare_Cleanroom/backoffice/services/db_writer/db_writer.py`
- **DATABASE_SCHEMA.sql**: `/home/user/Claire_de_Binare_Cleanroom/backoffice/docs/DATABASE_SCHEMA.sql`
- **Test-Events**: `/home/user/Claire_de_Binare_Cleanroom/tests/test_events.json`

---

**Viel Erfolg! 🚀**
