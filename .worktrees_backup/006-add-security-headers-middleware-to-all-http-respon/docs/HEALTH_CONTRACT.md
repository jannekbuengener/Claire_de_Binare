# Service Health Contract

**Purpose**: Define explicit health criteria for all Claire de Binare services to prevent silent failures and restart loops.

**Status**: ✅ Implemented (Issue #243)
**Last Updated**: 2025-12-27

---

## Health Categories

All services must belong to one of these health categories:

### 1. HEALTHY
- Service is fully operational
- All dependencies are available
- Can handle incoming requests/events
- Health check returns success (HTTP 200, exit 0)

### 2. ALLOWED_STARTING
- Service is initializing but not yet ready
- Dependencies may still be unavailable
- Health check fails but restart is deferred
- Uses `start_period` to allow graceful startup

### 3. FAILED
- Service cannot recover without intervention
- Health check fails after retries exhausted
- Container enters restart loop (unless `restart: never`)
- Requires manual investigation

---

## Service Health Matrix

| Service | Health Check Type | Interval | Timeout | Retries | Start Period | Fail-Fast? |
|---------|------------------|----------|---------|---------|--------------|------------|
| **Infrastructure** |
| `cdb_redis` | redis-cli ping | 10s | 3s | 3 | - | ✅ YES |
| `cdb_postgres` | pg_isready | 10s | 3s | 3 | - | ✅ YES |
| `cdb_prometheus` | HTTP /-/healthy | 30s | 10s | 3 | - | ✅ YES |
| `cdb_grafana` | HTTP /api/health | 30s | 10s | 3 | - | ❌ NO |
| **Application Services** |
| `cdb_core` | Process alive (kill -0) | 30s | 3s | 3 | - | ❌ NO |
| `cdb_risk` | HTTP /health | 30s | 5s | 3 | - | ❌ NO |
| `cdb_execution` | None (manual) | - | - | - | - | ❌ NO |
| `cdb_db_writer` | None (manual) | - | - | - | - | ❌ NO |
| `cdb_paper_runner` | HTTP /health | 30s | 10s | 3 | 10s | ❌ NO |

---

## Health Check Patterns

### Pattern 1: Infrastructure Services (Fail-Fast)

**Apply to**: Redis, Postgres, Prometheus

**Rationale**: Critical infrastructure must be healthy immediately. If these fail, dependent services cannot function.

**Example (Redis)**:
```yaml
healthcheck:
  test: ["CMD", "sh", "-c", "redis-cli -a $$REDIS_PASSWORD ping"]
  interval: 10s
  timeout: 3s
  retries: 3
  # No start_period = fail fast
```

**Failure Mode**: Container restarts immediately if health check fails 3 times.

---

### Pattern 2: Monitoring Services (Tolerate-Starting)

**Apply to**: Grafana

**Rationale**: Monitoring is not critical for trading operations. Can tolerate delayed startup.

**Example (Grafana)**:
```yaml
healthcheck:
  test: ["CMD", "curl", "-fsS", "http://localhost:3000/api/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  # Implicit start_period via restart policy
```

**Failure Mode**: Container restarts after retries, but non-blocking for other services.

---

### Pattern 3: Application Services (HTTP Health Endpoint)

**Apply to**: Risk Service, Paper Runner

**Rationale**: Services expose /health endpoint that checks internal state and dependencies.

**Example (Risk Service)**:
```yaml
healthcheck:
  test: ["CMD", "curl", "-fsS", "http://localhost:8002/health"]
  interval: 30s
  timeout: 5s
  retries: 3
```

**Health Endpoint Requirements**:
- Return HTTP 200 if healthy
- Return HTTP 503 if unhealthy (dependencies down, internal error)
- Check Redis/Postgres connections
- Check critical state (e.g., kill-switch not active)

---

### Pattern 4: Application Services (Process Alive Check)

**Apply to**: Core Service

**Rationale**: Service is event-driven with no HTTP endpoint. Simple process alive check.

**Example (Core)**:
```yaml
healthcheck:
  test: ["CMD-SHELL", "kill -0 1 || exit 1"]
  interval: 30s
  timeout: 3s
  retries: 3
```

**Failure Mode**: Only detects process death, not internal failures.

---

### Pattern 5: No Health Check (Manual Monitoring)

**Apply to**: Execution Service, DB Writer

**Rationale**: Services run fire-and-forget tasks. Health is monitored via logs and downstream effects.

**Monitoring Strategy**:
- Check logs for errors: `docker logs cdb_execution --tail 50`
- Check downstream data (orders published to Redis, rows in DB)
- Use kill-switch if critical failures detected

---

## Dependency Health Requirements

### Service Startup Order

Services must declare health dependencies using `depends_on.condition`:

```yaml
cdb_risk:
  depends_on:
    cdb_redis:
      condition: service_healthy  # REQUIRED
    cdb_postgres:
      condition: service_healthy  # REQUIRED
```

**Rule**: Application services MUST wait for infrastructure services to be HEALTHY before starting.

---

### Dependency Health Matrix

| Service | Required Healthy Dependencies |
|---------|-------------------------------|
| `cdb_core` | cdb_redis, cdb_postgres |
| `cdb_risk` | cdb_redis, cdb_postgres |
| `cdb_execution` | cdb_redis, cdb_postgres |
| `cdb_db_writer` | cdb_redis, cdb_postgres |
| `cdb_paper_runner` | cdb_redis, cdb_postgres |
| `cdb_grafana` | cdb_prometheus |
| `cdb_prometheus` | None (infrastructure) |
| `cdb_redis` | None (infrastructure) |
| `cdb_postgres` | None (infrastructure) |

---

## Health Check Timing Guidelines

### Interval
- **Infrastructure**: 10s (fast detection)
- **Application**: 30s (reduce overhead)

### Timeout
- **Infrastructure**: 3s (quick response expected)
- **Application**: 5-10s (allow for network/DB queries)

### Retries
- **All Services**: 3 retries (gives 30s-90s recovery window)

### Start Period
- **Default**: None (fail-fast)
- **Slow-starting services**: 10s (e.g., paper_runner)
- **Monitoring services**: Implicit via restart policy

---

## Failure Scenarios & Response

### Scenario 1: Redis Connection Lost

**Symptoms**:
- cdb_redis healthcheck fails
- Application services fail health checks
- Logs show "Redis connection refused"

**Response**:
1. Check Redis logs: `docker logs cdb_redis`
2. Verify Redis password: `docker exec cdb_redis redis-cli -a $REDIS_PASSWORD ping`
3. Restart Redis if needed: `docker restart cdb_redis`
4. Application services auto-recover when Redis healthy

---

### Scenario 2: Postgres Not Ready

**Symptoms**:
- cdb_postgres healthcheck fails
- Application services stuck in ALLOWED_STARTING
- Logs show "could not connect to database"

**Response**:
1. Check Postgres logs: `docker logs cdb_postgres`
2. Verify schema loaded: `docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c '\dt'`
3. Restart Postgres if needed: `docker restart cdb_postgres`
4. Application services auto-start when Postgres healthy

---

### Scenario 3: Application Service Silent Failure

**Symptoms**:
- Health check passes but service not functioning
- No orders processed, no events published
- Process is alive but stuck

**Response**:
1. Check service logs for errors
2. Verify Redis/Postgres connectivity from service
3. Check kill-switch state: `/health` endpoint or state file
4. Restart service: `docker restart cdb_risk`

---

### Scenario 4: Restart Loop (Excessive Failures)

**Symptoms**:
- Container restarts every 30-60 seconds
- Health check fails immediately after restart
- Logs repeat initialization errors

**Response**:
1. Identify root cause: dependency down, config error, code bug
2. Fix root cause (e.g., correct .env, update schema)
3. Stop stack: `make docker-down`
4. Fix configuration/code
5. Restart stack: `make docker-up`
6. Monitor health: `make docker-health`

---

## Health Check Best Practices

### ✅ DO:
- Use HTTP health endpoints for web services
- Check critical dependencies in health endpoint
- Return HTTP 503 for unhealthy state (not 500)
- Log health check failures for debugging
- Use `depends_on.condition: service_healthy` for critical dependencies
- Set appropriate timeouts (3s infrastructure, 5-10s application)
- Test health checks locally before deploying

### ❌ DON'T:
- Return HTTP 200 when dependencies are down
- Use health checks for slow-running background tasks
- Set timeout > interval (causes false failures)
- Skip health checks for critical services
- Use `restart: always` without health checks (causes silent restart loops)
- Hardcode secrets in health check commands

---

## Health Check Verification

### Manual Verification

```powershell
# Check all service health
make docker-health

# Check specific service
docker inspect cdb_redis --format='{{.State.Health.Status}}'
# Expected: "healthy"

# View health check logs
docker inspect cdb_redis --format='{{range .State.Health.Log}}{{.Output}}{{end}}'

# Test health endpoint manually
curl http://localhost:8002/health
# Expected: {"status":"ok"}
```

---

### Automated Verification (CI/E2E)

```python
# tests/e2e/test_health_contract.py
def test_all_services_healthy():
    """Verify all services report healthy status."""
    services = ["cdb_redis", "cdb_postgres", "cdb_risk", "cdb_core"]
    for service in services:
        result = subprocess.run(
            ["docker", "inspect", service, "--format={{.State.Health.Status}}"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "healthy", f"{service} is not healthy"
```

---

## Health Contract Evolution

### Adding New Services

When adding a new service:

1. **Determine Health Category**: Fail-Fast or Tolerate-Starting?
2. **Choose Health Check Pattern**: HTTP endpoint, process check, or none?
3. **Set Timing**: interval/timeout/retries based on service type
4. **Declare Dependencies**: `depends_on` with `condition: service_healthy`
5. **Document**: Add row to Service Health Matrix
6. **Test**: Verify health check works and fails appropriately

---

### Modifying Existing Health Checks

Before changing a health check:

1. **Document Rationale**: Why is change needed?
2. **Test Locally**: Verify new health check works
3. **Test Failure Modes**: Verify service restarts correctly on failure
4. **Update Documentation**: Update this contract
5. **Update Tests**: Update E2E health contract tests
6. **Communicate**: Notify team of health check changes

---

## References

- **Compose Files**: infrastructure/compose/base.yml, infrastructure/compose/dev.yml
- **Emergency Stop SOP**: docs/EMERGENCY_STOP_SOP.md (kill-switch health impact)
- **Stack Lifecycle**: docs/STACK_LIFECYCLE.md (health check in startup sequence)
- **Issue**: #243 (Health Contract Definition)

---

**Approval**: [Pending]
**Review Date**: [Pending]
**Version**: 1.0
