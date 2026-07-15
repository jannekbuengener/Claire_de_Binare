# False Positive Alert Investigation - 2026-01-19

**Investigation Date:** 2026-01-19
**Duration:** ~2 hours
**Status:** ✅ RESOLVED

---

## Summary

Daily Digest showed RED status due to 2 critical alerts firing:
- `DatabaseConnectionLost` (pg_up == 0)
- `RedisConnectionLost` (redis_up == 0)

**Investigation revealed:** Alerts were **FALSE POSITIVES** caused by misconfigured exporters. Actual DB and Redis services were healthy and running normally.

---

## Problem Analysis

### 1. Initial Observations

**Daily Digest (2026-01-19 10:33 UTC):**
```markdown
Status: RED
2 critical alert(s) firing

Top 3 Alerts:
- DatabaseConnectionLost: 1 (critical)
- RedisConnectionLost: 1 (critical)
- TradePipelineStalled: 1 (warning)
```

**Container Health:**
```bash
cdb_postgres: Up 2 days (healthy)
cdb_redis: Up 2 days (healthy)
cdb_redis_exporter: Up 2 days (unhealthy)  ← SUSPECT
```

**Prometheus Targets:**
- All 9 targets showing "up" status
- postgres_exporter: Last scrape successful
- redis_exporter: Last scrape successful

**Contradiction:** Exporters scraping successfully, but metrics show services down.

---

### 2. Metric Investigation

**postgres_exporter metrics:**
```bash
# Query pg_up metric
docker exec cdb_prometheus wget -qO- \
  "http://localhost:9090/api/v1/query?query=pg_up"

Result: pg_up = 0  # FALSE - Postgres is healthy
```

**redis_exporter metrics:**
```bash
# Query redis_up metric
docker exec cdb_prometheus wget -qO- \
  "http://localhost:9090/api/v1/query?query=redis_up"

Result: redis_up = 0  # FALSE - Redis is healthy
```

**Direct connection tests:**
```bash
# Test Postgres
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "SELECT 1"
Result: 1 (1 row)  ✅ CONNECTED

# Test Redis
docker exec cdb_redis sh -c 'redis-cli -a $(cat /run/secrets/redis_password) ping'
Result: PONG  ✅ CONNECTED
```

**Conclusion:** Services healthy, exporters reporting incorrect metrics.

---

### 3. Root Cause Analysis

#### postgres_exporter

**Configuration (base.yml):**
```yaml
cdb_postgres_exporter:
  environment:
    DATA_SOURCE_NAME_FILE: /run/secrets/postgres_password_dsn  # ❌ INVALID
```

**Exporter Logs:**
```
time=2026-01-17T14:15:20.409Z level=WARN msg="Failed to create PostgresCollector" err="empty dsn"
```

**Research Finding:** postgres_exporter does NOT support `DATA_SOURCE_NAME_FILE` environment variable.

**Supported variables:**
- `DATA_SOURCE_NAME` - Direct connection string (not _FILE)
- `DATA_SOURCE_URI_FILE` - URI only (requires separate user/pass files)

**Source:** [postgres_exporter README](https://github.com/prometheus-community/postgres_exporter/blob/master/README.md)

#### redis_exporter

**Configuration (base.yml):**
```yaml
cdb_redis_exporter:
  command: ["sh", "-c", "redis_exporter --redis.addr=$$REDIS_ADDR --redis.password=$$(cat /run/secrets/redis_password)"]
```

**Exporter Logs:**
```
time="2026-01-19T14:05:43Z" level=error msg="Redis INFO err: NOAUTH Authentication required."
```

**Root Cause:** Password file contains trailing newline character, causing authentication failure.

**Secret File Content:**
```bash
cat /run/secrets/redis_password | od -c
...
development_redis_password_P1DPfB4gUSat91Yx6McPMA==\n  # ← NEWLINE
```

---

## Solution

### 1. postgres_exporter Fix

**Changed:**
```yaml
# BEFORE (WRONG)
environment:
  DATA_SOURCE_NAME_FILE: /run/secrets/postgres_password_dsn

# AFTER (CORRECT)
entrypoint: ["/bin/sh", "-c"]
command: ["DATA_SOURCE_NAME=$$(cat /run/secrets/postgres_password_dsn) exec /bin/postgres_exporter"]
```

**Explanation:** Read DSN from secret file and set as environment variable at runtime.

### 2. redis_exporter Fix

**Changed:**
```yaml
# BEFORE (WRONG)
command: ["sh", "-c", "redis_exporter --redis.addr=$$REDIS_ADDR --redis.password=$$(cat /run/secrets/redis_password)"]

# AFTER (CORRECT)
entrypoint: ["/bin/sh", "-c"]
command: ["exec redis_exporter --redis.addr=redis://cdb_redis:6379 --redis.password=$$(cat /run/secrets/redis_password | tr -d '\\n')"]
```

**Explanation:** Strip trailing newline from password using `tr -d '\n'`.

---

## Validation

### 1. Exporter Health

**postgres_exporter logs (after fix):**
```
time=2026-01-19T14:18:19.331Z level=INFO msg="Established new database connection" fingerprint=cdb_postgres:5432
time=2026-01-19T14:18:19.353Z level=INFO msg="Semantic version changed" server=cdb_postgres:5432 from=0.0.0 to=15.15.0
```

**redis_exporter logs (after fix):**
```
time="2026-01-19T14:18:17Z" level=info msg="Providing metrics at :9121/metrics"
(no errors)
```

### 2. Metrics Verification

**Before:**
```json
{"metric": {"__name__": "pg_up"}, "value": [1768831872, "0"]}
{"metric": {"__name__": "redis_up"}, "value": [1768831872, "0"]}
```

**After:**
```json
{"metric": {"__name__": "pg_up"}, "value": [1768832313, "1"]}  ✅
{"metric": {"__name__": "redis_up"}, "value": [1768832315, "1"]}  ✅
```

### 3. Alert Status

**Before:**
```json
{"alertname": "DatabaseConnectionLost", "state": "firing", "severity": "critical"}
{"alertname": "RedisConnectionLost", "state": "firing", "severity": "critical"}
{"alertname": "TradePipelineStalled", "state": "firing", "severity": "warning"}
```

**After:**
```json
{"alertname": "TradePipelineStalled", "state": "firing", "severity": "warning"}
```

**Result:** Critical alerts RESOLVED (2 → 0). Only TradePipelineStalled remains (correct).

---

## Impact on Daily Digest

### Before Fix (10:33 UTC)

```markdown
Status: RED
**2 critical alert(s) firing**

Incidents:
- 2 critical alert(s) firing (active now)
```

### After Fix (14:19 UTC)

```markdown
Status: RED
**Approval rate critically low: 0.0%**

Top 3 Alerts:
- TradePipelineStalled: 1 (severity: warning)

Incidents:
- Approval rate critically low: 0.0% (active now)
```

**Key Change:**
- **Before:** RED due to false positive alerts (monitoring failure)
- **After:** RED due to real issue (0% approval rate - Scenario A)

**Now monitoring shows REAL system state:**
- Risk manager blocking 100% of signals (3469/3469 blocked)
- Zero trades executed (execution never reached)
- TradePipelineStalled correctly detecting Scenario A (Risk Blockade)

---

## Lessons Learned

### 1. Environment Variable Documentation

**Problem:** Assumed `DATA_SOURCE_NAME_FILE` exists (like Postgres `POSTGRES_PASSWORD_FILE`).

**Reality:** Each exporter has different conventions. Always check documentation.

**Pattern Found:**
- Official images (postgres, grafana): Support `_FILE` suffix
- Community exporters: May NOT support `_FILE` pattern

### 2. Secret File Hygiene

**Problem:** Trailing newlines in secret files break authentication.

**Solution:** Always strip whitespace when reading secrets:
```bash
cat /run/secrets/password | tr -d '\n'
```

### 3. False Positive Detection

**Indicators of false positives:**
1. Metrics show service down, but container healthy
2. Direct connection tests succeed
3. Exporter scraping successfully, but metrics incorrect
4. Exporter logs show configuration errors

**Investigation Priority:**
1. Check exporter logs first (fastest indicator)
2. Test direct connections (ground truth)
3. Verify environment variables in running container
4. Check documentation for correct configuration

---

## Evidence Trail

### Commands Used

```bash
# 1. Check container health
docker ps --filter name=cdb_postgres --filter name=cdb_redis --format "table {{.Names}}\t{{.Status}}"

# 2. Check Prometheus targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job, health}'

# 3. Check metrics
docker exec cdb_prometheus wget -qO- "http://localhost:9090/api/v1/query?query=pg_up"
docker exec cdb_prometheus wget -qO- "http://localhost:9090/api/v1/query?query=redis_up"

# 4. Test direct connections
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "SELECT 1"
docker exec cdb_redis sh -c 'redis-cli -a $(cat /run/secrets/redis_password) ping'

# 5. Check exporter logs
docker logs cdb_postgres_exporter --tail 50
docker logs cdb_redis_exporter --tail 50

# 6. Verify secret files
docker exec cdb_postgres_exporter cat /run/secrets/postgres_password_dsn
docker exec cdb_redis_exporter cat /run/secrets/redis_password | od -c

# 7. Check environment variables
docker exec cdb_postgres_exporter env | grep DATA
docker inspect cdb_postgres_exporter --format='{{json .Config.Env}}' | jq
```

### Files Modified

1. **infrastructure/compose/base.yml**
   - Fixed postgres_exporter configuration (line 118-119)
   - Fixed redis_exporter configuration (line 136-137)
   - Commit: 802a7bc

2. **docs/evidence/reports/shadow_mode/DAILY_DIGEST_2026-01-19.md**
   - Updated digest with resolved status
   - Commit: f582d4f

---

## Related Documentation

- [postgres_exporter GitHub](https://github.com/prometheus-community/postgres_exporter)
- [ALERTING_DIGEST_EVIDENCE.md](./ALERTING_DIGEST_EVIDENCE.md) - Alert routing validation
- [PRE_INCIDENT_EVAL_until_2026-01-17T21_17_02Z.md](./PRE_INCIDENT_EVAL_until_2026-01-17T21_17_02Z.md) - Shadow Mode validity
- [TradePipelineStalled alert definition](../../../../infrastructure/monitoring/alerts.yml#L243)

---

## Next Steps

1. **✅ COMPLETED:** Resolve false positive critical alerts
2. **CURRENT:** Investigate 0% approval rate (Scenario A: Risk Blockade)
3. **PENDING:** Check circuit breaker state and risk limits
4. **PENDING:** Validate Shadow Mode data accuracy

---

*False Positive Investigation Report - Claire de Binare Trading Bot*
*Generated: 2026-01-19 15:20 UTC*
