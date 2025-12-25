# Docker Stack Runbook

## Overview

Command-first troubleshooting guide for Claire de Binare Docker stack failures.

**Philosophy**: Copy-paste commands first, understand later.

---

## Quick Diagnostics

### Stack Health Check
```powershell
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Automated Drift Detection
```powershell
.\infrastructure\scripts\stack_doctor.ps1
```

### Fix Common Issues Automatically
```powershell
.\infrastructure\scripts\stack_doctor.ps1 -Fix
```

---

## Common Failures

### 1. Container Restarting

**Symptom**: `docker ps` shows "Restarting (X) Y seconds ago"

**Quick Fix**:
```powershell
# Check logs for error
docker logs cdb_<service> --tail 30

# If secret file error → see "Secret File Errors" section
# If port conflict → see "Port Conflicts" section
# If health check failing → see "Health Check Failures" section
```

---

### 2. Secret File Errors

**Symptom**: Logs show "cat: read error: Is a directory" or "secret file does not exist"

**Quick Fix**:
```powershell
# Step 1: Verify secret files exist and are FILES (not directories)
ls ../.cdb_local/.secrets/

# Expected output:
# -rw-r--r-- redis_password (24 bytes)
# -rw-r--r-- postgres_password (any size)

# Step 2: If directories exist, they're INVALID
# Fix: Create actual files with password content
# Example:
"your_password_here" | Out-File -FilePath ../.cdb_local/.secrets/postgres_password -NoNewline -Encoding ASCII

# Step 3: Restart stack
docker-compose down
.\infrastructure\scripts\stack_up.ps1 -Logging
```

---

### 3. "Both PASSWORD and PASSWORD_FILE are set"

**Symptom**: Postgres logs show "both POSTGRES_PASSWORD and POSTGRES_PASSWORD_FILE are set (but are exclusive)"

**Quick Fix**:
```powershell
# Step 1: Check if plaintext password env var exists
[Environment]::GetEnvironmentVariable("POSTGRES_PASSWORD", "User")

# Step 2: Remove it (Policy violation - no plaintext passwords!)
[Environment]::SetEnvironmentVariable("POSTGRES_PASSWORD", $null, "User")
[Environment]::SetEnvironmentVariable("REDIS_PASSWORD", $null, "User")

# Step 3: Restart PowerShell to apply changes
# Step 4: Restart stack
docker-compose down
.\infrastructure\scripts\stack_up.ps1 -Logging
```

---

### 4. Port Conflicts

**Symptom**: Error "port is already allocated" or "address already in use"

**Quick Fix**:
```powershell
# Step 1: Find which process is using the port
netstat -ano | findstr :<PORT>

# Step 2: Kill the process (if not needed)
Stop-Process -Id <PID> -Force

# Alternative: Change port in infrastructure/compose/dev.yml
# Example: Change "6379:6379" to "6380:6379"

# Step 3: Restart stack
.\infrastructure\scripts\stack_up.ps1
```

---

### 5. Health Check Failures

**Symptom**: Container shows "unhealthy" in `docker ps`

**Quick Fix**:
```powershell
# Step 1: Check what the healthcheck is testing
docker inspect cdb_<service> --format '{{json .State.Health}}' | ConvertFrom-Json

# Step 2: Run healthcheck manually
docker exec cdb_<service> <healthcheck_test_command>

# Example for Postgres:
docker exec cdb_postgres pg_isready -U claire_user -d claire_de_binare

# Example for Redis:
docker exec cdb_redis redis-cli ping

# Step 3: If healthcheck command fails, check service logs
docker logs cdb_<service> --tail 50
```

---

### 6. Volume Permission Errors

**Symptom**: Logs show "permission denied" or "cannot write to directory"

**Quick Fix**:
```powershell
# Step 1: Check volume ownership
docker exec cdb_<service> ls -la /data

# Step 2: Fix permissions (if needed)
docker exec -u root cdb_<service> chown -R <user>:<group> /data

# Example for Postgres:
docker exec -u root cdb_postgres chown -R postgres:postgres /var/lib/postgresql/data

# Step 3: Restart container
docker restart cdb_<service>
```

---

### 7. Orphaned Containers/Volumes

**Symptom**: Old containers or volumes cluttering `docker ps -a` or `docker volume ls`

**Quick Fix**:
```powershell
# Safe clean (preserves data volumes)
.\infrastructure\scripts\stack_clean.ps1

# Deep clean (DELETES ALL DATA - use with caution!)
.\infrastructure\scripts\stack_clean.ps1 -DeepClean
```

---

### 8. Stack Won't Start

**Symptom**: `stack_up.ps1` fails or hangs

**Quick Fix**:
```powershell
# Step 1: Bring down everything
docker-compose down

# Step 2: Check for conflicting resources
.\infrastructure\scripts\stack_doctor.ps1

# Step 3: Fix issues automatically
.\infrastructure\scripts\stack_doctor.ps1 -Fix

# Step 4: Try starting again
.\infrastructure\scripts\stack_up.ps1 -Logging
```

---

### 9. Grafana Datasource Provisioning Failures

**Symptom**: Grafana logs show "failed to provision data sources"

**Quick Fix**:
```powershell
# Step 1: Check if Postgres is healthy
docker exec cdb_postgres pg_isready -U claire_user -d claire_de_binare

# Step 2: Check if Postgres secret file is mounted
docker exec cdb_grafana ls -la /run/secrets/

# Expected: postgres_password file should exist

# Step 3: If secret missing, check compose file secret mounts
# File: infrastructure/compose/base.yml
# Should have:
#   cdb_grafana:
#     secrets:
#       - postgres_password (via grafana_password)

# Step 4: Restart Grafana
docker restart cdb_grafana
```

---

## Disaster Recovery

### Create Backup

```powershell
.\infrastructure\scripts\dr_backup.ps1
```

**Output**: `infrastructure/dr_backups/cdb_backup_YYYYMMDD_HHMMSS.zip`

---

### Restore from Backup

```powershell
# List available backups
ls infrastructure/dr_backups/*.zip

# Restore specific backup
.\infrastructure\scripts\dr_restore.ps1 -BackupName cdb_backup_YYYYMMDD_HHMMSS -Force
```

**Warning**: This will REPLACE all current data!

---

### Test DR Procedures (Automated)

```powershell
.\infrastructure\scripts\dr_drill.ps1
```

**What it does**:
1. Creates backup
2. Destroys all containers and volumes
3. Restores from backup
4. Verifies data integrity

**Use case**: Quarterly DR testing to meet Criterion F

---

## Rollback Procedures

### Tag Current State for Rollback

```powershell
.\infrastructure\scripts\stack_tag.ps1 -Latest
```

**Creates**: Rollback point with current Docker images

---

### Rollback to Previous State

```powershell
# Rollback to latest tagged state
.\infrastructure\scripts\stack_rollback.ps1 -Force

# Rollback to specific tag
.\infrastructure\scripts\stack_rollback.ps1 -TagName rollback-20241224-153000 -Force
```

**Target**: < 60 seconds (Acceptance Criterion A)

---

## Service-Specific Procedures

### Postgres

**Check database connection**:
```powershell
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "\dt"
```

**Manual backup**:
```powershell
docker exec cdb_postgres pg_dump -U claire_user -d claire_de_binare > backup.sql
```

**Manual restore**:
```powershell
Get-Content backup.sql | docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare
```

**Reset database** (DESTRUCTIVE):
```powershell
docker exec cdb_postgres psql -U claire_user -d postgres -c "DROP DATABASE claire_de_binare;"
docker exec cdb_postgres psql -U claire_user -d postgres -c "CREATE DATABASE claire_de_binare;"
```

**Database Schema Initialization**:

**CRITICAL**: Init scripts in `/docker-entrypoint-initdb.d/` only run on **first startup** when `postgres_data` volume is empty.

**Dev: Force Schema Reload** (wipes all data):
```powershell
cd infrastructure/compose
docker-compose -f base.yml -f dev.yml down
docker volume rm claire_de_binare_postgres_data
docker-compose -f base.yml -f dev.yml up -d
```

**Prod: Apply Schema Manually** (preserves data):
```powershell
# Apply base schema
Get-Content infrastructure/database/schema.sql | docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare

# Apply migration 002
Get-Content infrastructure/database/migrations/002_orders_price_nullable.sql | docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare
```

**Verify Schema Loaded**:
```powershell
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "\dt"
# Expected: orders, trades, signals, positions, portfolio_snapshots, schema_version
```

**Troubleshooting**:
- If tables don't exist after first startup → check postgres logs:
  ```powershell
  docker logs cdb_postgres | Select-String "initdb"
  ```
- Look for "running /docker-entrypoint-initdb.d/01-schema.sql"
- If schema wasn't loaded → volume wasn't empty (remove and recreate)

---

### Redis

**Check Redis connection**:
```powershell
docker exec cdb_redis redis-cli ping
```

**Check keys**:
```powershell
docker exec cdb_redis redis-cli DBSIZE
```

**Flush all data** (DESTRUCTIVE):
```powershell
docker exec cdb_redis redis-cli FLUSHALL
```

**Force save**:
```powershell
docker exec cdb_redis redis-cli SAVE
```

---

### Prometheus

**Check Prometheus health**:
```powershell
docker exec cdb_prometheus wget -qO- http://localhost:9090/-/healthy
```

**Check targets**:
```powershell
# Open in browser
Start-Process "http://localhost:19090/targets"
```

**Reload config** (after editing prometheus.yml):
```powershell
docker exec cdb_prometheus kill -HUP 1
```

---

### Grafana

**Check Grafana health**:
```powershell
docker exec cdb_grafana curl -fsS http://localhost:3000/api/health
```

**Reset admin password**:
```powershell
docker exec cdb_grafana grafana-cli admin reset-admin-password <new_password>
```

**Open Grafana**:
```powershell
Start-Process "http://localhost:3000"
# Login: admin / (check grafana_password secret file)
```

---

### Loki + Promtail

**Check Loki health**:
```powershell
docker exec claire_de_binare-cdb_loki-1 wget -qO- http://localhost:3100/ready
```

**Check Promtail logs** (for scraping errors):
```powershell
docker logs claire_de_binare-cdb_promtail-1 --tail 50
```

**Query Loki** (via Grafana):
```
1. Open Grafana: http://localhost:3000
2. Go to Explore
3. Select Loki datasource
4. Query: {container_name="cdb_postgres"}
```

---

## Performance Issues

### High CPU Usage

```powershell
# Check which container is using CPU
docker stats --no-stream

# Check container processes
docker exec <container> ps aux

# Restart high-CPU container
docker restart <container>
```

---

### High Memory Usage

```powershell
# Check memory usage
docker stats --no-stream

# For Redis: Check memory stats
docker exec cdb_redis redis-cli INFO memory

# For Postgres: Check connections
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "SELECT count(*) FROM pg_stat_activity;"

# Restart if memory leak suspected
docker restart <container>
```

---

### Disk Space Issues

```powershell
# Check disk usage
docker system df

# Clean up unused resources (safe)
docker system prune -a

# Clean up volumes (DESTRUCTIVE - loses data!)
docker volume prune
```

---

## Network Issues

### Container Can't Reach Another Container

```powershell
# Check network connectivity
docker exec cdb_core ping cdb_postgres

# Check if containers are on same network
docker network inspect claire_de_binare_cdb_network

# Restart networking
docker-compose down
docker network prune
.\infrastructure\scripts\stack_up.ps1 -Logging
```

---

### DNS Resolution Failures

```powershell
# Check DNS
docker exec cdb_core nslookup cdb_postgres

# Restart Docker daemon (last resort)
Restart-Service docker
```

---

## Log Management

### View Logs

**Single container**:
```powershell
docker logs cdb_<service> --tail 100 -f
```

**All containers**:
```powershell
docker-compose logs -f
```

**Specific time range** (via Loki):
```
1. Open Grafana: http://localhost:3000
2. Go to Explore
3. Query: {container_name="cdb_postgres"} |= "error"
4. Select time range
```

---

### Clear Logs

```powershell
# Truncate container logs
docker-compose down
docker system prune -a --volumes
.\infrastructure\scripts\stack_up.ps1 -Logging
```

---

## Configuration Changes

### Update Docker Compose Config

```powershell
# Step 1: Edit config file
# Example: infrastructure/compose/dev.yml

# Step 2: Validate syntax
docker-compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml config

# Step 3: Apply changes (recreates containers)
docker-compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml up -d
```

---

### Update Prometheus Config

```powershell
# Step 1: Edit infrastructure/monitoring/prometheus.yml

# Step 2: Reload Prometheus
docker exec cdb_prometheus kill -HUP 1

# Step 3: Verify config
docker logs cdb_prometheus --tail 20
```

---

### Update Grafana Datasources

```powershell
# Step 1: Edit infrastructure/monitoring/grafana/provisioning/datasources/*.yml

# Step 2: Restart Grafana
docker restart cdb_grafana

# Step 3: Verify in UI
Start-Process "http://localhost:3000/datasources"
```

---

## Emergency Procedures

### Complete Stack Failure

```powershell
# Step 1: Stop everything
docker-compose down

# Step 2: Check for system-wide issues
docker info

# Step 3: Clean orphaned resources
.\infrastructure\scripts\stack_clean.ps1 -Force

# Step 4: Restart Docker daemon
Restart-Service docker

# Step 5: Start stack fresh
.\infrastructure\scripts\stack_up.ps1 -Logging
```

---

### Data Corruption Detected

```powershell
# Step 1: IMMEDIATE - Stop writes
docker stop cdb_core cdb_db_writer cdb_risk cdb_execution cdb_paper_runner

# Step 2: Create emergency backup
.\infrastructure\scripts\dr_backup.ps1

# Step 3: Verify backup integrity
Expand-Archive -Path infrastructure/dr_backups/cdb_backup_*.zip -DestinationPath temp_verify/
ls temp_verify/

# Step 4: Decide recovery strategy:
# Option A: Restore from last good backup
.\infrastructure\scripts\dr_restore.ps1 -BackupName cdb_backup_YYYYMMDD_HHMMSS -Force

# Option B: Attempt repair (Postgres example)
docker exec cdb_postgres pg_isready
# If healthy, data might be OK

# Step 5: Restart all services
.\infrastructure\scripts\stack_up.ps1 -Logging
```

---

### Security Incident

```powershell
# Step 1: IMMEDIATE - Isolate stack
docker-compose down

# Step 2: Enable network isolation for restart
.\infrastructure\scripts\stack_up.ps1 -NetworkIsolation

# Step 3: Check for unauthorized access
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "SELECT * FROM pg_stat_activity;"

# Step 4: Rotate all secrets
# - Generate new passwords
# - Update ../.cdb_local/.secrets/ files
# - Restart services

# Step 5: Verify compliance
.\infrastructure\scripts\stack_doctor.ps1
```

---

## Monitoring

### Key Metrics to Watch

**Container Health**:
```powershell
watch -n 5 'docker ps --format "table {{.Names}}\t{{.Status}}"'
```

**Resource Usage**:
```powershell
docker stats --no-stream
```

**Log Errors** (via Loki):
```
Query: {container_name=~"cdb_.*"} |= "error" or "fatal" or "exception"
```

---

## Preventive Maintenance

### Weekly

- Run `.\infrastructure\scripts\stack_doctor.ps1 -Verbose`
- Check disk space: `docker system df`
- Review logs for recurring errors

### Monthly

- Create backup: `.\infrastructure\scripts\dr_backup.ps1`
- Test rollback: `.\infrastructure\scripts\stack_tag.ps1 -Latest`
- Update images: `docker-compose pull && .\infrastructure\scripts\stack_up.ps1`

### Quarterly

- Run DR drill: `.\infrastructure\scripts\dr_drill.ps1`
- Review and rotate old backups
- Verify all runbook procedures still work

---

## E2E Regression Shield (CI & Local)

**Purpose**: Automated protection against regressions in Paper Trading flow (Order → Execution → order_results).

**Coverage**: 4 test cases validating Pub/Sub flow, schema contracts, stream persistence, and subscriber health.

**Status**: ✅ Active on every PR (`.github/workflows/e2e-tests.yml`)

---

### Running E2E Tests Locally

**Prerequisites**:
- Stack running: `.\infrastructure\scripts\stack_up.ps1 -Logging`
- Redis accessible: `docker exec cdb_redis redis-cli ping`
- Core services healthy: `docker ps` shows 9+ containers running

**Run Tests**:
```powershell
# From repository root
$env:E2E_RUN="1"
pytest tests/e2e/test_paper_trading_p0.py -v --no-cov -rs
```

**Expected Output**:
```
test_order_to_execution_flow PASSED        [25%]
test_order_results_schema PASSED           [50%]
test_stream_persistence PASSED             [75%]
test_subscriber_count PASSED               [100%]

4 passed in ~15s
```

**Environment Variables**:
- `E2E_RUN=1` - **Required** to enable E2E tests (safety gate)
- `REDIS_PASSWORD` - Optional, defaults to `claire_redis_secret_2024`

---

### CI Trigger Rules

**Workflow**: `.github/workflows/e2e-tests.yml`

**Triggers on PR changes to**:
- `services/**` (any service code changes)
- `tests/e2e/**` (test changes)
- `infrastructure/**` (compose files, configs, database schema)
- `.github/workflows/e2e-tests.yml` (workflow itself)

**Manual Trigger**:
```
GitHub Actions → E2E Tests - Paper Trading → Run workflow
```

**Timeout**: 15 minutes (entire workflow)

**When Does It NOT Run**:
- Changes to `docs/**` only
- Changes to `scripts/**` (non-infrastructure)
- Changes to `.md` files only

---

### CI Workflow Steps

1. **Checkout** - Get PR code
2. **Setup Python 3.11** - Install pytest + redis-py
3. **Start Stack** - `docker-compose -f base.yml -f dev.yml up -d`
4. **Health Checks** (60s timeout each):
   - Redis: `redis-cli ping` returns `PONG`
   - Postgres: `pg_isready` confirms accepting connections
   - Core services: Wait 10s, then `docker compose ps`
5. **Run E2E Tests** - `E2E_RUN=1 pytest tests/e2e/test_paper_trading_p0.py -v --no-cov -rs`
6. **Capture Logs on Failure**:
   - `docker compose ps` (service status)
   - `docker compose logs --tail=300` (last 300 lines)
7. **Upload Artifacts** - Logs saved for 7 days
8. **Cleanup** - `docker-compose down -v` (always runs)

---

### Artifacts & Logs (CI Failures)

**Where to Find**:
1. Go to failed PR check
2. Click "Details" on "E2E Tests - Paper Trading"
3. Scroll to bottom → "Artifacts" section
4. Download `e2e-failure-logs` (ZIP file)

**Retention**: 7 days

**What's Included**:
- `docker compose ps` output (service health status)
- Last 300 lines of logs from all services
- Timestamp of failure

**Logs Location (local)**:
```powershell
# If tests fail locally, check:
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml logs --tail=300

# Specific service:
docker logs cdb_execution --tail=100
docker logs cdb_risk --tail=100
```

---

### Troubleshooting Tree

#### Test Failure: "Could not connect to Redis"

**Diagnostic Commands**:
```powershell
# 1. Check Redis container running
docker ps | Select-String "cdb_redis"

# 2. Check Redis accepts connections
docker exec cdb_redis redis-cli ping
# Expected: PONG

# 3. Check password (if AUTH error)
docker exec cdb_redis redis-cli -a claire_redis_secret_2024 ping

# 4. Check port mapping (if running tests from host)
docker port cdb_redis
# Expected: 6379/tcp -> 0.0.0.0:6379
```

**Fix**:
- If container not running → check `docker logs cdb_redis`
- If AUTH error → verify `REDIS_PASSWORD` env var
- If port not mapped → use internal hostname `cdb_redis` instead of `localhost`

---

#### Test Failure: "No order_result received after 10 seconds"

**Diagnostic Commands**:
```powershell
# 1. Check execution service is running and subscribed
docker logs cdb_execution --tail=50 | Select-String "orders"
# Expected: "Subscribed to channel: orders"

# 2. Check if execution service is processing orders
docker logs cdb_execution --tail=50 | Select-String "order"

# 3. Check subscriber count on orders channel
docker exec cdb_redis redis-cli PUBSUB NUMSUB orders
# Expected: orders <count>  (count should be >= 1)

# 4. Manually test order publishing
docker exec cdb_redis redis-cli PUBLISH orders '{"order_id":"test-123","symbol":"BTC/USDT","side":"BUY","quantity":0.001}'
# Expected: Returns number of subscribers (should be >= 1)
```

**Fix**:
- If execution not subscribed → restart: `docker restart cdb_execution`
- If execution crashed → check logs: `docker logs cdb_execution --tail=100`
- If order_results not published → verify execution service publish logic (see #225)

---

#### Test Failure: "Expected at least 2 subscribers on order_results"

**Diagnostic Commands**:
```powershell
# 1. Check current subscriber count
docker exec cdb_redis redis-cli PUBSUB NUMSUB order_results
# Expected: order_results 2 (or more)

# 2. Check which services should subscribe
# Expected subscribers: cdb_risk, cdb_db_writer (minimum)
docker logs cdb_risk --tail=30 | Select-String "order_results"
docker logs cdb_db_writer --tail=30 | Select-String "order_results"
# Expected: "Subscribed to channel: order_results" or similar

# 3. Check if services are running
docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String -Pattern "cdb_risk|cdb_db_writer"
```

**Fix**:
- If subscriber count = 0 → all subscribers crashed or not started
- If subscriber count = 1 → one service down (check which)
- Restart missing subscriber: `docker restart cdb_risk` or `docker restart cdb_db_writer`

---

#### Test Failure: "Stream length did not increase"

**Diagnostic Commands**:
```powershell
# 1. Check if stream.fills exists
docker exec cdb_redis redis-cli EXISTS stream.fills
# Expected: 1 (exists)

# 2. Check stream length
docker exec cdb_redis redis-cli XLEN stream.fills
# Should be > 0 if any orders processed

# 3. Read latest entries
docker exec cdb_redis redis-cli XREVRANGE stream.fills + - COUNT 5

# 4. Check execution service XADD logic
docker logs cdb_execution --tail=50 | Select-String "stream"
```

**Fix**:
- If stream doesn't exist → execution service not adding events (check logs)
- If stream exists but not growing → execution service not processing orders
- Verify `config.STREAM_ORDER_RESULTS` is set in execution service

---

#### Test Failure: "Timestamp must be Unix int, got str"

**Root Cause**: Schema mismatch - execution service sending ISO string instead of Unix int.

**Diagnostic Commands**:
```powershell
# 1. Manually subscribe and check payload format
docker exec -it cdb_redis redis-cli
> SUBSCRIBE order_results
# Trigger an order, observe the JSON payload

# 2. Check execution service to_dict() logic
# File: services/execution/models.py
# ExecutionResult.to_dict() should return timestamp as int, not string
```

**Fix**:
- Update `ExecutionResult.to_dict()` to send Unix timestamp (int)
- See Issue #225 for reference fix
- DO NOT change receiver schema - sender must align

---

### Definition of Done (Phase 2 PRs)

**All Phase 2 feature PRs must**:

✅ **E2E Workflow Green** - All 4 tests pass in CI

✅ **No E2E Skip** - Tests actually run (not skipped due to missing `E2E_RUN=1`)

✅ **Logs Reviewed on Fail** - If tests fail, PR author must:
   - Download artifacts from CI
   - Check service logs for root cause
   - Fix issue before merge (no "merge anyway" exceptions)

**Verification Command**:
```powershell
# Before creating PR, run locally:
$env:E2E_RUN="1"
pytest tests/e2e/test_paper_trading_p0.py -v --no-cov

# All 4 tests must pass
```

---

### Future Enhancements

**Not Implemented (Optional)**:
- ❌ Nightly regression runs (PR-only sufficient for now)
- ❌ Error case coverage (rejected orders, timeouts) - separate issue
- ❌ Performance benchmarks (latency tracking) - Phase 3

**When to Add Nightly**:
- If PR-only misses intermittent failures
- If external dependency instability (Docker registry, etc.)
- If team requests scheduled confidence checks

**How to Add Nightly**:
```yaml
# Add to .github/workflows/e2e-tests.yml trigger section:
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily
```

---

## Contact & Escalation

### Self-Service Tools

1. `.\infrastructure\scripts\stack_doctor.ps1 -Fix` - Auto-fix common issues
2. `LEGACY_FILES.md` - Migration guide
3. `infrastructure/compose/COMPOSE_LAYERS.md` - Architecture reference

### When to Escalate

- Data loss detected (immediate escalation)
- Security incident (immediate escalation)
- Stack down > 15 minutes (escalate after exhausting runbook)
- Repeated failures after following runbook (escalate with logs)

---

## Appendix

### File Locations

- **Compose files**: `infrastructure/compose/*.yml`
- **Scripts**: `infrastructure/scripts/*.ps1`
- **Configs**: `infrastructure/monitoring/*.yml`
- **Secrets**: `../.cdb_local/.secrets/*`
- **Backups**: `infrastructure/dr_backups/*.zip`

### Useful Commands Cheat Sheet

```powershell
# Quick start
.\infrastructure\scripts\stack_up.ps1 -Logging

# Health check
docker ps --format "table {{.Names}}\t{{.Status}}"

# Logs
docker logs cdb_<service> --tail 50 -f

# Cleanup
.\infrastructure\scripts\stack_clean.ps1

# Backup
.\infrastructure\scripts\dr_backup.ps1

# Rollback
.\infrastructure\scripts\stack_rollback.ps1 -Force

# Doctor
.\infrastructure\scripts\stack_doctor.ps1 -Fix
```

---

## See Also

- `infrastructure/compose/COMPOSE_LAYERS.md` - Architecture
- `LEGACY_FILES.md` - Migration guide
- `FUTURE_SERVICES.md` - Planned services
