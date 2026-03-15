# CDB Quick Start - Blue/Red Stack

**Target:** Developers & Operators
**Time:** ~5 minutes
**Prerequisites:** Docker Desktop, Python 3.12+, secrets configured

---

## Initial Setup (One-Time)

### 1. Create Docker Network

```powershell
docker network create cdb_network
```

**Verify:**
```powershell
docker network ls | Select-String "cdb_network"
```

---

### 2. Configure Secrets

**Location:** `C:\Users\<you>\Documents\.secrets\.cdb\`

**Required Files:**
```
REDIS_PASSWORD
POSTGRES_PASSWORD
POSTGRES_PASSWORD_DSN  (format: postgresql://user:password@host:port/dbname)
MEXC_API_KEY.txt
MEXC_API_SECRET.txt
GRAFANA_PASSWORD
SMTP_USER
SMTP_PASSWORD
SMTP_FROM
ALERT_EMAIL_TO
```

**Example DSN:**
```
postgresql://claire_user:your_password@cdb_postgres:5432/claire_de_binare
```

---

## Daily Operations

### Start Stack (Automated)

**Full Stack (BLUE + RED):**
```powershell
cd D:\Dev\Workspaces\Repos\Claire_de_Binare
.\infrastructure\scripts\setup_blue_red.ps1
```

**Core Only (Skip Monitoring/Signals):**
```powershell
.\infrastructure\scripts\setup_blue_red.ps1 -SkipRed
```

**Skip Smoke Test (Faster Iteration):**
```powershell
.\infrastructure\scripts\setup_blue_red.ps1 -SkipSmokeTest
```

---

### Start Stack (Manual)

**Step 1: Start BLUE (Core)**
```powershell
docker compose -f infrastructure\compose\compose.blue.yml up -d
```

**Step 2: Verify Core Flow**
```powershell
.\infrastructure\scripts\smoke_test.ps1
```

**Step 3: Start RED (Optional)**
```powershell
docker compose -f infrastructure\compose\compose.red.yml up -d
```

---

### Check Status

**BLUE Stack:**
```powershell
docker compose -f infrastructure\compose\compose.blue.yml ps
```

**RED Stack:**
```powershell
docker compose -f infrastructure\compose\compose.red.yml ps
```

**All Services:**
```powershell
docker ps --filter "name=cdb_" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

---

### View Logs

**BLUE (Core):**
```powershell
docker compose -f infrastructure\compose\compose.blue.yml logs -f
```

**Specific Service:**
```powershell
docker compose -f infrastructure\compose\compose.blue.yml logs -f cdb_risk
```

**Last 100 Lines:**
```powershell
docker compose -f infrastructure\compose\compose.blue.yml logs --tail 100 cdb_execution
```

**Grep for Errors:**
```powershell
docker compose -f infrastructure\compose\compose.blue.yml logs --tail 500 | Select-String -Pattern "ERROR|CRITICAL"
```

---

### Stop Stack

**BLUE + RED:**
```powershell
docker compose -f infrastructure\compose\compose.blue.yml down
docker compose -f infrastructure\compose\compose.red.yml down
```

**BLUE Only:**
```powershell
docker compose -f infrastructure\compose\compose.blue.yml down
```

**With Volume Cleanup (DESTRUCTIVE):**
```powershell
docker compose -f infrastructure\compose\compose.blue.yml down -v
# WARNING: Deletes ALL data (postgres, redis, prometheus, grafana)
```

---

### Restart Services

**Restart Single Service:**
```powershell
docker compose -f infrastructure\compose\compose.blue.yml restart cdb_risk
```

**Restart Entire Stack:**
```powershell
docker compose -f infrastructure\compose\compose.blue.yml restart
```

**Rebuild + Restart (After Code Changes):**
```powershell
docker compose -f infrastructure\compose\compose.blue.yml up -d --build
```

---

## Health Checks

### Service Endpoints

| Service | Endpoint | Expected |
|---------|----------|----------|
| Risk | http://localhost:8002/health | `{"status":"ok"}` |
| Execution | http://localhost:8003/health | `{"status":"ok"}` |
| Paper Runner | http://localhost:8004/health | `{"status":"ok"}` |
| Signal | http://localhost:8005/health | `{"status":"ok"}` |
| Allocation | http://localhost:8006/health | `{"status":"ok"}` |
| Candles | http://localhost:8007/health | `{"status":"ok"}` |
| Regime | http://localhost:8008/health | `{"status":"ok"}` |
| WS | http://localhost:8000/health | `{"status":"ok"}` |
| Grafana | http://localhost:3000/api/health | `{"database":"ok"}` |
| Prometheus | http://localhost:19090/-/healthy | `Prometheus is Healthy.` |

### Quick Health Check (All Services)

```powershell
@(8002,8003,8004,8005,8006,8007,8008,8000,3000,19090) | ForEach-Object {
    $port = $_
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$port/health" -UseBasicParsing -TimeoutSec 2
        Write-Host "[OK] Port $port" -ForegroundColor Green
    } catch {
        Write-Host "[FAIL] Port $port" -ForegroundColor Red
    }
}
```

---

## Smoke Test

### Run Test

```powershell
.\infrastructure\scripts\smoke_test.ps1
```

**With Verbose Output:**
```powershell
.\infrastructure\scripts\smoke_test.ps1 -Verbose
```

**Expected Output:**
```
[PASS] SMOKE TEST PASSED
Core flow operational: Signal -> Risk -> Execution -> DB
```

**Report Location:** `reports/CORE_FLOW_E2E_SMOKE.md`

---

### Manual Signal Injection (Debug)

**Inject Test Signal:**
```powershell
$signal = @{
    type = "signal"
    signal_id = "DEBUG_$(Get-Date -Format 'yyyyMMddHHmmss')"
    strategy_id = "paper"
    symbol = "BTCUSDT"
    side = "BUY"
    price = 85000.0
    pct_change = 0.01
    confidence = 0.95
    timestamp = [int](Get-Date -UFormat %s)
    ts_ms = [int64](Get-Date -UFormat %s) * 1000
} | ConvertTo-Json -Compress

$env:REDIS_PASSWORD = Get-Content "$env:USERPROFILE\Documents\.secrets\.cdb\REDIS_PASSWORD" -Raw

docker exec cdb_redis sh -c "redis-cli -a `$(cat /run/secrets/redis_password) PUBLISH signals '$signal'"
```

**Verify Order Created:**
```powershell
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "SELECT order_id, symbol, side, status FROM orders ORDER BY created_at DESC LIMIT 5;"
```

---

## Troubleshooting

### Service Not Starting

**Check Logs:**
```powershell
docker logs cdb_<service> --tail 100
```

**Check Dependencies:**
```powershell
docker compose -f infrastructure\compose\compose.blue.yml config
```

**Rebuild Service:**
```powershell
docker compose -f infrastructure\compose\compose.blue.yml up -d --build --force-recreate cdb_<service>
```

---

### Smoke Test Failing

**Cause 1: No Allocation**

```powershell
curl http://localhost:8002/status | ConvertFrom-Json | Select-Object -ExpandProperty allocation_state
```

**Expected:** `allocation_pct > 0` for `paper` strategy

**Fix:** Check allocation service is running and publishing decisions:
```powershell
docker logs cdb_allocation --tail 50
```

---

**Cause 2: Redis Connection Failed**

```powershell
docker exec cdb_redis sh -c "redis-cli -a `$(cat /run/secrets/redis_password) ping"
```

**Expected:** `PONG`

**Fix:** Restart Redis:
```powershell
docker compose -f infrastructure\compose\compose.blue.yml restart cdb_redis
```

---

**Cause 3: Postgres Not Ready**

```powershell
docker exec cdb_postgres pg_isready -U claire_user -d claire_de_binare
```

**Expected:** `accepting connections`

**Fix:** Wait for init to complete:
```powershell
docker logs cdb_postgres | Select-String "database system is ready"
```

---

### Port Conflicts

**Find Process Using Port:**
```powershell
netstat -ano | findstr :<PORT>
```

**Kill Process:**
```powershell
Stop-Process -Id <PID> -Force
```

---

### Reset Everything (Nuclear Option)

```powershell
# Stop all containers
docker compose -f infrastructure\compose\compose.blue.yml down
docker compose -f infrastructure\compose\compose.red.yml down

# Remove volumes (DESTRUCTIVE - deletes all data)
docker volume rm cdb-blue_postgres_data cdb-blue_redis_data cdb-blue_validation_data
docker volume rm cdb-red_prom_data cdb-red_grafana_data

# Remove network
docker network rm cdb_network

# Start fresh
.\infrastructure\scripts\setup_blue_red.ps1
```

---

## Monitoring

### Grafana Dashboards

**URL:** http://localhost:3000
**Login:** `admin` / (password from `GRAFANA_PASSWORD` secret)

**Available Dashboards:**
- Core Trading Metrics
- Risk Manager Status
- Execution Performance
- Database Performance

---

### Prometheus Metrics

**URL:** http://localhost:19090

**Key Metrics:**
- `signals_received_total` - Signals received by Risk
- `orders_approved_total` - Orders approved
- `orders_blocked_total` - Orders blocked
- `circuit_breaker_active` - Circuit breaker status

**Query Examples:**
```promql
# Order approval rate
rate(orders_approved_total[5m])

# Block rate
rate(orders_blocked_total[5m])

# Allocation state
allocation_pct{strategy="paper"}
```

---

## Common Workflows

### Code Change → Test

```powershell
# 1. Rebuild affected service
docker compose -f infrastructure\compose\compose.blue.yml up -d --build cdb_risk

# 2. Check logs
docker logs cdb_risk --tail 50 -f

# 3. Run smoke test
.\infrastructure\scripts\smoke_test.ps1
```

---

### Add New Service to BLUE

1. Edit `infrastructure/compose/compose.blue.yml`
2. Add service definition
3. Rebuild: `docker compose -f compose.blue.yml up -d --build`
4. Verify: `docker compose -f compose.blue.yml ps`

---

### Legacy Compose (CI-Only)

Legacy compose (`base.yml + dev.yml`) remains only for CI/test workflows
(e.g., `shadow-soak-evidence.yml`, `e2e.yml`). It is not the normal
operator runtime path. See `COMPOSE_LAYERS.md` for details.

---

## Reference

**Architecture:** `infrastructure/docs/BLUE_RED_SPLIT.md`
**Smoke Test Details:** `scripts/README_SMOKE_TEST.md`
**Compose Files:**
- BLUE: `infrastructure/compose/compose.blue.yml`
- RED: `infrastructure/compose/compose.red.yml`

**Scripts:**
- Setup: `infrastructure/scripts/setup_blue_red.ps1`
- Smoke Test: `infrastructure/scripts/smoke_test.ps1`
- Core Smoke: `scripts/smoke_core_flow.py`
