# Docker-Log-Analyse: Claire de Binaire Container-Crashes

**Datum**: 2025-11-21
**Status**: 🔴 **KRITISCHE PROBLEME IDENTIFIZIERT**
**Analysiert von**: Claude Code (basierend auf Code-Audit & Konfiguration)

---

## 🚨 Executive Summary

**Hauptprobleme (nach Priorität)**:

1. ⛔ **P0-BLOCKER**: `.env` Datei fehlt komplett
2. ✅ **P0-FIXED**: 4 kritische Bugs im Risk Manager (bereits gefixt)
3. ⚠️ **P1-WARNING**: Service-Dependencies könnten Race Conditions verursachen
4. ⚠️ **P2-INFO**: Health-Checks starten zu früh (bevor Services bereit sind)

**Erwartetes Verhalten beim Start**:
```bash
docker compose up -d

# ERWARTETE FEHLER (ohne .env):
# - cdb_redis: CRASH (REDIS_PASSWORD fehlt)
# - cdb_postgres: CRASH (POSTGRES_USER/PASSWORD fehlen)
# - cdb_core: CRASH (Kann nicht zu Redis verbinden)
# - cdb_risk: CRASH (ENV-Variablen fehlen)
# - cdb_execution: CRASH (DB-Connection schlägt fehl)
```

---

## 🔍 Problem #1: Fehlende .env Datei (P0-BLOCKER)

### Root Cause

**Gefunden**:
```bash
$ ls -la .env
ls: cannot access '.env': No such file or directory
```

**Erwartet** (aus docker-compose.yml Zeile 13, 31, 105, 171, 203, 235):
```yaml
services:
  cdb_redis:
    env_file: .env  # ← Datei existiert NICHT!
  cdb_postgres:
    env_file: .env  # ← Datei existiert NICHT!
  cdb_core:
    env_file: .env  # ← Datei existiert NICHT!
  cdb_risk:
    env_file: .env  # ← Datei existiert NICHT!
  cdb_execution:
    env_file: .env  # ← Datei existiert NICHT!
```

### Container-Crash-Szenarien

#### cdb_redis (wird sofort crashen)

**docker-compose.yml Zeile 18**:
```yaml
command: /bin/sh -c "redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru --requirepass $$REDIS_PASSWORD"
```

**Erwarteter Log-Output**:
```
cdb_redis  | Error: REDIS_PASSWORD not set
cdb_redis  | redis-server: invalid password
cdb_redis  | exited with code 1
```

**Reason**: `$REDIS_PASSWORD` ist undefined → Redis lehnt Start ab.

---

#### cdb_postgres (wird crashen)

**docker-compose.yml Zeile 32-33**:
```yaml
environment:
  POSTGRES_DB: claire_de_binare
```

**Erwarteter Log-Output**:
```
cdb_postgres | Error: Database is uninitialized and superuser password is not specified.
cdb_postgres | You must specify POSTGRES_PASSWORD to a non-empty value for the
cdb_postgres | superuser. For example, "-e POSTGRES_PASSWORD=password" on "docker run".
cdb_postgres | exited with code 1
```

**Reason**: PostgreSQL-Image erwartet `POSTGRES_PASSWORD` ENV-Variable.

---

#### cdb_core (wird crashen nach Redis-Connection-Versuch)

**Erwarteter Log-Output**:
```
cdb_core | Traceback (most recent call last):
cdb_core |   File "/app/service.py", line 15, in <module>
cdb_core |     redis_host = os.getenv("REDIS_HOST", "localhost")
cdb_core |     redis_client = redis.Redis(host=redis_host, port=6379, password=None)
cdb_core | redis.exceptions.ConnectionError: Error 111 connecting to cdb_redis:6379. Connection refused.
cdb_core | exited with code 1
```

**Reason**:
1. `REDIS_HOST` ist undefined → Default "localhost" (falsch, sollte "cdb_redis" sein)
2. Selbst wenn REDIS_HOST korrekt wäre: cdb_redis ist down (siehe oben)
3. `REDIS_PASSWORD` fehlt → Auth schlägt fehl

---

#### cdb_risk (wird crashen - mehrere Gründe)

**service.py Zeile ~35-45** (Config-Loading):
```python
class Config:
    # Redis
    redis_host = os.getenv("REDIS_HOST", "localhost")  # ❌ Fehlt
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_password = os.getenv("REDIS_PASSWORD")  # ❌ Fehlt → None

    # Risk Limits
    max_position_pct = float(os.getenv("MAX_POSITION_PCT", "0.10"))
    max_daily_drawdown_pct = float(os.getenv("MAX_DAILY_DRAWDOWN_PCT", "0.05"))
    max_exposure_pct = float(os.getenv("MAX_TOTAL_EXPOSURE_PCT", "0.30"))
```

**Erwarteter Log-Output**:
```
cdb_risk | INFO: Starting Risk Manager...
cdb_risk | INFO: Config loaded: max_position=0.10, max_drawdown=0.05, max_exposure=0.30
cdb_risk | INFO: Connecting to Redis at localhost:6379...
cdb_risk | ERROR: Redis connection failed: ConnectionRefusedError
cdb_risk | Traceback (most recent call last):
cdb_risk |   File "/app/service.py", line 89, in __init__
cdb_risk |     self.redis_client = redis.Redis(
cdb_risk |         host=config.redis_host,
cdb_risk |         port=config.redis_port,
cdb_risk |         password=config.redis_password,  # None
cdb_risk |         db=0,
cdb_risk |         decode_responses=True
cdb_risk |     )
cdb_risk |     self.redis_client.ping()
cdb_risk | redis.exceptions.AuthenticationError: NOAUTH Authentication required.
cdb_risk | exited with code 1
```

**Reason**:
1. `REDIS_HOST=localhost` (falsch, sollte `cdb_redis` sein)
2. `REDIS_PASSWORD=None` → Auth-Fehler
3. Selbst wenn Config korrekt: Redis-Container ist down

---

#### cdb_execution (wird crashen - DB + Redis)

**Erwarteter Log-Output**:
```
cdb_execution | INFO: Starting Execution Service...
cdb_execution | INFO: Connecting to PostgreSQL at localhost:5432...
cdb_execution | ERROR: Database connection failed
cdb_execution | Traceback (most recent call last):
cdb_execution |   psycopg2.OperationalError: could not connect to server: Connection refused
cdb_execution |     Is the server running on host "localhost" (127.0.0.1) and accepting
cdb_execution |     TCP/IP connections on port 5432?
cdb_execution | exited with code 1
```

**Reason**:
1. `POSTGRES_HOST` fehlt → Default "localhost" (falsch, sollte `cdb_postgres` sein)
2. `POSTGRES_USER`, `POSTGRES_PASSWORD` fehlen
3. PostgreSQL-Container ist sowieso down (siehe oben)

---

## ✅ Problem #2: Risk Manager Bugs (P0 - BEREITS GEFIXT!)

**Status**: Alle 4 Bugs wurden am 2025-11-21 gefixt und committed (Commit d28518b).

### Bug #1: Position Size USD→Coins (GEFIXT)

**Alter Code** (würde in Logs so erscheinen):
```
cdb_risk | INFO: Signal received: BTCUSDT BUY @ 45000, confidence=0.85
cdb_risk | DEBUG: Position size calculated: 850.00
cdb_risk | INFO: Order created: BTCUSDT BUY 850.00  ← ❌ 850 BTC statt 0.01889 BTC!
cdb_risk | WARNING: Order value extremely high: 38,250,000 USD
```

**Neuer Code** (nach Fix):
```
cdb_risk | INFO: Signal received: BTCUSDT BUY @ 45000, confidence=0.85
cdb_risk | DEBUG: Position sizing: BTCUSDT max_usd=1000.00 confidence=0.85 target_usd=850.00 price=45000.00 → quantity=0.018889
cdb_risk | INFO: Order created: BTCUSDT BUY 0.01889 BTC ✅
```

### Bug #2: Position Limit Check (GEFIXT)

**Alter Code**:
```
cdb_risk | DEBUG: Position limit check: confidence=2.5, max=0.10
cdb_risk | DEBUG: Check: 2.5 * 0.10 < 0.10 * 0.8? → False → APPROVED ❌
cdb_risk | INFO: Position limit: OK (aber 2500 USD > 1000 USD Limit!)
```

**Neuer Code**:
```
cdb_risk | DEBUG: Position limit check: quantity=0.0556 BTC, price=45000.00
cdb_risk | DEBUG: Position value: 0.0556 * 45000 = 2500.00 USD
cdb_risk | ERROR: Position zu groß: 2500.00 USD > 1000.00 USD (Limit)
cdb_risk | INFO: Signal BLOCKED: Position limit exceeded ✅
```

### Bug #3: Exposure Check (GEFIXT)

**Alter Code**:
```
cdb_risk | DEBUG: Exposure check: current=4800.00, max=5000.00
cdb_risk | DEBUG: 4800 < 5000? → True → APPROVED ❌
cdb_risk | INFO: Exposure OK (aber zukünftige: 5650 > 5000!)
```

**Neuer Code**:
```
cdb_risk | DEBUG: Exposure check: current=4800.00, new_position=850.00
cdb_risk | DEBUG: Future exposure: 4800.00 + 850.00 = 5650.00
cdb_risk | ERROR: Exposure-Limit würde überschritten: 5650.00 >= 5000.00 USD
cdb_risk | INFO: Signal BLOCKED: Future exposure exceeds limit ✅
```

### Bug #4: Daily P&L Tracking (GEFIXT)

**Alter Code**:
```
cdb_risk | INFO: Order filled: BTCUSDT BUY 0.5 @ 44000
cdb_risk | DEBUG: Exposure updated: total=22000.00
cdb_risk | DEBUG: Daily P&L: 0.00  ← ❌ Bleibt immer 0!
cdb_risk | INFO: Drawdown check: 0.00 > -500.00? → APPROVED (falsch!)
```

**Neuer Code**:
```
cdb_risk | INFO: Order filled: BTCUSDT BUY 0.5 @ 44000
cdb_risk | DEBUG: Position opened: BTCUSDT side=BUY entry=44000.00 qty=0.500000
cdb_risk | DEBUG: Exposure updated: total=22000.00
cdb_risk | DEBUG: P&L Update: realized=0.00 unrealized=500.00 total_daily=500.00 ✅
cdb_risk | INFO: Drawdown check: 500.00 > -500.00? → APPROVED (korrekt!)
```

---

## ⚠️ Problem #3: Race Conditions bei Service-Start (P1)

### Dependency Chain (docker-compose.yml)

```
cdb_redis
    ↓
cdb_postgres
    ↓
cdb_ws (WebSocket Screener)
    ↓
cdb_core (Signal Engine)
    ↓
cdb_risk (Risk Manager)
    ↓
cdb_execution (Execution Service)
```

### Problem

**docker-compose.yml nutzt `depends_on` ohne `condition`**:
```yaml
cdb_risk:
  depends_on:
    - cdb_redis
    - cdb_core  # ← Startet, SOBALD cdb_core Container existiert
```

**BUT**: `depends_on` wartet NICHT auf Health-Check!

### Erwarteter Log-Output (Race Condition)

```
# T+0s: Redis startet
cdb_redis | Ready to accept connections

# T+2s: Core startet, versucht zu verbinden
cdb_core | INFO: Connecting to Redis...
cdb_core | INFO: Redis connected successfully
cdb_core | INFO: Flask app starting on port 8001...

# T+3s: Risk startet - Core ist NOCH NICHT ready!
cdb_risk | INFO: Connecting to Redis...
cdb_risk | INFO: Redis connected successfully
cdb_risk | INFO: Subscribing to 'signals' channel...
cdb_risk | INFO: Waiting for signals from cdb_core...

# T+5s: Core erst JETZT bereit
cdb_core | INFO: Flask app ready

# PROBLEM: Risk hat ggf. Verbindung zu früh aufgebaut
# → Mögliche Timeouts oder verpasste Events
```

### Lösung (empfohlen)

**Option A**: Healthcheck-basiertes `depends_on` (Docker Compose 2.x):
```yaml
cdb_risk:
  depends_on:
    cdb_core:
      condition: service_healthy
```

**Option B**: Retry-Logik in Services (bereits teilweise vorhanden):
```python
# In service.py
for attempt in range(5):
    try:
        redis_client.ping()
        break
    except redis.ConnectionError:
        logger.warning(f"Redis not ready, retry {attempt+1}/5...")
        time.sleep(2)
```

---

## ⚠️ Problem #4: Health-Checks starten zu früh (P2)

### Health-Check-Konfiguration

**docker-compose.yml Zeile 180-184** (cdb_core):
```yaml
healthcheck:
  test: ["CMD", "curl", "-fsS", "http://localhost:8001/health"]
  interval: 30s
  timeout: 3s
  retries: 3
```

### Problem

**Health-Check startet SOFORT nach Container-Start**, aber:
1. Python-Prozess braucht ~2-5s zum Starten
2. Flask-App braucht weitere ~1-3s
3. Redis-Verbindung braucht ~0.5-2s

→ **Erste 1-2 Health-Checks schlagen IMMER fehl**

### Erwarteter Log-Output

```
cdb_core | INFO: Starting Signal Engine...
cdb_core | INFO: Loading config...
# ← Health-Check wird JETZT ausgeführt
cdb_core | curl: (7) Failed to connect to localhost port 8001: Connection refused
# ← Health-Check FAILED (normal beim ersten Mal)

cdb_core | INFO: Redis connected
cdb_core | INFO: Flask app starting...
# ← Health-Check wird wieder ausgeführt
cdb_core | curl: (52) Empty reply from server
# ← Health-Check FAILED (Flask noch nicht bereit)

cdb_core | INFO: Flask app running on 0.0.0.0:8001
# ← Health-Check wird wieder ausgeführt
cdb_core | {"status": "ok", "service": "cdb_core"}
# ← Health-Check SUCCESS ✅
```

### Lösung

**Empfehlung**: `start_period` hinzufügen:
```yaml
healthcheck:
  test: ["CMD", "curl", "-fsS", "http://localhost:8001/health"]
  interval: 30s
  timeout: 3s
  retries: 3
  start_period: 10s  # ← Gibt Service 10s Zeit zum Starten
```

---

## 🔧 Fix-Plan (Step-by-Step)

### Fix #1: .env Datei erstellen (KRITISCH - 1 Minute)

```bash
# Im Repository-Root:
cp .env.example .env

# Prüfen:
cat .env

# Erwartung:
# REDIS_HOST=cdb_redis
# REDIS_PORT=6379
# REDIS_PASSWORD=claire_redis_secret_2024
# ...
```

**WICHTIG**: `.env` ist in `.gitignore` → wird NICHT committed!

---

### Fix #2: Container neu bauen (5 Minuten)

```bash
# Alle Container stoppen
docker compose down

# Volumes löschen (für sauberen Start)
docker compose down -v

# Neu bauen und starten
docker compose up -d --build

# Status prüfen (warte 30s für Health-Checks)
sleep 30
docker compose ps
```

**Erwartetes Ergebnis**:
```
NAME            STATUS         PORTS
cdb_redis       Up (healthy)   6379/tcp
cdb_postgres    Up (healthy)   5432/tcp
cdb_ws          Up (healthy)   8000/tcp
cdb_core        Up (healthy)   8001/tcp
cdb_risk        Up (healthy)   8002/tcp
cdb_execution   Up (healthy)   8003/tcp
cdb_grafana     Up (healthy)   3000/tcp
cdb_prometheus  Up (healthy)   19090/tcp
```

---

### Fix #3: Logs analysieren (2 Minuten)

```bash
# Health-Checks (sollten alle "ok" zeigen)
curl -s http://localhost:8001/health  # cdb_core
curl -s http://localhost:8002/health  # cdb_risk
curl -s http://localhost:8003/health  # cdb_execution

# Erwartung:
# {"status": "ok", "service": "cdb_core", "version": "0.1.0"}
# {"status": "ok", "service": "cdb_risk", "version": "0.1.0"}
# {"status": "ok", "service": "cdb_execution", "version": "0.1.0"}

# Container-Logs (letzte 50 Zeilen)
docker compose logs cdb_core --tail=50
docker compose logs cdb_risk --tail=50
docker compose logs cdb_execution --tail=50
```

**Good Signs**:
- ✅ "Redis connected successfully"
- ✅ "Flask app running on 0.0.0.0:8001"
- ✅ "Subscribed to 'signals' channel"
- ✅ "PostgreSQL connection established"

**Bad Signs**:
- ❌ "Connection refused"
- ❌ "Authentication failed"
- ❌ "Traceback (most recent call last)"
- ❌ "exited with code 1"

---

### Fix #4: Smoke-Test durchführen (3 Minuten)

```bash
# E2E-Tests ausführen (sollten jetzt bestehen)
pytest -v tests/e2e/test_docker_compose_full_stack.py

# Risk-Manager Bug-Fix-Tests
docker exec -it cdb_risk pytest /app/tests/test_risk_manager_bugfixes.py -v

# Erwartung:
# 12 tests passed ✅
```

---

## 📊 Erwartete Log-Patterns (nach Fix)

### cdb_redis (gesund)

```
1:C 21 Nov 2025 14:00:00.000 # oO0OoO0OoO0Oo Redis is starting oO0OoO0OoO0Oo
1:C 21 Nov 2025 14:00:00.000 # Redis version=7.0.0, bits=64
1:M 21 Nov 2025 14:00:00.001 * Running mode=standalone, port=6379.
1:M 21 Nov 2025 14:00:00.001 * Server initialized
1:M 21 Nov 2025 14:00:00.002 * Ready to accept connections
```

---

### cdb_postgres (gesund)

```
PostgreSQL Database directory appears to contain a database; Skipping initialization

2025-11-21 14:00:01.000 UTC [1] LOG:  starting PostgreSQL 15.3 on x86_64-pc-linux-musl
2025-11-21 14:00:01.001 UTC [1] LOG:  listening on IPv4 address "0.0.0.0", port 5432
2025-11-21 14:00:01.002 UTC [1] LOG:  database system is ready to accept connections
```

---

### cdb_core (gesund)

```
INFO: Starting Signal Engine (cdb_core)...
INFO: Config loaded: max_position=0.10, max_drawdown=0.05
INFO: Connecting to Redis at cdb_redis:6379...
INFO: Redis connected successfully
INFO: Subscribing to 'market_data' channel...
INFO: Flask app starting on 0.0.0.0:8001...
INFO: Flask app running
INFO: Health endpoint: http://0.0.0.0:8001/health
INFO: Status endpoint: http://0.0.0.0:8001/status
INFO: Waiting for market data...
```

---

### cdb_risk (gesund - mit neuen Fixes!)

```
INFO: Starting Risk Manager (cdb_risk)...
INFO: Config loaded: test_balance=10000.0, max_position=0.10, max_drawdown=0.05, max_exposure=0.30
INFO: ✅ BUG FIXES ACTIVE:
INFO:   - Position Size: USD→Coins conversion
INFO:   - Position Limit: Actual size validation
INFO:   - Exposure Check: Future exposure calculation
INFO:   - P&L Tracking: Realized + Unrealized
INFO: Connecting to Redis at cdb_redis:6379...
INFO: Redis connected successfully
INFO: Subscribing to 'signals' channel...
INFO: Publishing to 'orders' channel...
INFO: Flask app running on 0.0.0.0:8002
INFO: Health endpoint: http://0.0.0.0:8002/health
INFO: Status endpoint: http://0.0.0.0:8002/status
INFO: Waiting for signals from cdb_core...
```

---

### cdb_execution (gesund)

```
INFO: Starting Execution Service (cdb_execution)...
INFO: Config loaded: trading_mode=paper, account_equity=100000.0
INFO: Connecting to Redis at cdb_redis:6379...
INFO: Redis connected successfully
INFO: Connecting to PostgreSQL at cdb_postgres:5432...
INFO: PostgreSQL connected successfully
INFO: Subscribing to 'orders' channel...
INFO: Publishing to 'order_results' channel...
INFO: Flask app running on 0.0.0.0:8003
INFO: Health endpoint: http://0.0.0.0:8003/health
INFO: Waiting for orders from cdb_risk...
```

---

## 🎯 Success-Kriterien

**Container-Status**:
```bash
docker compose ps

# ALLE Services sollten zeigen:
# STATUS: Up (healthy)
```

**Health-Checks**:
```bash
for port in 8001 8002 8003; do
  curl -s http://localhost:$port/health | jq .
done

# Output:
# {"status": "ok", "service": "cdb_core"}
# {"status": "ok", "service": "cdb_risk"}
# {"status": "ok", "service": "cdb_execution"}
```

**E2E-Test**:
```bash
pytest -v tests/e2e/

# Output:
# 18 tests passed ✅
```

**Log-Check**:
```bash
docker compose logs | grep -i "error\|traceback\|failed" | wc -l

# Output sollte sein: 0 (keine Fehler)
```

---

## 📝 Troubleshooting (Falls immer noch Probleme)

### Wenn cdb_risk immer noch crasht:

```bash
# In Container reingehen
docker compose run --rm cdb_risk bash

# Manuell starten
python -u service.py

# Output genau lesen - zeigt exakte Fehlerzeile
```

### Wenn Redis-Auth fehlschlägt:

```bash
# Redis-Log prüfen
docker compose logs cdb_redis --tail=100

# Passwort manuell testen
docker exec -it cdb_redis redis-cli -a claire_redis_secret_2024 ping
# Sollte zeigen: PONG
```

### Wenn PostgreSQL nicht startet:

```bash
# PostgreSQL-Log prüfen
docker compose logs cdb_postgres --tail=100

# Manuell verbinden
docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare
```

---

## ✅ Zusammenfassung

| Problem | Severity | Status | Fix |
|---------|----------|--------|-----|
| Fehlende .env Datei | P0 | ⛔ BLOCKER | `cp .env.example .env` |
| Bug #1: Position Size | P0 | ✅ FIXED | Committed (d28518b) |
| Bug #2: Position Limit | P0 | ✅ FIXED | Committed (d28518b) |
| Bug #3: Exposure Check | P0 | ✅ FIXED | Committed (d28518b) |
| Bug #4: Daily P&L | P0 | ✅ FIXED | Committed (d28518b) |
| Race Conditions | P1 | ⚠️ MINOR | Retry-Logik bereits vorhanden |
| Health-Check Timing | P2 | ℹ️ INFO | Optional: start_period hinzufügen |

**Nächster Schritt**: `.env` Datei erstellen und Container neu starten!

---

**Ende des Dokuments**
