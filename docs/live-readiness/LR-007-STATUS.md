# LR-007 Shadow Mode Status

**Last Updated:** 2026-02-08 11:57 UTC
**Status:** ⏳ IN_PROGRESS (Day 0/30)

---

## Timeline

| Event | Date/Time (UTC) |
|-------|----------------|
| **Start** | 2026-02-07 12:43:48 (PR #806 merged) |
| **Elapsed** | 0 days 22 hours |
| **Remaining** | 30 days |
| **Target End** | 2026-03-09 12:43:48 |

---

## Scope

**Services Under Test (Control Layer):**
- `cdb_ws` (WebSocket Market Data)
- `cdb_regime` (Regime Classification)
- `cdb_allocation` (Allocation Decisions)
- `cdb_risk` (Risk Gates)
- `cdb_execution` (Order Lifecycle, `mock_trading=true`)
- `cdb_redis` (Stream Infrastructure)

**Markets:** BTCUSDT (1m timeframe), weitere optional

**Mode:** Shadow Mode (`mock_trading=true`, keine realen Exchange-Orders)

---

## Pass/Fail Criteria (per LR-007-SPEC.md)

### PASS Requirements (ALL must be met):
- ✅ Runtime ≥ 30 calendar days (Control Layer)
- ⏳ Container restarts = 0 (for Control Layer services)
- ⏳ Decision rate > 0 for ≥95% of measurement windows
- ⏳ Reject rate: 0.10 ≤ rate ≤ 0.90 (risk gates functioning)
- ⏳ Circuit breaker trips < 3
- ⏳ Kill switch never active
- ⏳ Error rate < 5%
- ⏳ Stream drop rate < 1%
- ⏳ All evidence artifacts exist

### HARD FAIL Triggers (ANY = immediate abort):
- ❌ Kill switch active > 60s
- ❌ Stream gap > 60 minutes
- ❌ Service producing no decisions for >15 min (sustained)
- ❌ Unauthorized order placement attempt
- ❌ Secrets leak
- ❌ Repeated circuit breaker (≥5 trips/24h)

---

## Current Metrics (TBD - Pending Evidence Collection)

**NOTE:** Metrics collection and daily digest generation pending. Required artifacts:
- Container uptime logs (RED/BLACK/BLUE stacks)
- Decision rate metrics (Prometheus queries)
- Circuit breaker trip counts
- Kill switch activation logs
- Stream gap monitoring

**Next Action:** Set up daily digest script or manual evidence collection process.

---

## Evidence Artifacts (Planned)

**Location:** `reports/shadow_mode/SOAK_TEST_LR007_<DATE>.md`

**Required Content:**
1. Daily uptime snapshots (Docker `ps` + health status)
2. Decision rate graphs (Grafana exports or Prometheus queries)
3. Circuit breaker/Kill switch event logs
4. Stream gap analysis (Redis XINFO STREAM queries)
5. Error rate summaries (service logs filtered)

**Frequency:** Daily or weekly digests, cumulative at Day 30

---

## Restart Policy

**Per LR-007 Spec:**
- **Planned restart** (stack upgrade, config change) → Resets counter to Day 0
- **Hotfix allowed:** Max 1 per 30-day period, <5min downtime, requires validation

**Current Restart Count:** 0 (as of start)

---

## Compliance Status

| Component | Status | Notes |
|-----------|--------|-------|
| `mock_trading=true` | ✅ ENFORCED | Validated by LR-002 Contract Tests |
| Exchange API Guards | ✅ ACTIVE | Circuit breaker blocks order placement |
| Decision Trace (LR-006A) | ✅ ACTIVE | Decision events logged |
| Secrets Protection | ✅ ACTIVE | Tresor-Zone enforced |

---

## References

- **Spec:** `docs/live-readiness/LR-007-SPEC.md`
- **PR:** #806 (merged 2026-02-07)
- **Commits:** 9ba22c0 (merge), 70b5439 (start), 67e4c27 (spec)
- **Related:** LR-001 to LR-006A (completed prerequisites)

---

## Next Steps

1. **Set up automated evidence collection** (Docker logs, Prometheus metrics)
2. **Create daily digest template** (`reports/shadow_mode/DAILY_DIGEST_<DATE>.md`)
3. **Monitor for HARD FAIL triggers** (especially stream gaps, kill switch)
4. **Weekly status review** (every 7 days, cumulative at Day 30)

---

**Approval Gate:** LR-007 PASS unlocks LR-008 Six-Eyes Policy discussion.
