# Paper Trading Runbook

**Philosophy**: Copy-paste commands first, understand later.

**Purpose**: Operational guide for Claire de Binare paper trading mode setup, monitoring, and troubleshooting.

---

## Quick Start

### 1. Initial Setup (First Time Only)

```powershell
# Step 1: Create .env from template
cp .env.example .env

# Step 2: Verify paper mode configuration
Get-Content .env | Select-String "SIGNAL_STRATEGY_ID"
# Expected: SIGNAL_STRATEGY_ID=primary_breakout_v1

Get-Content .env | Select-String "SIGNAL_ADAPTER_ID"
# Expected: SIGNAL_ADAPTER_ID=momentum_builtin

Get-Content .env | Select-String "SIGNAL_TRADE_SIDE_MODE"
# Expected: SIGNAL_TRADE_SIDE_MODE=long_only

Get-Content .env | Select-String "DRY_RUN"
# Expected: DRY_RUN=true

Get-Content .env | Select-String "MEXC_TESTNET"
# Expected: MEXC_TESTNET=true

# Step 3: Verify secret files exist
ls $env:SECRETS_PATH
# Or on Linux/Mac: ls ~/Documents/.secrets/.cdb/
# Expected: REDIS_PASSWORD, POSTGRES_PASSWORD, GRAFANA_PASSWORD (all FILES, not directories)
```

---

### 2. Start Paper Trading Stack

```powershell
# Start all services (including paper runner)
make docker-up

# Wait 30 seconds for services to initialize
Start-Sleep -Seconds 30

# Verify all services healthy
make docker-health

# Check paper runner specifically
docker ps --filter "name=cdb_paper_runner"
# Expected: Status "healthy"
```

---

### 3. Monitor Paper Trading Activity

```powershell
# View paper runner logs (live)
make paper-trading-logs

# View last 50 events
docker logs cdb_paper_runner --tail 50

# Check health endpoint
curl http://localhost:8004/health
# Expected: {"status":"ok","service":"paper_trading_runner","uptime_seconds":X,"events_logged":Y}
```

---

## Paper-Capture Checkpoint Time-Integrity

**Grundregel:** Paper-Capture läuft gegen reale Marktzeit. ARVP-Replay darf beschleunigen. Paper-Monitoring darf es nicht. Kein Agent darf Monitoring-Zeit simulieren oder vorspulen.

### Checkpoint-Typen (verbindlich)

Jeder Monitoring-Report muss exakt einen dieser Typen deklarieren:

| Typ | Bedingung | Bedeutung |
|---|---|---|
| `instant_snapshot` | Kein vorangegangener Checkpoint bekannt, oder `real_elapsed_time` < konfiguriertes Intervall | Momentaufnahme ohne Zeitverfluss-Aussage; kein Zyklus-Abschluss |
| `real_elapsed_checkpoint` | `real_elapsed_time >= konfiguriertes Intervall`, belegbar durch Zeitstempel-Delta | Echter Monitoring-Zyklus abgeschlossen |
| `scheduled_follow_up_needed` | Checkpoint initiiert, konfiguriertes Intervall noch nicht abgelaufen | Nächster Check ausstehend; Wecker noch nicht erreicht |

Fehlt die Typdeklaration → Default: `instant_snapshot` (fail-closed).

### Pflichtfelder pro Checkpoint-Report

```yaml
checkpoint_type: instant_snapshot | real_elapsed_checkpoint | scheduled_follow_up_needed
checkpoint_started_at: "<ISO8601>"        # Zeitpunkt des letzten vorherigen Checks (oder "unknown" wenn nicht bekannt)
checkpoint_observed_at: "<ISO8601>"       # Zeitpunkt dieses Checks
real_elapsed_time: "<HH:MM:SS>"           # Differenz observed_at - started_at; "unknown" wenn started_at fehlt
next_real_checkpoint_due_at: "<ISO8601>"  # Wann ist der nächste echte Zyklus fällig; "TBD" wenn Wecker nicht gestellt
```

### Stop-Bedingung für Agenten

Ein Agent darf einen Report **nur als `real_elapsed_checkpoint`** klassifizieren, wenn **alle drei Bedingungen** erfüllt sind:

1. `checkpoint_started_at` ist bekannt und belegt.
2. `checkpoint_observed_at` ist der tatsächliche Zeitpunkt des aktuellen Checks.
3. `real_elapsed_time = checkpoint_observed_at - checkpoint_started_at >= konfiguriertes Monitoring-Intervall`.

Fehlt eine dieser Bedingungen → Typ zwingend `instant_snapshot`, auch wenn das Intervall nominell "abgelaufen" sein könnte.

### Verbote (absolut)

- Kein Agent darf einen 30-Minuten-, 60-Minuten- oder 120-Minuten-Checkpoint als abgeschlossen melden, ohne dass `real_elapsed_time >= Intervall` aus belegbaren Zeitstempeln ableitbar ist.
- Kein Agent darf fehlende Zeitdaten durch Annahmen ersetzen.
- Checkpoint-Berichte ohne `checkpoint_type`-Deklaration gelten als `instant_snapshot`.
- Eine Kette von `instant_snapshot`-Reports ersetzt keinen `real_elapsed_checkpoint`.

### Freigabe-Regel (Operator)

Der Operator bestätigt einen Monitoring-Zyklus als abgeschlossen, wenn:

- ein realer Wecker oder eine externe Zeitreferenz den Ablauf des Intervalls bestätigt, **oder**
- der Zeitstempel-Delta zwischen zwei aufeinanderfolgenden Checkpoint-Kommentaren das konfigurierte Intervall nachweislich überschreitet.

### Trennung Paper-Capture / ARVP-Replay

| Modus | Zeitbasis | Monitoring |
|---|---|---|
| Paper-Capture | **Reale Marktzeit** | Checkpoints müssen reale Zeit belegen |
| ARVP-Replay | Beschleunigt (simuliert) | Separater Kontext; keine Paper-Capture-Aussage |

Diese Modi dürfen in Checkpoint-Reports **nicht** vermischt werden. Ein ARVP-Replay-Ergebnis ist kein Ersatz für einen Paper-Capture-Checkpoint.

---

## Configuration

### Environment Variables

| Variable | Default | Purpose | Safety |
|----------|---------|---------|--------|
| `SIGNAL_STRATEGY_ID` | `primary_breakout_v1` | Canonical strategy on paper path | ⚠️ Keep on `primary_breakout_v1`; `live` remains DANGER |
| `SIGNAL_ADAPTER_ID` | `momentum_builtin` | Current main-backed strategy adapter path | ⚠️ Must stay `momentum_builtin` for current boundary |
| `SIGNAL_TRADE_SIDE_MODE` | `long_only` | primary v1 side guard | ⚠️ Must stay `long_only` for `primary_breakout_v1` |
| `DRY_RUN` | `true` | Log-only mode | ⚠️ Must be `true` for testing |
| `MEXC_TESTNET` | `true` | Exchange testnet | ⚠️ Must be `true` for testing |
| `PAPER_TRADING_DURATION_DAYS` | `14` | Test duration | Optional |
| `LOG_LEVEL` | `INFO` | Logging verbosity | Optional (DEBUG/INFO/WARNING/ERROR) |

### Safety Checklist

Before starting paper trading:

- [ ] `SIGNAL_STRATEGY_ID=primary_breakout_v1` (paper path only)
- [ ] `SIGNAL_ADAPTER_ID=momentum_builtin` (current main adapter boundary)
- [ ] `SIGNAL_TRADE_SIDE_MODE=long_only` (primary v1 guard)
- [ ] `DRY_RUN=true` (NO real trades)
- [ ] `MEXC_TESTNET=true` (TESTNET only)
- [ ] Secret files exist and are FILES (not directories)
- [ ] All services healthy (`make docker-health`)

---

## Health Monitoring

### Service Status

```powershell
# Quick health check (all services)
docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String "cdb_"

# Paper runner specific status
docker inspect cdb_paper_runner --format='{{.State.Health.Status}}'
# Expected: "healthy"
```

### Health Endpoint Details

**Endpoint**: `http://localhost:8004/health`

**Healthy Response**:
```json
{
  "status": "ok",
  "service": "paper_trading_runner",
  "uptime_seconds": 3600,
  "events_logged": 142,
  "last_health_check": "2025-12-27T14:30:00"
}
```

**Unhealthy Response** (503):
```json
{
  "status": "stopped"
}
```

### Event Logs

Paper trading events logged to: `logs/events/events_YYYYMMDD.jsonl`

```powershell
# View today's events
Get-Content logs/events/events_$(Get-Date -Format "yyyyMMdd").jsonl | ConvertFrom-Json | Format-Table

# Count events by type
Get-Content logs/events/events_*.jsonl | ConvertFrom-Json | Group-Object event_type | Select-Object Count,Name
```

---

## Troubleshooting

### 1. Container Not Starting

**Symptom**: `docker ps` shows cdb_paper_runner as "Restarting" or "Exited"

**Quick Fix**:
```powershell
# Check logs for error
docker logs cdb_paper_runner --tail 30

# Common issues:
# - Redis connection failed → Check cdb_redis is healthy
# - Postgres connection failed → Check cdb_postgres is healthy
# - Secret file error → See "Secret File Errors" section

# Restart service
docker-compose restart cdb_paper_runner
```

---

### 2. Health Check Failing

**Symptom**: `docker inspect` shows health status "unhealthy"

**Quick Fix**:
```powershell
# Step 1: Check if port 8004 is accessible
curl http://localhost:8004/health

# If connection refused:
# - Service not running → check logs
# - Port conflict → check netstat -ano | Select-String "8004"

# Step 2: Check service logs for errors
docker logs cdb_paper_runner --tail 50 | Select-String "ERROR"

# Step 3: Verify dependencies healthy
docker ps --filter "name=cdb_redis"
docker ps --filter "name=cdb_postgres"
# Both should show "healthy" status

# Step 4: Restart service
docker-compose restart cdb_paper_runner
```

---

### 3. No Events Being Logged

**Symptom**: Event count stays at 0, no JSONL files created

**Quick Fix**:
```powershell
# Step 1: Verify logs directory exists
Test-Path logs/
# If false → create manually: mkdir logs

# Step 2: Check file permissions
ls logs/ | Select-Object Name, Attributes

# Step 3: Check Redis connection (events come via Redis)
docker exec cdb_redis redis-cli -a $env:REDIS_PASSWORD ping
# Expected: PONG

# Step 4: Verify signal strategy publishing
docker logs cdb_core --tail 50 | Select-String "signal"
```

---

### 4. Secret File Errors

**Symptom**: Logs show "cat: read error: Is a directory" or "secret file does not exist"

**Quick Fix**:
```powershell
# Step 1: Verify secret files exist and are FILES (not directories)
ls $env:SECRETS_PATH
# Or on Linux/Mac: ls ~/Documents/.secrets/.cdb/

# Expected: All should be files with size > 0 bytes
# -rw-r--r-- REDIS_PASSWORD (e.g., 24 bytes)
# -rw-r--r-- POSTGRES_PASSWORD (any size > 0)

# Step 2: If directories exist, they're INVALID
# Fix: Create actual files with password content (use init-secrets.ps1 or:)
"your_password_here" | Out-File -FilePath "$env:SECRETS_PATH\POSTGRES_PASSWORD" -NoNewline -Encoding ASCII

# Step 3: Verify file contents (should be plain text password)
Get-Content "$env:SECRETS_PATH\POSTGRES_PASSWORD"

# Step 4: Restart stack
docker-compose down
make docker-up
```

---

### 5. Port Conflict on 8004

**Symptom**: Service fails to start with "port already allocated" error

**Quick Fix**:
```powershell
# Step 1: Find process using port 8004
netstat -ano | Select-String "8004"

# Step 2: Kill process (use PID from step 1)
Stop-Process -Id <PID> -Force

# Alternative: Change port in dev.yml
# Edit infrastructure/compose/dev.yml line ~161:
# ports:
#   - "127.0.0.1:8005:8004"  # Use 8005 instead

# Step 3: Restart service
docker-compose restart cdb_paper_runner
```

---

## Validation & Testing

### End-to-End Test

```powershell
# Set environment for E2E tests
$env:E2E_RUN = "1"
$env:E2E_DISABLE_CIRCUIT_BREAKER = "1"

# Run paper trading E2E tests
python -m pytest tests/e2e/test_paper_trading_p0.py -v -rs --no-cov

# Expected: All tests PASS
# - test_tc_p0_001_happy_path_market_to_trade
# - test_tc_p0_002_signal_to_execution
```

### Manual Validation Checklist

- [ ] All services start: `make docker-up`
- [ ] All services healthy: `make docker-health` (all show "healthy")
- [ ] Paper runner healthy: `curl http://localhost:8004/health` (returns 200 OK)
- [ ] Events logging: `ls logs/events/events_*.jsonl` (files exist)
- [ ] E2E tests pass: `pytest tests/e2e/test_paper_trading_p0.py` (all PASS)
- [ ] No errors in logs: `docker logs cdb_paper_runner | Select-String "ERROR"` (empty)

---

## Common Commands Reference

```powershell
# Start paper trading
make docker-up

# Stop paper trading (graceful)
make docker-down

# Restart paper runner only
docker-compose restart cdb_paper_runner

# View logs (live)
make paper-trading-logs

# View logs (last 100 lines)
docker logs cdb_paper_runner --tail 100

# Check health
curl http://localhost:8004/health

# Check all services
make docker-health

# Run E2E tests
$env:E2E_RUN="1"; python -m pytest tests/e2e/test_paper_trading_p0.py -v
```

---

## Disaster Recovery

### Complete Stack Reset

```powershell
# Step 1: Stop all containers
docker-compose down

# Step 2: Verify all stopped
docker ps -a | Select-String "cdb_"
# Should show no running containers

# Step 3: Remove paper runner container (if exists)
docker rm -f cdb_paper_runner

# Step 4: Clean logs (OPTIONAL - backup first!)
# Move-Item logs/ logs_backup_$(Get-Date -Format "yyyyMMdd_HHmmss")/

# Step 5: Restart stack
make docker-up

# Step 6: Wait 30s then verify
Start-Sleep -Seconds 30
make docker-health
```

---

## Next Steps

After successful paper trading setup:

1. **Monitor for 24 hours**: Ensure no errors in logs
2. **Review event logs**: `logs/events/events_*.jsonl`
3. **Run full 14-day test**: Let paper runner complete full cycle
4. **Review results**: Analyze P&L, trade accuracy, signal quality

⚠️ **NEVER move to live trading without**:
- [ ] Successful 14-day paper trading completion
- [ ] Zero critical errors in logs
- [ ] All E2E tests passing consistently
- [ ] Explicit approval from system owner
