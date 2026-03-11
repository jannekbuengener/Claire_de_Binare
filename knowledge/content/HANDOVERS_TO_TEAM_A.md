# Team B → Team A Handovers

**From:** Team B (Dev-Stream)
**To:** Team A (Infra-Stream)
**Date:** 2025-12-29
**Status:** Deliverable

---

## 📋 Handover Summary

Team B delivers **3 critical handovers** to enable Team A's infrastructure work:

1. **Test Execution Contract** - How to run/validate the test suite
2. **Infrastructure Requirements** - ENV vars, Redis streams, ports needed
3. **Minimal Metrics** - Prometheus metrics for E2E validation

**Rule:** Each handover = 1 page summary + 1 artifact link (per protocol)

---

## Handover #1: Test Execution Contract

### Summary (1 Page)

**Purpose:** Define how Team A can execute and validate the test suite

**Command (Single Entry Point):**
```powershell
.venv/Scripts/python.exe -m pytest tests/ -v
```

**Expected Outputs:**

| Test Suite | Command | Success Criteria | Duration |
|------------|---------|------------------|----------|
| Smoke | `pytest tests/unit/test_models.py -v` | 3/3 PASSED | < 1s |
| Unit | `pytest tests/unit/ -v` | 180+ PASSED | < 30s |
| E2E | `pytest -m e2e tests/e2e/ -v` | 20+ PASSED | 2-5 min |

**Failure Signatures (Team A Must Recognize):**

```python
# 1. Missing Dependencies
ModuleNotFoundError: No module named 'pytest'
→ Solution: pip install -r requirements-dev.txt

# 2. Docker Stack Not Running
redis.exceptions.ConnectionError: Error connecting to Redis
→ Solution: docker-compose up -d

# 3. Environment Variable Missing
KeyError: 'POSTGRES_PASSWORD'
→ Solution: Check secrets mounted in docker-compose
```

**DoD (Definition of Done):**
- [ ] Smoke suite PASSES (3/3 tests)
- [ ] No collection errors
- [ ] Coverage report generated (if --cov flag used)

**Artifact:** 📄 [TEST_HARNESS_V1.md](TEST_HARNESS_V1.md) (full guide)

---

## Handover #2: Infrastructure Requirements

### Summary (1 Page)

**Purpose:** Define what infrastructure Team A must provide for Team B's code

### Required Environment Variables

**Per Service (cdb_signal example):**

| ENV Var | Required? | Default | Purpose | Set By |
|---------|-----------|---------|---------|--------|
| `REDIS_HOST` | ✅ Yes | - | Redis hostname | compose |
| `REDIS_PASSWORD` | ✅ Yes | - | Redis auth | secrets |
| `POSTGRES_HOST` | ✅ Yes | - | Postgres hostname | compose |
| `POSTGRES_USER` | ✅ Yes | - | Postgres username | compose |
| `POSTGRES_PASSWORD` | ✅ Yes | - | Postgres auth | secrets |
| `SIGNAL_STRATEGY_ID` | ✅ Yes | - | Strategy identifier | compose |
| `SIGNAL_PORT` | ⚠️ Optional | 8001 | HTTP port | compose |
| `SIGNAL_THRESHOLD_PCT` | ⚠️ Optional | 3.0 | Signal threshold | compose |
| `SIGNAL_MIN_VOLUME` | ⚠️ Optional | 100000 | Volume filter | compose |
| `LOG_LEVEL` | ⚠️ Optional | INFO | Logging verbosity | compose |

**Pattern:** All services follow same structure (REDIS_*, POSTGRES_*, service-specific)

### Required Redis Streams

| Stream | Producer | Consumer | Purpose | Max Length |
|--------|----------|----------|---------|------------|
| `stream.market_data` | cdb_ws | cdb_signal | Trade data | 10000 |
| `stream.signals` | cdb_signal | cdb_risk | Trading signals | 10000 |
| `stream.orders` | cdb_risk | cdb_execution | Order commands | 10000 |
| `stream.fills` | cdb_execution | cdb_db_writer | Fill confirmations | 10000 |

**Note:** Streams are auto-created by XADD, but Team A should monitor length

### Required Redis Pub/Sub Topics

| Topic | Producer | Consumers | Purpose |
|-------|----------|-----------|---------|
| `market_data` | cdb_ws | cdb_signal | Real-time trades |
| `signals` | cdb_signal | cdb_risk, cdb_db_writer | Trading signals |
| `orders` | cdb_risk | cdb_execution, cdb_db_writer | Order flow |
| `alerts` | All services | Monitoring | Error alerts |

### Required Ports (Localhost Binding)

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| cdb_redis | 6379 | TCP | Redis server |
| cdb_postgres | 5432 | TCP | PostgreSQL |
| cdb_prometheus | 19090 | HTTP | Metrics scraping |
| cdb_grafana | 3000 | HTTP | Dashboards |
| cdb_ws | 8000 | HTTP | WebSocket service API |
| cdb_signal | 8005 | HTTP | Signal engine API |
| cdb_risk | 8002 | HTTP | Risk manager API |
| cdb_execution | 8003 | HTTP | Execution service API |

**Binding Rule:** All ports bound to `127.0.0.1` (localhost only) for security

### Secrets Architecture Requirements

**Location:** `/run/secrets/` (Docker secrets)

**Required Secrets:**
- `redis_password` (Redis AUTH)
- `postgres_password` (Postgres password)

**Access Pattern:**
```bash
# In container entrypoint:
export REDIS_PASSWORD=$(cat /run/secrets/redis_password)
export POSTGRES_PASSWORD=$(cat /run/secrets/postgres_password)
exec python -u service.py
```

**Team A Responsibilities:**
- Mount secrets from `${SECRETS_PATH}/.cdb/` → `/run/secrets/`
- Ensure secrets readable by service user (e.g., signaluser:1000)
- Rotate secrets without service downtime (use secrets versioning)

**Artifact:** 📄 [CONTRACTS.md](CONTRACTS.md) (stream schemas)

---

## Handover #3: Minimal Metrics for E2E Validation

### Summary (1 Page)

**Purpose:** Define which Prometheus metrics Team A must expose for E2E validation

### Critical Metrics (Must Have)

**Per Service:**

| Metric | Service | Type | Purpose | Success Criteria |
|--------|---------|------|---------|------------------|
| `decoded_messages_total` | cdb_ws | Counter | Trades decoded | > 0, monotonic |
| `redis_publish_total` | cdb_ws | Counter | Messages published | > 0, monotonic |
| `signals_generated_total` | cdb_signal | Counter | Signals created | > 0 after threshold triggers |
| `signal_engine_status` | cdb_signal | Gauge | Service health | 1 = running, 0 = stopped |
| `risk_pending_orders_total` | cdb_risk | Gauge | Orders in validation | >= 0 |
| `risk_total_exposure_value` | cdb_risk | Gauge | Portfolio exposure | >= 0 |

### E2E Validation Query

**Command:**
```bash
# Check all critical metrics
curl -s http://localhost:8000/metrics | grep -E "decoded_messages_total|redis_publish_total"
curl -s http://localhost:8005/metrics | grep -E "signals_generated_total|signal_engine_status"
curl -s http://localhost:8002/metrics | grep -E "risk_pending_orders_total|risk_total_exposure_value"
```

**Success Criteria (Healthy Pipeline):**
```prometheus
# cdb_ws
decoded_messages_total > 0
redis_publish_total > 0

# cdb_signal
signals_generated_total > 0  # After price movement > threshold
signal_engine_status 1

# cdb_risk
risk_pending_orders_total >= 0
risk_total_exposure_value >= 0
```

### Metric Collection Requirements

**Prometheus Scrape Config:**
```yaml
# Team A must configure:
scrape_configs:
  - job_name: 'cdb_services'
    scrape_interval: 15s
    static_configs:
      - targets:
        - 'cdb_ws:8000'
        - 'cdb_signal:8005'
        - 'cdb_risk:8002'
        - 'cdb_execution:8003'
```

**Endpoint Standard:**
- Path: `/metrics`
- Format: Prometheus text format
- Timeout: 5s max
- Auth: None (internal network only)

### Alerting Thresholds (Recommendations to Team A)

```yaml
# Suggested Grafana alerts:
- alert: SignalEngineDown
  expr: signal_engine_status == 0
  for: 1m

- alert: NoSignalsGenerated
  expr: rate(signals_generated_total[5m]) == 0
  for: 10m

- alert: WebSocketStalled
  expr: rate(decoded_messages_total[1m]) == 0
  for: 2m
```

**Artifact:** 📄 Prometheus queries in `/infrastructure/monitoring/prometheus.yml`

---

## 🚨 Escalation Protocol

### If Team B Needs from Team A:

**Example:** "Team B needs XLEN metric for stream.signals"

1. Create finding: `FINDING: stream.signals length not exposed as metric`
2. Mark as blocker: `BLOCKER: Team A (Infra)`
3. Escalate to Orchestrator with impact statement
4. Wait for Team A response (max 1 page summary)

### If Team A Needs from Team B:

**Example:** "Team A needs to know what log level is safe for production"

1. Team A creates finding: `FINDING: LOG_LEVEL production recommendation unclear`
2. Mark as blocker: `BLOCKER: Team B (Dev)`
3. Team B responds with 1-page summary + artifact link

---

## ✅ Handover Checklist (Team B Complete)

- [x] **Handover #1:** Test Execution Contract defined
- [x] **Handover #2:** Infra requirements documented (ENV, streams, ports, secrets)
- [x] **Handover #3:** Minimal metrics for E2E validation specified
- [x] **Artifacts:** All linked (TEST_HARNESS_V1.md, CONTRACTS.md, prometheus.yml)
- [x] **Escalation:** Protocol defined (1-page summary, blocker marking)

**Team A Action Required:**
- [ ] Review handovers
- [ ] Confirm all requirements feasible
- [ ] Identify blockers (if any)
- [ ] Respond with 1-page summary of gaps/questions

---

**Deliverable:** Team A Handovers ✅
**Status:** Ready for Team A review
**Format:** 3 handovers × 1 page + artifact links (per protocol)
