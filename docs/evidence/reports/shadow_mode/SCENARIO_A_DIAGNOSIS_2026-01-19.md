# Scenario A Diagnosis: Risk Blockade (100% Blocking)

**Investigation Date:** 2026-01-19 15:00 UTC
**Status:** ROOT CAUSE IDENTIFIED
**Blocker:** Paper trading auto-unwind DISABLED

---

## Task 1: Block Reasons (Evidence)

### Log Analysis (Last 60 minutes)

**Command:**
```bash
docker logs cdb_risk --since 60m | grep -E "Signal empfangen|Max Exposure"
```

**Results:**
- **Total signals received:** 157
- **Total blocks:** 157 (100%)
- **Block reasons (by count):**

| Reason | Count | Details |
|--------|-------|---------|
| **Max Exposure Limit** | 157 | `Max Exposure erreicht: 3005.47 >= 3000.00` |
| Other reasons | 0 | None found |

**Summary:** 100% of signals blocked due to a single reason: **Max exposure limit exceeded**.

---

## Task 2: State Comparison (Evidence Table)

### Multi-System Exposure State

| System | Exposure (USD) | Position (BTC) | Timestamp | Notes |
|--------|----------------|----------------|-----------|-------|
| **Risk (In-Memory)** | **3005.47** | 0.06013 BUY | 2026-01-17 21:17:03 | Stuck since first breach |
| **DB (positions)** | 0.00 | 0.00000 | Never updated | ⚠️ NOT SYNCHRONIZED |
| **DB (orders)** | 3006.56 | 0.06013 BUY | 2026-01-17 21:17:02 | Matches risk calc ✓ |

### Evidence Commands

```bash
# Risk in-memory exposure
docker logs cdb_risk | grep "Max Exposure" | head -1
# Output: 3005.47 >= 3000.00

# DB positions (source-of-truth)
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c \
  "SELECT COUNT(*) as open_positions, SUM(size * entry_price) as total_exposure_usd \
   FROM positions WHERE closed_at IS NULL;"
# Output: 0 positions, NULL exposure

# DB orders (execution history)
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c \
  "SELECT SUM(filled_size) as total_btc, SUM(filled_size * avg_fill_price) as total_usd \
   FROM orders WHERE status = 'filled' AND side = 'buy' \
   AND created_at >= '2026-01-17 14:15:00';"
# Output: 0.06013317 BTC, $3006.56 USD
```

### State Drift Analysis

**Drift Detected:** ❌ NO
- Risk manager exposure (3005.47) **matches** orders table (3006.56) ✓
- Difference of $1.09 is rounding/timing variance (acceptable)
- Risk state is **ACCURATE** for what it processed

**Real Problem:** 🔴 Configuration Issue
- DB positions table is NOT synchronized (separate infrastructure issue)
- Paper trading positions accumulate **without auto-unwinding**
- No mechanism to reset/close simulated positions

---

## Root Cause Analysis

### Timeline

```
2026-01-17 14:15:21  Risk service started (exposure = 0)
2026-01-17 14:15:21  Config: PAPER_AUTO_UNWIND = false (default)
2026-01-17 14:15:xx  Bootstrap allocation: paper=0.02 (2%)
2026-01-17 14:15-21:17  60 BUY orders filled (~$3000 exposure)
2026-01-17 21:17:03  First "Max Exposure" warning (3005.47 >= 3000.00)
2026-01-17 21:17:03  *** ALL SUBSEQUENT SIGNALS BLOCKED ***
2026-01-19 15:00:00  Still blocked (3005.47 unchanged for 2 days)
```

### Configuration Analysis

**File:** `services/risk/config.py:33`
```python
paper_auto_unwind: bool = os.getenv("PAPER_AUTO_UNWIND", "false").lower() == "true"
```

**Current Value:** `false` (default, not set in environment)

**Function:** `services/risk/service.py:607-641`
```python
def _maybe_auto_unwind(self, result: OrderResult) -> None:
    if not self.config.paper_auto_unwind:
        return  # ← EXITS IMMEDIATELY
    # Auto-creates SELL orders for paper BUY fills
    # Prevents exposure accumulation in Shadow Mode
```

**Impact:**
- Shadow Mode (paper trading) accumulates BUY positions
- No automatic SELL orders to close positions
- Exposure grows until max_exposure limit hit
- All future signals blocked indefinitely

###Why This Matters

**Shadow Mode Purpose:** 14-day validation of signal quality WITHOUT real trades

**Current Behavior:**
1. ✅ Signals flow (real-time)
2. ✅ Orders created (paper only)
3. ✅ Mock execution fills orders
4. ❌ Positions accumulate (no unwinding)
5. ❌ Exposure limit hit after ~60 fills
6. ❌ System blocked (cannot process more signals)

**Result:** Shadow Mode becomes **self-poisoning** after ~2 hours of operation.

---

## Task 3: Recovery Plan

### Option Analysis

#### Option A: Enable Auto-Unwind (RECOMMENDED ✓)

**Action:** Set `PAPER_AUTO_UNWIND=true` in dev.yml

**Implementation:**
```yaml
# infrastructure/compose/dev.yml
services:
  cdb_risk:
    environment:
      PAPER_AUTO_UNWIND: "true"  # Enable paper position auto-close
```

**Trade-offs:**
- ✅ Minimal change (1 line)
- ✅ Safe (no data loss)
- ✅ Prevents future accumulation
- ⚠️ Requires container restart to apply
- ❌ Does NOT fix current stuck 3005.47 exposure

**Outcome:** Future paper positions auto-close, but current block remains.

---

#### Option B: Add Exposure Reset Endpoint (CLEAN SOLUTION)

**Action:** Implement `/admin/reset_exposure` API endpoint

**Implementation:**
```python
# services/risk/service.py (add new endpoint)
@app.route("/admin/reset_exposure", methods=["POST"])
def admin_reset_exposure():
    """Reset risk state exposure (admin only, Shadow Mode recovery)"""
    global risk_state
    risk_state.total_exposure = 0.0
    risk_state.positions.clear()
    risk_state.last_prices.clear()
    risk_state.open_positions = 0
    logger.warning("ADMIN: Exposure reset to 0 (Shadow Mode recovery)")
    return jsonify({"status": "ok", "total_exposure": 0.0})
```

**Usage:**
```bash
curl -X POST http://localhost:5002/admin/reset_exposure
```

**Trade-offs:**
- ✅ No restart required
- ✅ Immediate effect (unblocks signals)
- ✅ Clean state recovery
- ✅ Preserves Shadow Mode continuity
- ⚠️ Requires code change + PR
- ⚠️ Adds admin endpoint (security consideration)

**Outcome:** Exposure reset to 0, signals flow immediately after call.

---

#### Option C: Reconcile State from DB on Startup (ROBUST)

**Action:** Query positions table on risk service startup, rebuild exposure

**Implementation:**
```python
# services/risk/service.py (in RiskManager.__init__ or connect_redis)
def _bootstrap_exposure_from_db(self):
    """Rebuild risk state from DB positions (source-of-truth)"""
    # Query: SELECT symbol, size, entry_price FROM positions WHERE closed_at IS NULL
    # Rebuild risk_state.positions and risk_state.total_exposure
    pass
```

**Trade-offs:**
- ✅ Aligns with "DB is source-of-truth" principle
- ✅ Survives restarts (state from persistent storage)
- ✅ Correct by design (no manual interventions)
- ❌ Requires DB dependency in risk service
- ❌ More complex implementation
- ❌ Still requires restart to apply

**Outcome:** Risk service always starts with accurate state from DB.

---

### Recommended Minimal Action: **Option A + Option B Combined**

**Phase 1: Immediate Recovery (Today)**
1. Implement `/admin/reset_exposure` endpoint (Option B)
2. Deploy to dev environment
3. Call endpoint to reset stuck exposure: `curl -X POST http://localhost:5002/admin/reset_exposure`
4. Verify signals flow again

**Phase 2: Prevention (Today)**
1. Enable `PAPER_AUTO_UNWIND=true` in dev.yml (Option A)
2. Restart risk service to apply config
3. Monitor: paper positions should auto-close

**Phase 3: Robustness (Week 2)**
1. Implement DB state reconciliation (Option C)
2. Add to risk service startup sequence
3. Test restart recovery

---

## Deliverable: PR #XXX (Minimal Patch)

### Files Changed

**1. infrastructure/compose/dev.yml** (enable auto-unwind)
```yaml
services:
  cdb_risk:
    environment:
      PAPER_AUTO_UNWIND: "true"
```

**2. services/risk/service.py** (add reset endpoint)
```python
@app.route("/admin/reset_exposure", methods=["POST"])
def admin_reset_exposure():
    """Reset risk state exposure to 0 (Shadow Mode recovery only)"""
    if config.env not in ["development", "shadow"]:
        return jsonify({"error": "Only available in dev/shadow"}), 403

    global risk_state
    old_exposure = risk_state.total_exposure
    risk_state.total_exposure = 0.0
    risk_state.positions.clear()
    risk_state.last_prices.clear()
    risk_state.open_positions = 0

    logger.warning(
        "ADMIN: Exposure reset from %.2f to 0.0 (Shadow Mode recovery)",
        old_exposure
    )
    return jsonify({
        "status": "ok",
        "old_exposure": old_exposure,
        "new_exposure": 0.0,
        "message": "Risk state reset successful"
    })
```

### Testing Steps

```bash
# 1. Verify current stuck state
curl http://localhost:5002/health | jq '.total_exposure'
# Expected: 3005.47

# 2. Apply patch (git pull + docker-compose up -d)

# 3. Reset exposure
curl -X POST http://localhost:5002/admin/reset_exposure
# Expected: {"status": "ok", "old_exposure": 3005.47, "new_exposure": 0.0}

# 4. Verify reset
curl http://localhost:5002/health | jq '.total_exposure'
# Expected: 0.0

# 5. Wait for next signal (should be approved now)
docker logs -f cdb_risk | grep "approved\|blocked"
# Expected: "approved" messages

# 6. Monitor auto-unwind after fills
docker logs -f cdb_risk | grep "PAPER_AUTO_UNWIND"
# Expected: "PAPER_AUTO_UNWIND: queued SELL" messages
```

---

## Evidence Package

### Commands Run

```bash
# Block reason extraction
docker logs cdb_risk --since 60m | grep "Max Exposure" | wc -l
# Result: 314 warnings (157 signals × 2 log lines each)

# Risk in-memory state
docker logs cdb_risk | grep "3005" | head -1
# Result: 2026-01-17 21:17:03 "Max Exposure erreicht: 3005.47 >= 3000.00"

# DB positions state
docker exec cdb_postgres psql -U claire_user -d claire_de_binare \
  -c "SELECT COUNT(*), SUM(size * entry_price) FROM positions WHERE closed_at IS NULL;"
# Result: 0 positions, NULL exposure

# DB orders state
docker exec cdb_postgres psql -U claire_user -d claire_de_binare \
  -c "SELECT SUM(filled_size), SUM(filled_size * avg_fill_price) \
      FROM orders WHERE status = 'filled' AND side = 'buy' \
      AND created_at >= '2026-01-17 14:15:00';"
# Result: 0.06013317 BTC, $3006.56 USD

# Config check
docker exec cdb_risk env | grep PAPER_AUTO_UNWIND
# Result: (empty - not set, defaults to false)

# Redis order_results
docker exec cdb_redis sh -c 'redis-cli -a $(cat /run/secrets/redis_password) \
  XLEN stream.order_results'
# Result: 8835 order results in stream
```

### Log Excerpts

```log
# Risk service startup
2026-01-17 14:15:21,201 [INFO] risk_manager: 🚀 Risk-Manager gestartet
2026-01-17 14:15:21,233 [INFO] risk_manager: Bootstrap allocation: strategy_id=paper allocation_pct=0.0200

# First exposure breach
2026-01-17 21:17:03,474 [WARNING] risk_manager: Alert: [WARNING] RISK_LIMIT: Max Exposure erreicht: 3005.47 >= 3000.00
2026-01-17 21:17:03,474 [WARNING] risk_manager: ⚠️ Max Exposure erreicht: 3005.47 >= 3000.00

# Continuous blocking (sample from 2 days later)
2026-01-19 13:52:13,958 [WARNING] risk_manager: Alert: [WARNING] RISK_LIMIT: Max Exposure erreicht: 3005.47 >= 3000.00
2026-01-19 13:53:09,458 [WARNING] risk_manager: Alert: [WARNING] RISK_LIMIT: Max Exposure erreicht: 3005.47 >= 3000.00
2026-01-19 13:57:04,652 [WARNING] risk_manager: Alert: [WARNING] RISK_LIMIT: Max Exposure erreicht: 3005.47 >= 3000.00
```

---

## Next Steps

1. ✅ **COMPLETED:** Diagnosis with evidence
2. 🔄 **CURRENT:** Implement minimal patch (Options A + B)
3. ⏭️ **NEXT:** Deploy + test recovery
4. ⏭️ **FOLLOW-UP:** Implement robust DB reconciliation (Option C)

---

**Impact:** Unblocks Shadow Mode, enables continuous signal validation for remaining 12 days.

**Risk:** LOW - Changes are dev-only, admin endpoint gated by environment check.

**Estimated Fix Time:** 30 minutes (code) + 10 minutes (test) = 40 minutes total.

---

*Scenario A Diagnosis Report - Claire de Binare Trading Bot*
*Generated: 2026-01-19 15:05 UTC*
