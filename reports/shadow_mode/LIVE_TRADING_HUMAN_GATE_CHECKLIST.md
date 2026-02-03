# Live Trading Human Gate Checklist

**System:** Claire de Binare (CDB) Control Layer
**Incident:** P0 - Regime Consumer Silent Failure (RESOLVED)
**Current State:** Shadow Mode
**Checklist Date:** 2026-02-03 15:07 UTC
**P0 Fix Merged:** 2026-02-03 15:05:21 UTC (PR #774)

---

## Incident Context

**Root Cause:** Missing exception handling in regime consumer loop caused silent exit on Redis failures. Flask remained healthy while consumer died silently for 27 hours.

**Fix Applied:**
- Exception handling around XREAD loop
- Redis reconnect with ping verification
- Heartbeat metric (regime_last_heartbeat_timestamp_seconds)
- Error counter (regime_consumer_errors_total)
- Health endpoint returns 503 on stalled consumer (>60s heartbeat age)

**Recovery Verified:** 2026-02-03 14:51:24 UTC
- Backlog processed (candles_processed: 1636 → 1660)
- Heartbeat active (< 1s age)
- Zero consumer errors
- Test candle processed correctly

---

## 1. SHADOW MODE SOAK (MINIMUM 48h)

**Status:** ❌ **FAIL** (NOT VERIFIED)

**Requirements:**
- [ ] Shadow Mode runtime ≥ 48h continuous
- [ ] No container restarts in BLUE stack (cdb_candles, cdb_regime, cdb_allocation, cdb_ws)
- [ ] regime_last_heartbeat_timestamp_seconds continuously fresh (age < 60s)
- [ ] rate(regime_candles_processed_total[5m]) > 0 at all times
- [ ] regime_consumer_errors_total stable (no spikes)

**Evidence:**
- P0 fix deployed: 2026-02-03 14:51:24 UTC
- Current time: 2026-02-03 15:07 UTC
- **Elapsed: ~16 minutes** (< 48h requirement)

**Result:** ❌ **FAIL** - Insufficient soak time. Minimum 48h continuous runtime required.

**Earliest Re-evaluation:** 2026-02-05 14:51 UTC

---

## 2. ALERTING ENABLED & VERIFIED

**Status:** ❌ **FAIL** (NOT VERIFIED)

**Requirements:**
- [ ] RegimeConsumerStalled alert exists
  - expr: `rate(regime_candles_processed_total[5m]) == 0`
- [ ] RegimeHealthError alert exists
  - Health endpoint returns HTTP 503 for >2 minutes
- [ ] Redis/Stream lag alert (if applicable)
- [ ] Alerts tested and demonstrated firing

**Evidence:**
- **MISSING:** No Prometheus alert rules found in repository
- **MISSING:** No alert testing evidence
- **MISSING:** No alert configuration files

**Result:** ❌ **FAIL** - No alerting infrastructure configured or verified.

**Required Actions:**
1. Deploy Prometheus alert rules
2. Test alert firing conditions
3. Document alert response procedures

---

## 3. FAIL-CLOSED RISK & EXECUTION

**Status:** ❌ **NOT VERIFIED**

**Requirements:**
- [ ] Risk service blocks orders if regime is stale
- [ ] Risk service blocks orders if allocation is stale
- [ ] Risk service blocks orders if signals are missing
- [ ] Execution requires explicit human approval
- [ ] End-to-end Shadow Test passed (Market → Candle → Regime → Allocation → Risk → Execution)

**Evidence:**
- **MISSING:** No end-to-end shadow test evidence
- **MISSING:** No stale regime rejection test
- **MISSING:** No stale allocation rejection test
- **PARTIAL:** Decision contract v1 merged (PR #765) includes risk gates

**Result:** ❌ **NOT VERIFIED** - No evidence of fail-closed behavior testing.

**Required Actions:**
1. Execute end-to-end shadow test with real market data
2. Test stale regime rejection (inject old regime timestamp)
3. Test stale allocation rejection (simulate allocation service failure)
4. Document fail-closed behavior validation

---

## 4. DATA INTEGRITY & SIGNAL CORRECTNESS

**Status:** ⚠️ **PARTIAL PASS**

**Requirements:**
- [x] Regime processes ONLY intended symbols (BTCUSDT verified via test)
- [ ] Candle schema stable (no frequent parse failures)
- [ ] Allocation emits decisions ONLY on valid regime changes
- [ ] No unexplained regime flips or allocation decisions

**Evidence:**
- ✅ Symbol filtering verified: Test #1 (symbol=TEST) correctly ignored
- ✅ BTCUSDT processing verified: Test #2 processed synthetic candle
- ✅ Confirmation bars logic working: Extreme candle didn't trigger duplicate regime (already HIGH_VOL_CHAOTIC)
- **MISSING:** Long-term candle parse failure rate
- **MISSING:** Allocation decision correctness validation over time

**Result:** ⚠️ **PARTIAL PASS** - Core logic verified, but insufficient long-term data.

**Required Actions:**
1. Monitor `Candle.from_payload()` failure rate over 48h
2. Verify allocation decisions align with regime changes
3. Document any schema validation errors

---

## 5. OPERATIONAL RUNBOOK

**Status:** ❌ **FAIL** (NOT VERIFIED)

**Requirements:**
- [ ] Runbook exists and is accessible
- [ ] Restart policy defined (auto vs manual)
- [ ] Rollback procedure documented (image/tag/commit)
- [ ] On-call responsibility defined

**Evidence:**
- **MISSING:** No operational runbook found
- **MISSING:** No restart policy documentation
- **MISSING:** No rollback procedure
- **MISSING:** No on-call assignment

**Result:** ❌ **FAIL** - No operational runbook exists.

**Required Actions:**
1. Create operational runbook with:
   - Service restart procedures
   - Rollback steps (including Docker image tags)
   - Escalation paths
   - On-call contact information
2. Test runbook procedures in staging
3. Store in accessible location (e.g., `docs/operations/`)

---

## ADDITIONAL OBSERVATIONS

**Current Metrics (2026-02-03 15:07 UTC):**
```
regime_candles_processed_total: 1660+
regime_consumer_errors_total: 0
regime_last_heartbeat_timestamp_seconds: 1770131169.315178 (fresh)
heartbeat_age_seconds: 0.055 (< 1s)
health status: "ok" (HTTP 200)
```

**Service Status:**
- Blue Stack: All services UP and healthy
- Consumer: Active, processing candles
- No errors observed since recovery

**Outstanding Issues:**
- 48h soak period not yet elapsed
- No alerting infrastructure
- No end-to-end shadow test evidence
- No operational runbook

---

## FINAL DECISION

**Status:** ❌ **NO-GO**

**Rationale:**

**Critical Failures:**
1. **Soak Time:** 16 minutes elapsed, 48h required (HARD FAIL)
2. **Alerting:** No alerts configured or tested (HARD FAIL)
3. **Operational Readiness:** No runbook (HARD FAIL)
4. **Testing:** No end-to-end fail-closed verification (HARD FAIL)

**Summary:**
- 1 of 5 sections PARTIAL PASS
- 4 of 5 sections FAIL or NOT VERIFIED
- **MINIMUM 48h soak period MUST complete before re-evaluation**

**Live trading is FORBIDDEN.**

---

## RE-EVALUATION CRITERIA

**Earliest Re-evaluation Date:** 2026-02-05 14:51 UTC (48h post-fix)

**Required Before Re-evaluation:**
1. ✅ Complete 48h continuous runtime (NO restarts)
2. ❌ Deploy and test Prometheus alerts
3. ❌ Execute end-to-end shadow test with fail-closed validation
4. ❌ Create and test operational runbook
5. ⚠️ Validate data integrity over full 48h period

**Next Review:** Manual trigger after 48h soak completion + alert deployment + runbook creation

---

**Gate Status:** 🔴 **CLOSED**
**Human Approval:** **DENIED**
**Shadow Mode:** **CONTINUES**

---

*This checklist enforces live trading discipline. No exceptions permitted.*
*Governance Agent: Claude Code (Sonnet 4.5)*
*Generated: 2026-02-03 15:07 UTC*
