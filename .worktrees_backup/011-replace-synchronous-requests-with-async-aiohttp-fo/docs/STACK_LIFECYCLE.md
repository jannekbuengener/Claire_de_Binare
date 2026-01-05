# Stack Lifecycle - Canonical Path

**Single source of truth for Claire de Binare Docker stack operations.**

## Philosophy

**ONE path for each operation. No alternatives. No ambiguity.**

---

## Prerequisites

Before any stack operation:

```powershell
# Verify you're in project root
Test-Path infrastructure/compose/base.yml  # Must return True

# Verify .env exists
Test-Path .env  # Must return True (copy from .env.example if missing)

# Verify Docker is running
docker info  # Must succeed (no errors)
```

---

## Canonical Compose Configuration

### File Hierarchy (Fixed)

```
infrastructure/compose/
├── base.yml                 # Core infrastructure (ALWAYS required)
├── dev.yml                  # Development overlay (DEFAULT)
├── prod.yml                 # Production overlay (use in production)
├── test.yml                 # Test overlay (E2E tests only)
└── logging.yml              # Logging overlay (optional)
```

### Deterministic Composition

**Development (DEFAULT):**
```powershell
docker compose \
  -f infrastructure/compose/base.yml \
  -f infrastructure/compose/dev.yml \
  up -d
```

**Production:**
```powershell
docker compose \
  -f infrastructure/compose/base.yml \
  -f infrastructure/compose/prod.yml \
  up -d
```

**E2E Testing:**
```powershell
docker compose \
  -f infrastructure/compose/base.yml \
  -f infrastructure/compose/test.yml \
  up -d
```

---

## Stack Operations

### 1. START Stack

**Command (Dev):**
```powershell
make docker-up
```

**What it does:**
1. Reads `infrastructure/compose/base.yml` + `dev.yml`
2. Creates network (`cdb_network`)
3. Creates volumes (redis_data, postgres_data, etc.)
4. Starts infrastructure services (Redis, Postgres, Prometheus, Grafana)
5. Starts application services (core, risk, execution, db_writer)
6. Waits for health checks (30s timeout)

**Expected output:**
```
🐳 Starte Docker Compose Stack...
✓ Using Compose Fragments (base + dev)
[+] Running 9/9
 ✔ Network cdb_network         Created
 ✔ Container cdb_redis          Healthy
 ✔ Container cdb_postgres       Healthy
 ✔ Container cdb_prometheus     Healthy
 ✔ Container cdb_grafana        Healthy
 ✔ Container cdb_core           Healthy
 ✔ Container cdb_risk           Healthy
 ✔ Container cdb_execution      Healthy
 ✔ Container cdb_db_writer      Healthy
```

**Failure handling:**
```powershell
# If startup fails, check logs
make docker-health

# View specific service logs
docker logs cdb_<service_name>

# If still failing, RESET (see below)
make docker-down
make docker-up
```

---

### 2. STOP Stack

**Command:**
```powershell
make docker-down
```

**What it does:**
1. Stops all containers (graceful shutdown, 10s timeout)
2. Removes containers
3. Preserves volumes (data NOT lost)
4. Preserves network

**Expected output:**
```
🛑 Stoppe Docker Compose Stack...
[+] Running 9/9
 ✔ Container cdb_db_writer      Removed
 ✔ Container cdb_execution      Removed
 ✔ Container cdb_risk           Removed
 ✔ Container cdb_core           Removed
 ✔ Container cdb_grafana        Removed
 ✔ Container cdb_prometheus     Removed
 ✔ Container cdb_postgres       Removed
 ✔ Container cdb_redis          Removed
 ✔ Network cdb_network          Removed
```

**Data safety:**
- ✅ Postgres data preserved (volume: `postgres_data`)
- ✅ Redis data preserved (volume: `redis_data`)
- ✅ Grafana dashboards preserved (volume: `grafana_data`)
- ✅ Prometheus metrics preserved (volume: `prometheus_data`)

---

### 3. HEALTH Check

**Command:**
```powershell
make docker-health
```

**What it does:**
1. Lists all containers with health status
2. Checks for "healthy" vs "unhealthy" vs "starting"
3. Shows uptime for each service

**Expected output (healthy stack):**
```
Container         Status                  Ports
cdb_redis         Up 2 minutes (healthy)  127.0.0.1:6379->6379/tcp
cdb_postgres      Up 2 minutes (healthy)  127.0.0.1:5432->5432/tcp
cdb_prometheus    Up 2 minutes (healthy)  127.0.0.1:9090->9090/tcp
cdb_grafana       Up 2 minutes (healthy)  127.0.0.1:3000->3000/tcp
cdb_core          Up 2 minutes (healthy)  127.0.0.1:8001->8001/tcp
cdb_risk          Up 2 minutes (healthy)  127.0.0.1:8002->8002/tcp
cdb_execution     Up 2 minutes (healthy)  127.0.0.1:8003->8003/tcp
cdb_db_writer     Up 2 minutes (healthy)  127.0.0.1:8005->8005/tcp
```

**Unhealthy stack:**
```
Container         Status                     Ports
cdb_redis         Up 30 seconds (unhealthy)  127.0.0.1:6379->6379/tcp
```

**Troubleshooting unhealthy services:**
```powershell
# 1. Check logs
docker logs cdb_<service_name> --tail 50

# 2. Check health endpoint (if service has one)
curl http://localhost:<port>/health

# 3. If persistent unhealthy, restart service
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml restart <service_name>
```

---

### 4. RESET Stack (Nuclear Option)

**When to use:**
- Stack won't start after multiple attempts
- Corrupt data suspected
- Want clean slate for testing
- Migrating to new schema version

**⚠️ WARNING: This DELETES ALL DATA**

**Command:**
```powershell
# Full reset (DANGEROUS - deletes all data)
make docker-down
docker volume rm $(docker volume ls -q | Select-String "cdb_")
make docker-up
```

**Step-by-step safe reset:**
```powershell
# 1. Stop stack
make docker-down

# 2. List volumes to confirm what will be deleted
docker volume ls | Select-String "cdb_"

# Expected:
# cdb_grafana_data
# cdb_postgres_data
# cdb_prometheus_data
# cdb_redis_data

# 3. Backup critical data (if needed)
# (See BACKUP section below)

# 4. Delete volumes
docker volume rm cdb_redis_data
docker volume rm cdb_postgres_data
docker volume rm cdb_prometheus_data
docker volume rm cdb_grafana_data

# 5. Restart stack (fresh state)
make docker-up
```

---

## Stack Verification

After START, always verify:

```powershell
# 1. All services running
make docker-health

# 2. All services healthy (no "unhealthy" status)
docker ps --filter name=cdb_ --format "{{.Names}}: {{.Status}}"

# 3. Networks exist
docker network ls | Select-String "cdb_"

# 4. Volumes exist
docker volume ls | Select-String "cdb_"
```

**Expected result:**
- ✅ 8 containers running
- ✅ All show "(healthy)" in status
- ✅ 1 network (`cdb_network`)
- ✅ 4 volumes (redis_data, postgres_data, prometheus_data, grafana_data)

---

## Environment Configuration

### Required ENV Variables

Copy `.env.example` to `.env` and set:

```bash
# Redis
REDIS_HOST=cdb_redis
REDIS_PORT=6379
REDIS_PASSWORD=<path_to_secret_file>

# Postgres
POSTGRES_HOST=cdb_postgres
POSTGRES_PORT=5432
POSTGRES_USER=cdb_user
POSTGRES_PASSWORD=<path_to_secret_file>
POSTGRES_DB=claire_de_binare

# Trading Mode
TRADING_MODE=paper  # paper|staged|live (default: paper)
LIVE_TRADING_CONFIRMED=  # Set to "yes" ONLY for live trading

# MEXC API (only for STAGED/LIVE modes)
MEXC_API_KEY=<path_to_secret_file>
MEXC_API_SECRET=<path_to_secret_file>
MEXC_TESTNET=true  # true for STAGED, false for LIVE
```

### Secret Files

Secrets must be FILES, not directories:

```powershell
# Verify secrets exist
Test-Path <path_in_env_var>  # Must return True

# Verify secrets are FILES (not directories)
(Get-Item <path_in_env_var>).PSIsContainer  # Must return False

# Example:
Test-Path C:\Users\<user>\Documents\.secrets\.cdb\REDIS_PASSWORD
(Get-Item C:\Users\<user>\Documents\.secrets\.cdb\REDIS_PASSWORD).PSIsContainer
# Must return: True, False
```

---

## Version Pinning

### Image Versions (Deterministic)

All infrastructure images MUST be pinned with SHA256 digests:

```yaml
# base.yml
services:
  redis:
    image: redis@sha256:ee64a64eaab618d88051c3ade8f6352d11531fcf79d9a4818b9b183d8c1d18ba
    # DO NOT use: redis:latest or redis:7

  postgres:
    image: postgres@sha256:b3968e348b48f1198cc6de6611d055dbad91cd561b7990c406c3fc28d7095b21
    # DO NOT use: postgres:latest or postgres:16
```

### Application Services (Build from Source)

Application services built from Dockerfiles (no external images):

```yaml
# dev.yml
services:
  cdb_core:
    build:
      context: ../..
      dockerfile: services/core/Dockerfile
    # Always builds from current commit
```

---

## Stack States

### State 1: STOPPED

**Indicators:**
- `docker ps` shows no cdb_* containers
- Volumes exist but inactive
- Network may exist but unused

**How to reach:**
```powershell
make docker-down
```

---

### State 2: STARTING

**Indicators:**
- Containers exist, status shows "starting" or "health: starting"
- Health checks in progress (< 30s)

**Normal duration:** 10-30 seconds

**If stuck > 60s:**
```powershell
# Check which service is stuck
make docker-health

# View logs of stuck service
docker logs cdb_<stuck_service> --tail 50

# If Redis/Postgres stuck, likely auth issue
# Check secret files exist and are correct
```

---

### State 3: HEALTHY (Target State)

**Indicators:**
- All containers show "(healthy)" in status
- Health endpoints return 200 OK
- Services can communicate (Redis, Postgres reachable)

**Verification:**
```powershell
# Quick check
make docker-health

# Detailed check
curl http://localhost:8001/health  # core
curl http://localhost:8002/health  # risk
curl http://localhost:8003/health  # execution
curl http://localhost:8005/health  # db_writer

# All should return: {"status": "ok", ...}
```

---

### State 4: UNHEALTHY (Requires Action)

**Indicators:**
- One or more containers show "(unhealthy)"
- Health checks failing repeatedly

**Recovery path:**
```powershell
# 1. Identify unhealthy service
make docker-health

# 2. Check logs
docker logs cdb_<unhealthy_service> --tail 100

# 3. Common fixes:
# - Auth error → Check secret files
# - Connection refused → Check dependent service healthy
# - Port conflict → Check no other process using port

# 4. Restart unhealthy service
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml restart <service>

# 5. If still unhealthy after 3 restart attempts, RESET
make docker-down
make docker-up
```

---

## Backup & Restore

### Backup Critical Data

```powershell
# Backup Postgres data
docker exec cdb_postgres pg_dump -U cdb_user claire_de_binare > backup_$(Get-Date -Format "yyyyMMdd_HHmmss").sql

# Backup Redis data (if RDB enabled)
docker exec cdb_redis redis-cli SAVE
docker cp cdb_redis:/data/dump.rdb redis_backup_$(Get-Date -Format "yyyyMMdd_HHmmss").rdb
```

### Restore from Backup

```powershell
# Restore Postgres
cat backup_YYYYMMDD_HHMMSS.sql | docker exec -i cdb_postgres psql -U cdb_user -d claire_de_binare

# Restore Redis
docker cp redis_backup_YYYYMMDD_HHMMSS.rdb cdb_redis:/data/dump.rdb
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml restart cdb_redis
```

---

## Troubleshooting Matrix

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `make docker-up` fails immediately | Compose file syntax error | Run `docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml config` to validate |
| Container exits immediately | Missing ENV variable | Check `.env` file complete |
| Health check stuck "starting" | Dependent service not healthy | Check `docker-health`, fix dependencies first |
| Port conflict error | Another process using port | `netstat -ano \| Select-String <port>`, kill conflicting process |
| Secret file error | Secret is directory not file | Verify `(Get-Item <path>).PSIsContainer` returns False |
| Redis auth failed | Wrong password in .env | Check REDIS_PASSWORD points to correct file |
| Postgres auth failed | Wrong credentials | Check POSTGRES_USER, POSTGRES_PASSWORD correct |

---

## References

- **Compose Files:** `infrastructure/compose/`
- **Compose Layers Doc:** `infrastructure/compose/COMPOSE_LAYERS.md`
- **Environment Template:** `.env.example`
- **Trading Modes:** `docs/TRADING_MODES.md`
- **Security:** `docs/SECURITY_HARDENING.md`

---

**Last Updated:** 2025-12-27
**Status:** ✅ Canonical (Issue #242)
