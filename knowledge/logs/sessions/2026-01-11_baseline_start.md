# Baseline-Run START - Shadow Mode Preparation

**Start Time:** 2026-01-11 18:43:24 UTC
**Duration:** 24 hours
**End Time:** 2026-01-12 18:43:24 UTC (expected)
**Purpose:** Collect empirical data for Shadow Mode Acceptance Criteria thresholds

---

## Baseline Snapshot (T0)

### System Status
**All services UP:**
- cdb_ws: UP (1h, healthy)
- cdb_signal: UP (1h, healthy)
- cdb_risk: UP (1h, healthy)
- cdb_execution: UP (1h, healthy)

### Prometheus Counters (T0 = 2026-01-11 18:43 UTC)

| Metric | Value (T0) |
|--------|-----------|
| `execution_orders_received_total` | 42 |
| `execution_orders_filled_total` | 38 |
| `execution_orders_rejected_total` | 4 |
| `orders_blocked_total` | 0 |
| `circuit_breaker_active` | 0 |

**Initial Rates:**
- **Success Rate:** 38/42 = **90.5%** (below estimated 95%)
- **Error Rate:** 4/42 = **9.5%** (above estimated 5%)
- **Risk Block Rate:** 0/42 = **0%** (no risk blocks active)

**Finding:** Initial estimates (95% success, 5% error) were too optimistic. Real system shows ~90% success.

---

## Data Consistency (T0)

### Reconciliation Check
**Script:** `scripts/baseline_reconciliation.sh`
**Result:** ✅ RECONCILIATION OK

| Source | Count (T0) |
|--------|-----------|
| Redis `stream.fills` | 144 |
| PostgreSQL `orders` (filled + rejected) | 144 |
| **Difference** | 0 |

**Status:** 100% consistency (Redis = Postgres)

---

## Latency Sample (T0)

**Method:** Log-based timestamp analysis (0 EUR cost)
**Sample:** Last 6 orders from execution service logs

| Order ID | Processing Start | Published | Latency |
|----------|-----------------|-----------|---------|
| MOCK_62865966 | 18:41:13.926 | 18:41:13.982 | ~56ms |
| MOCK_66941088 | 18:42:31.522 | 18:42:31.600 | ~78ms |
| MOCK_80409314 | 18:39:47.226 | 18:39:47.326 | ~100ms |
| MOCK_50392746 | 18:39:11.929 | 18:39:12.032 | ~103ms |
| MOCK_42319137 | 18:37:47.230 | 18:37:47.363 | ~133ms |
| MOCK_89284280 (REJECTED) | 18:37:04.037 | 18:37:04.174 | ~137ms |

**Observed Latency:**
- Min: 56ms
- Max: 137ms
- **Average: ~101ms**
- **p95 estimate: <150ms** (well below 500ms threshold)

**Note:** Latency measured = "Processing order" → "Published result" (execution service only, not end-to-end)

---

## Market Conditions (T0)

**BTC Price:** $49,961 - $50,047 (range from last 6 orders)
**Volatility:** Low (< 0.2% price movement in logs)
**Trade Frequency:** ~1 order per 30-60 seconds

**Baseline Conditions:** Normal market, low volatility, paper trading mode (Mock Executor)

---

## Measurement Plan (24h)

### Metrics to Collect (T+24h)
1. **Success Rate:** `(filled_total_T24 - filled_total_T0) / (received_total_T24 - received_total_T0)`
2. **Error Rate:** `(rejected_total_T24 - rejected_total_T0) / (received_total_T24 - received_total_T0)`
3. **Risk Blocks:** `orders_blocked_total_T24 - orders_blocked_total_T0`
4. **Data Consistency:** Run `baseline_reconciliation.sh` (expect 0 diff)
5. **Latency:** Sample last 20 orders from logs, calculate p95/p99
6. **Service Uptime:** Check for crashes/restarts in Docker logs

### Success Criteria (Baseline Run)
- ✅ No service crashes or manual restarts
- ✅ Reconciliation check passes (Redis = Postgres)
- ✅ At least 50 orders processed (statistical significance)
- ✅ Latency p95 < 500ms

### Expected Deliverables (T+24h)
1. Final threshold values for Shadow Mode Acceptance Criteria
2. Decision: Adjust 95% success threshold based on empirical data
3. Baseline Report with graphs/trends (optional, if time permits)

---

## Cost Accounting

**Infrastructure:** 0 EUR (existing stack, no new services)
**Measurement:** 0 EUR (Prometheus already scraping, logs already captured)
**Reconciliation Script:** 0 EUR (bash + docker exec, no CI)
**Total:** **0 EUR** ✅

---

## Next Steps

**T+24h (2026-01-12 18:43 UTC):**
1. Collect End-Snapshot (Prometheus counters T24)
2. Run reconciliation check
3. Sample latency from logs (last 20 orders)
4. Calculate delta metrics (Success Rate, Error Rate over 24h)
5. Set final Shadow Mode thresholds based on empirical data
6. Document Baseline Report
7. Start official 5-day Shadow Mode Run

**Reminder:** DO NOT START Shadow Mode until Baseline complete + thresholds validated!

---

**Baseline Run Status:** IN PROGRESS (24h timer started)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
