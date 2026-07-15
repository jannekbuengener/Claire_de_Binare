# Control Layer Regime Transition Test Evidence

**Test Date:** 2026-02-03 14:20:05 UTC
**Test Type:** Synthetic Candle Injection → Regime Change → Allocation Decision
**Blue Stack:** All services UP and healthy
**Objective:** Validate Control Layer response to state transition

---

## Executive Summary

🔴 **TEST RESULT: FAIL**

**Root Cause:** Regime service did NOT process the injected synthetic candle. No regime change occurred, therefore no allocation decision was emitted.

**Critical Finding:** `cdb_regime` service shows ZERO processing activity in logs - only healthcheck pings. The service is NOT consuming from `stream.candles_1m`.

---

## 1. Pre-Check (Baseline) - ✅ PASS

```bash
# Timestamp
2026-02-03 14:20:05 UTC

# Blue Stack Status
docker compose -p blue_stk -f infrastructure/compose/compose.blue.yml ps
```

| Service | Status | Health |
|---------|--------|--------|
| cdb_allocation | Up 15 hours | healthy |
| cdb_candles | Up 27 hours | healthy |
| cdb_regime | Up 27 hours | healthy |
| cdb_ws | Up 2 days | healthy |

### Stream Baseline:
```bash
stream.candles_1m:           1623
stream.regime_signals:       1     ✅ (Guard: PASS)
stream.allocation_decisions: 1     ✅ (Guard: PASS)
```

**Guard Check:** PASS - Both regime_signals and allocation_decisions = 1 (clean isolated test state)

---

## 2. Candle Injection - ✅ Executed

```bash
docker exec cdb_redis sh -c 'redis-cli -a $(cat /run/secrets/redis_password) XADD stream.candles_1m "*" ts 1770128400 symbol TEST timeframe 60s open 100 high 140 low 60 close 135 volume 9999 trades 1 schema_version 1 source_version 1'

# Result: 1770128439816-0 (SUCCESS)
```

**Extreme Candle Characteristics:**
- **open:** 100
- **high:** 140 (+40% spike)
- **low:** 60 (-40% spike)
- **close:** 135 (+35% gain)
- **volume:** 9999 (extreme)
- **ATR/ADX trigger:** Guaranteed regime flip

---

## 3. Verification (30s post-inject) - 🔴 FAIL

```bash
# Stream lengths after 30s wait
stream.regime_signals:       1  (NO CHANGE ❌)
stream.allocation_decisions: 1  (NO CHANGE ❌)
stream.candles_1m:           1625 (+2, includes synthetic)
```

**Expected:**
- regime_signals: 1 → 2 (1 new regime emitted)
- allocation_decisions: 1 → 2 (1 new allocation emitted)

**Actual:**
- regime_signals: **1 → 1** (NO regime change)
- allocation_decisions: **1 → 1** (NO allocation change)

**FAIL Criterion Met:** "Kein Regime-Change nach 30s trotz Extrem-Candle"

---

## 4. Payload Evidence

### Latest Candles (last 3):
```
Stream ID: 1770128457097-0 (BTCUSDT, normal candle, ts=1770128400)
  symbol: BTCUSDT
  open: 78126.63, high: 78153.86, low: 78114.50, close: 78141.87
  volume: 8.56154731, trades: 147

Stream ID: 1770128439816-0 (TEST, synthetic inject ✅)
  symbol: TEST
  ts: 1770128400
  open: 100, high: 140, low: 60, close: 135
  volume: 9999, trades: 1

Stream ID: 1770128397093-0 (BTCUSDT, normal candle, ts=1770128340)
  symbol: BTCUSDT
  open: 78100.69, high: 78129.82, low: 78082.49, close: 78126.64
  volume: 25.15180887, trades: 143
```

**Observation:** Synthetic candle successfully inserted into stream at `1770128439816-0`.

### Last Regime Signal (unchanged):
```
Stream ID: 1770032038841-0
  ts: 1770031980 (26.7 hours ago)
  symbol: BTCUSDT
  regime: HIGH_VOL_CHAOTIC
  adx: 59.688852
  atr: 53.658422
  source_version: 1
```

**Observation:** Last regime signal is 26+ hours old. NO new regime emitted.

### Last Allocation Decision (unchanged):
```
Stream ID: 1770073374987-0
  ts: 1770031980 (26.7 hours ago)
  strategy_id: paper
  allocation_pct: 0.020000
  reason: regime=HIGH_VOL_CHAOTIC|risk_off|perf_not_ready
  cooldown_until: (empty)
```

**Observation:** Last allocation is 26+ hours old, matches old regime signal. NO new allocation.

---

## 5. Service Logs Analysis

### cdb_regime logs (50 lines tail):
```
Only healthcheck pings every 30s:
2026-02-03 14:19:26 [INFO] werkzeug: GET /health HTTP/1.1" 200
2026-02-03 14:19:56 [INFO] werkzeug: GET /health HTTP/1.1" 200
2026-02-03 14:20:26 [INFO] werkzeug: GET /health HTTP/1.1" 200
2026-02-03 14:20:56 [INFO] werkzeug: GET /health HTTP/1.1" 200
2026-02-03 14:21:26 [INFO] werkzeug: GET /health HTTP/1.1" 200
2026-02-03 14:21:57 [INFO] werkzeug: GET /health HTTP/1.1" 200
... (no processing activity)
```

**Critical Finding:** ZERO processing logs. No candle consumption, no indicator calculation, no regime emit.

### cdb_allocation logs (50 lines tail):
```
Only healthcheck pings every 30s:
2026-02-03 14:19:26 [INFO] werkzeug: GET /health HTTP/1.1" 200
2026-02-03 14:19:56 [INFO] werkzeug: GET /health HTTP/1.1" 200
2026-02-03 14:20:26 [INFO] werkzeug: GET /health HTTP/1.1" 200
2026-02-03 14:20:56 [INFO] werkzeug: GET /health HTTP/1.1" 200
2026-02-03 14:21:26 [INFO] werkzeug: GET /health HTTP/1.1" 200
2026-02-03 14:21:57 [INFO] werkzeug: GET /health HTTP/1.1" 200
... (no processing activity)
```

**Observation:** Also idle. Expected (no new regime signal to consume).

---

## 6. Root Cause Analysis

### Primary Issue: `cdb_regime` Not Consuming Stream

**Evidence:**
1. Synthetic candle successfully inserted into `stream.candles_1m` (ID: `1770128439816-0`)
2. `cdb_regime` service healthy (Docker healthcheck passing)
3. **But:** ZERO processing logs in regime service
4. Last regime signal is 26+ hours old (predates test by >1 day)

**Hypothesis A: Service Not Started/Consuming**
- Service may be running but consumer thread/loop not active
- Check: Is `run_consumer()` or equivalent actually running?
- Check: Consumer Group position (XINFO GROUPS)

**Hypothesis B: Symbol Filter Issue**
- Service may filter `symbol != BTCUSDT`, ignoring `TEST`
- Check: Candle consumption logic - does it filter by symbol?
- Note: Last regime signal was for BTCUSDT only

**Hypothesis C: Stale Consumer Position**
- Consumer may be blocked at old stream position, not reading new entries
- Check: XINFO GROUPS stream.candles_1m

---

## 7. Recommended Next Steps

### Immediate Triage (DO NOT FIX YET):
1. Check consumer group status:
   ```bash
   docker exec cdb_redis sh -c 'redis-cli -a $(cat /run/secrets/redis_password) XINFO GROUPS stream.candles_1m'
   ```

2. Check regime service startup logs:
   ```bash
   docker compose -p blue_stk -f infrastructure/compose/compose.blue.yml logs cdb_regime | grep -i "consumer\|start\|ready"
   ```

3. Verify service code: Does `cdb_regime` have active stream consumer?

4. Check symbol filter: Does regime only process BTCUSDT candles?

### Evidence Preservation:
- Current stream state captured ✅
- Logs captured ✅
- No fix attempted (as per test protocol) ✅

---

## 8. Test Verdict

**RESULT:** 🔴 **FAIL**

**DoD Check:**
- ❌ Regime wechselt genau einmal → Did not change at all
- ❌ Allocation emit't genau eine neue Decision → Did not emit
- ❌ Danach: System wieder idle → N/A (never processed)
- ✅ Kein Spam, keine Loops → Correct (no activity = no spam)

**Hard STOP Criterion Triggered:**
> "Kein Regime-Change nach 30s (trotz Extrem-Candle)"

**Conclusion:**
Control Layer is **NOT TRANSITION-SAFE**. The regime service is not consuming candles from the stream, therefore no state transitions can occur. This is a **critical blocker** for production deployment.

**Blocker Severity:** P0 - System cannot react to market changes

---

## Appendix: Test Parameters

**Test Script:** `D:/Dev/Workspaces/Prompts/CLAUDE CODE/20260203_141920.md`
**Execution:** Manual via Claude Code Agent
**Stack:** Blue Stack (`blue_stk`)
**Redis Container:** `cdb_redis`
**Services Monitored:** `cdb_regime`, `cdb_allocation`
**Test Duration:** ~2 minutes (30s wait + verification)
**Evidence Timestamp:** 2026-02-03 14:20:05 - 14:22:00 UTC
