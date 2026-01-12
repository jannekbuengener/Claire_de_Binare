# Shadow Mode START - 5-Day Validation Run

**Start Time:** 2026-01-12 18:32:16 UTC
**Duration:** 5 days (120 hours)
**End Time:** 2026-01-17 18:32:16 UTC (expected)
**Purpose:** Validate system readiness for Canary deployment with empirically-set thresholds

---

## Shadow Mode Acceptance Criteria (DoD)

Based on 24h Baseline Run empirical data (397 orders, 2026-01-11 to 2026-01-12):

| Criterion | Threshold | Baseline Result | Check Frequency |
|-----------|-----------|-----------------|-----------------|
| **1. Success Rate** | ≥ 95% | 96.7% ✅ | Daily |
| **2. Error Rate** | ≤ 5% | 3.3% ✅ | Daily |
| **3. Latency p95** | < 200ms | ~172ms ✅ | Weekly (min 20 orders) |
| **4. Data Consistency** | 100% (0 discrepancies) | 100% ✅ | Daily |
| **5. Risk Block Coverage** | > 0 blocks cumulative | 0 ⚠️ (validation pending) | Cumulative over 5 days |
| **6. Service Stability** | **0 unplanned restarts** | 1 unplanned ❌ (baseline) | Continuous |

**Rollback Triggers:**
- **ABORT if:** 2+ unplanned restarts in 5 days
- **ABORT if:** Data inconsistency detected (Redis ≠ Postgres)
- **INVESTIGATE if:** Success Rate < 90% for 2+ consecutive days
- **INVESTIGATE if:** Latency p95 > 300ms sustained

**Planned Restarts:** Allowed IF marker in `knowledge/logs/ops/maintenance.log` BEFORE event (<5min downtime, root cause documented)

---

## T0 Snapshot (2026-01-12 18:32 UTC)

### System Status
**All services UP (33 minutes):**
- cdb_ws: healthy
- cdb_signal: healthy
- cdb_risk: healthy
- cdb_execution: healthy
- cdb_allocation: healthy
- cdb_regime: healthy
- cdb_candles: healthy
- cdb_paper_runner: healthy
- cdb_db_writer: healthy
- cdb_redis: healthy
- cdb_postgres: healthy
- cdb_prometheus: healthy
- cdb_grafana: healthy

**Last restart:** 2026-01-12 ~17:59 UTC (stack restart from baseline period - root cause documented in Issue #547)

### Prometheus Counters (T0)

| Metric | Value (T0) |
|--------|------------|
| `execution_orders_received_total` | 131 |
| `execution_orders_filled_total` | 128 |
| `execution_orders_rejected_total` | 5 |
| `orders_blocked_total` | 0 |
| `circuit_breaker_active` | 0 |

**Initial Rates:**
- **Success Rate:** 128/131 = **97.7%** (exceeds 95% target ✅)
- **Error Rate:** 5/131 = **3.8%** (below 5% target ✅)
- **Risk Block Rate:** 0/131 = **0%** (validation pending)

### Data Consistency (T0)

**Reconciliation Check:** ✅ **RECONCILIATION OK**

| Source | Count (T0) |
|--------|------------|
| Redis `stream.fills` | 520 |
| PostgreSQL `orders` (filled + rejected) | 520 |
| **Difference** | 0 |

**Status:** 100% consistency (Redis = Postgres)

**Note:** Prometheus shows 131 orders (since last restart ~33min ago), but persistent stores (Redis + Postgres) show 520 total orders since system initialization. Shadow Mode tracking will use **delta calculations** to avoid restart-related counter resets.

---

## Shadow Mode Monitoring Plan

### Daily Checks (every 24h at ~18:30 UTC)

**1. Data Consistency Check**
```bash
./scripts/baseline_reconciliation.sh
# Expected: 0 discrepancies (Redis = Postgres)
# Rollback trigger: ANY mismatch
```

**2. Success/Error Rate Tracking**
```bash
# Get T+Nh snapshot (replace N with day number: 1, 2, 3, 4, 5)
docker exec cdb_prometheus wget -qO- 'http://localhost:9090/api/v1/query?query=execution_orders_received_total'
docker exec cdb_prometheus wget -qO- 'http://localhost:9090/api/v1/query?query=execution_orders_filled_total'
docker exec cdb_prometheus wget -qO- 'http://localhost:9090/api/v1/query?query=execution_orders_rejected_total'

# Calculate delta: (count_TN - count_T0) for 24h window
# Success Rate = filled_delta / received_delta
# Error Rate = rejected_delta / received_delta
# Threshold: Success ≥ 95%, Error ≤ 5%
```

**3. Service Stability Check**
```bash
# Check for unplanned restarts
docker ps --filter "name=cdb_" --format "{{.Names}}\t{{.Status}}"
cat knowledge/logs/ops/maintenance.log | tail -5

# Expected: All services UP, no new unplanned entries in maintenance.log
# Rollback trigger: 2+ unplanned restarts
```

**4. Risk Block Coverage (cumulative)**
```bash
docker exec cdb_prometheus wget -qO- 'http://localhost:9090/api/v1/query?query=orders_blocked_total'
# Expected: > 0 by end of 5 days (validates Risk Manager functional)
```

### Weekly Check (Day 5)

**5. Latency Sample (p95)**
```bash
# Sample last 20 orders from execution logs
docker logs cdb_execution --tail 500 | grep -E "Processing order|Published result" | tail -40

# Calculate timestamp diffs → p95
# Threshold: < 200ms
# Investigate if: > 300ms sustained
```

---

## Shadow Mode Rules (Active)

**Trading Mode:** Paper Trading (Mock Executor)
- No real API calls to MEXC
- Simulated order execution with realistic delays
- Mock rejections for liquidity simulation (~3-5% rejection rate)

**Risk Management:** ACTIVE
- Circuit breaker: MONITORING (not triggered)
- Position limits: ENFORCED (paper trading limits)
- Volatility checks: ACTIVE
- Expected: 0 risk blocks in normal market conditions (baseline showed 0/397)

**Data Flow:** FULL PIPELINE
```
MEXC WebSocket → cdb_ws → Redis → cdb_signal → cdb_risk → cdb_execution → stream.fills
                                                                                ↓
                                                                         cdb_db_writer
                                                                                ↓
                                                                            PostgreSQL
```

**Observability:**
- Grafana Dashboard: `CDB - System Health & Trade Flow` (14 panels)
- Maintenance Panel: Shows last 5 restart events (planned vs unplanned)
- Prometheus: All metrics scraped every 15s
- Logs: Docker logs retained for debugging

**Cost:** 0 EUR (no new services, existing stack only)

---

## Baseline Context (Reference)

**24h Baseline Run (2026-01-11 18:43 to 2026-01-12 18:04 UTC):**
- Orders processed: 397
- Success Rate: 96.7% (exceeds target)
- Error Rate: 3.3% (below target)
- Latency p95: ~172ms (below target)
- Data Consistency: 100% (0 discrepancies)
- **Finding:** 1 unplanned restart at ~18:00 UTC (root cause: TBD, documented in Issue #547)

**Threshold Adjustments:**
- Latency: 500ms → 200ms (based on empirical data)
- DoD: "0 Restarts" → "0 Unplanned Restarts" (planned maintenance allowed)

**Evidence:**
- Baseline START: `knowledge/logs/sessions/2026-01-11_baseline_start.md`
- Baseline EVALUATION: `knowledge/logs/sessions/2026-01-12_baseline_evaluation.md`
- Reconciliation Script: `scripts/baseline_reconciliation.sh`
- Maintenance Log: `knowledge/logs/ops/maintenance.log`

---

## Next Steps

**Daily (at ~18:30 UTC for 5 days):**
1. Run reconciliation check
2. Collect Prometheus counters (calculate delta from T0)
3. Check service stability (docker ps + maintenance.log)
4. Log results in daily check files (Day 1-5)

**Day 5 (2026-01-17 18:32 UTC):**
1. Final snapshot (T+120h)
2. Latency sample (last 20 orders)
3. Risk block verification (cumulative > 0?)
4. Shadow Mode Evaluation Report
5. Decision: GO/NO-GO for Canary deployment

**Monitoring:**
- Watch Grafana Dashboard for anomalies
- Review maintenance.log for unplanned restarts
- Investigate if Success Rate drops below 90%

---

## Cost Accounting

**Shadow Mode Run Cost:** **0 EUR** ✅

**Infrastructure:** Existing stack (no new services)
**Monitoring:** Prometheus + Grafana (already running)
**Data:** Redis + Postgres (already operational)
**Checks:** Bash scripts + docker commands (0 cost)
**CI:** No CI runs during Shadow Mode (manual checks only)

---

**Shadow Mode Status:** **ACTIVE** (5-Day Run Started)
**Expected End:** 2026-01-17 18:32 UTC
**Next Check:** 2026-01-13 18:30 UTC (Day 1 Daily Check)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
