# Positions Table Reconciliation - 2026-01-19

**Date:** 2026-01-19
**Status:** ✅ READY FOR EXECUTION
**Purpose:** One-time migration to reconstruct positions table from historical orders

---

## Problem Statement

**Current State (2026-01-19 16:00 UTC):**

```sql
-- Positions table (source-of-truth): EMPTY
SELECT * FROM positions WHERE closed_at IS NULL;
-- Result: 0 rows

-- Orders table (history): NET OPEN POSITION
SELECT
    side,
    COUNT(*) as count,
    SUM(filled_size) as total_size,
    SUM(filled_size * avg_fill_price) as total_usd
FROM orders
WHERE status = 'filled'
  AND created_at >= '2026-01-17 14:15:00'
GROUP BY side;

-- Result:
-- side | count | total_size |   total_usd
-- -----|-------|------------|-------------
-- buy  |   287 | 0.06013317 | 3006.56 USD
```

**State Mismatch:**
- Positions table: 0.00000000 BTC (EMPTY)
- Orders table: 0.06013317 BTC (NET LONG BTCUSDT)
- **Gap:** Position exists in reality but not in source-of-truth

**Impact:**
- Risk manager would bootstrap with exposure = 0.0 USD
- Actual exposure ≈ 3006.56 USD
- State drift would persist (incorrect risk decisions)

---

## Solution: One-Time Reconciliation

### Script: `infrastructure/scripts/reconcile_positions.py`

**Purpose:** Reconstruct positions table from historical orders

**Algorithm:**
1. Query all filled orders since Shadow Mode start (2026-01-17 14:15:00)
2. Calculate net position per symbol:
   - `net_qty = SUM(BUY fills) - SUM(SELL fills)`
3. Compute weighted average entry price:
   - `weighted_avg = SUM(qty × price) / SUM(qty)`
4. Insert positions table rows for net non-zero positions
5. Generate reconciliation report

**Safety Features:**
- ✅ Idempotent: Can be run multiple times (skips existing positions)
- ✅ Read-only on orders table
- ✅ Writes only to positions table
- ✅ No manual trades generated
- ✅ Detailed logging and reconciliation report

---

## Expected Reconciliation Output

### Before Reconciliation

```sql
-- Positions table
SELECT symbol, side, size, entry_price FROM positions WHERE closed_at IS NULL;
-- Result: 0 rows (EMPTY)
```

### After Reconciliation

```sql
-- Positions table (reconstructed from orders)
SELECT symbol, side, size, entry_price, opened_at, updated_at
FROM positions WHERE closed_at IS NULL;

-- Expected Result:
-- symbol   | side | size        | entry_price | opened_at           | updated_at
-- ---------|------|-------------|-------------|---------------------|---------------------
-- BTCUSDT  | long | 0.06013317  | ~50004.18   | 2026-01-17 14:15:xx | 2026-01-17 21:17:02

-- Calculations:
-- net_qty = 0.06013317 BTC (287 BUY fills - 0 SELL fills)
-- weighted_avg_entry = 3006.56 USD / 0.06013317 BTC ≈ $50,004.18
-- total_exposure = 0.06013317 × 50004.18 ≈ $3,006.56 USD
```

### Reconciliation Report

```
================================================================================
POSITIONS RECONCILIATION REPORT
================================================================================
Timestamp: 2026-01-19T16:30:00.000000
Shadow Mode Start: 2026-01-17 14:15:00

Summary:
  Total Positions: 1
  Total Exposure: $3,006.56 USD

Positions:
  BTCUSDT: LONG 0.06013317 @ $50,004.18 (exposure: $3,006.56, 287 BUY / 0 SELL)
================================================================================
```

---

## Deployment Process

### Step 1: Run Reconciliation Script

```bash
# Set PostgreSQL password
export POSTGRES_PASSWORD=$(cat /run/secrets/postgres_password)

# Run reconciliation
docker compose -f infrastructure/compose/base.yml \
  -f infrastructure/compose/dev.yml \
  exec cdb_risk python infrastructure/scripts/reconcile_positions.py
```

**Expected Output:**
```
2026-01-19 16:30:00 [INFO] 🚀 Starting positions reconciliation...
2026-01-19 16:30:00 [INFO] ✅ Connected to PostgreSQL at cdb_postgres:5432/claire_de_binare
2026-01-19 16:30:00 [INFO] 📊 Found 287 filled orders since 2026-01-17 14:15:00
2026-01-19 16:30:00 [INFO] 📊 Calculating net positions from order history...
2026-01-19 16:30:00 [INFO]   BTCUSDT: LONG 0.06013317 @ 50004.18 (287 BUY, 0 SELL)
2026-01-19 16:30:00 [INFO] 📝 Writing 1 positions to database...
2026-01-19 16:30:00 [INFO] ✅ Position written: ID=1, BTCUSDT LONG 0.06013317 @ 50004.18
2026-01-19 16:30:00 [INFO]
================================================================================
POSITIONS RECONCILIATION REPORT
================================================================================
Timestamp: 2026-01-19T16:30:00.000000
Shadow Mode Start: 2026-01-17 14:15:00

Summary:
  Total Positions: 1
  Total Exposure: $3,006.56 USD

Positions:
  BTCUSDT: LONG 0.06013317 @ $50,004.18 (exposure: $3,006.56, 287 BUY / 0 SELL)
================================================================================
2026-01-19 16:30:00 [INFO] ✅ Reconciliation complete: 1 positions written
```

### Step 2: Verify Positions Table

```bash
# Query positions table
docker compose exec cdb_postgres psql -U claire_user -d claire_de_binare -c \
  "SELECT symbol, side, size, entry_price, opened_at, updated_at FROM positions WHERE closed_at IS NULL;"
```

**Expected Result:**
```
 symbol   | side | size       | entry_price | opened_at                     | updated_at
----------|------|------------|-------------|-------------------------------|-------------------------------
 BTCUSDT  | long | 0.06013317 | 50004.18000 | 2026-01-17 14:15:xx.xxxxxx+00 | 2026-01-17 21:17:02.516486+00
(1 row)
```

### Step 3: Deploy Risk Service with Bootstrap

```bash
# Rebuild risk service
docker compose -f infrastructure/compose/base.yml \
  -f infrastructure/compose/dev.yml \
  up -d --build cdb_risk
```

**Expected Logs:**
```
2026-01-19 16:35:00 [INFO] Redis verbunden: cdb_redis:6379
2026-01-19 16:35:00 [INFO] Positions table empty - checking for state mismatch...
2026-01-19 16:35:00 [INFO] ✅ Risk state bootstrap complete: 1 positions, total exposure: 3006.56 USD
2026-01-19 16:35:00 [INFO]   Position loaded: BTCUSDT LONG 0.06013317 @ 50004.18 (exposure: 3006.56 USD)
2026-01-19 16:35:00 [INFO] 🚀 Risk-Manager gestartet
```

### Step 4: Verify Risk State

```bash
# Check risk health endpoint
curl -s http://localhost:8002/health | jq '{total_exposure, open_positions}'
```

**Expected Result:**
```json
{
  "total_exposure": 3006.56,
  "open_positions": 1
}
```

---

## Safety Gate Behavior

### Scenario A: Reconciliation NOT Run (Current State)

If you try to start risk service WITHOUT running reconciliation first:

```bash
docker compose up -d cdb_risk
```

**Risk service will FAIL with:**
```
================================================================================
❌ CRITICAL: STATE MISMATCH DETECTED
================================================================================
Positions table: EMPTY (0 open positions)
Orders table:    NET 0.06013317 BTC
  BUY fills:     0.06013317 BTC
  SELL fills:    0.00000000 BTC

Risk manager CANNOT start with incorrect state.

ACTION REQUIRED:
Run positions reconciliation script to reconstruct positions table:

  python infrastructure/scripts/reconcile_positions.py

Or set POSTGRES_PASSWORD environment variable and run:

  docker compose exec cdb_risk python infrastructure/scripts/reconcile_positions.py

This will rebuild positions table from order history.
After reconciliation completes, restart risk service.
================================================================================

RuntimeError: State mismatch: positions table empty but orders show open position
```

**Result:** Service exits with code 1 (FAIL-CLOSED)

### Scenario B: Reconciliation Already Run

If positions table already has data:

```bash
# Run reconciliation again (idempotent)
python infrastructure/scripts/reconcile_positions.py
```

**Expected Output:**
```
2026-01-19 16:40:00 [INFO] 🚀 Starting positions reconciliation...
2026-01-19 16:40:00 [INFO] ✅ Connected to PostgreSQL
2026-01-19 16:40:00 [INFO] ⚠️ Found 1 existing open positions:
2026-01-19 16:40:00 [INFO]   BTCUSDT: LONG 0.06013317
2026-01-19 16:40:00 [INFO] ⚠️ Reconciliation will skip existing positions (idempotent)
2026-01-19 16:40:00 [INFO] 📊 Found 287 filled orders since 2026-01-17 14:15:00
2026-01-19 16:40:00 [INFO] 📊 Calculating net positions from order history...
2026-01-19 16:40:00 [INFO]   BTCUSDT: LONG 0.06013317 @ 50004.18 (287 BUY, 0 SELL)
2026-01-19 16:40:00 [INFO] 📝 Writing 1 positions to database...
2026-01-19 16:40:00 [INFO] ⚠️ Position for BTCUSDT already exists (id=1) - skipping
2026-01-19 16:40:00 [INFO] ✅ Reconciliation complete: 0 positions written
```

**Result:** No duplicates created, existing data preserved

---

## Post-Reconciliation State

### System State After Migration

```
┌─────────────────────────────────────────┐
│ Positions Table (Source-of-Truth)      │
│ ======================================= │
│ BTCUSDT: LONG 0.06013317 @ $50,004.18  │
│ Exposure: $3,006.56 USD                 │
└────────────────┬────────────────────────┘
                 │
                 │ Bootstrap reads on startup
                 ▼
┌─────────────────────────────────────────┐
│ Risk Manager In-Memory State           │
│ ======================================= │
│ risk_state.positions = {               │
│   "BTCUSDT": 0.06013317                │
│ }                                       │
│ risk_state.total_exposure = 3006.56    │
└─────────────────────────────────────────┘
```

### Signal Processing Behavior

**Current Behavior (BEFORE reconciliation):**
- All signals blocked: Max Exposure 3005.47 >= 3000.00
- Approval rate: 0%

**Expected Behavior (AFTER reconciliation):**
- **STILL BLOCKED** until position closes or limit increases
- Risk manager now has CORRECT state (3006.56 USD)
- But still above max_exposure limit (3000 USD)
- **PAPER_AUTO_UNWIND will generate SELL** on next signal approval
- Once SELL fills → position closes → exposure drops to 0
- Then signals can flow again

**Note:** Reconciliation fixes STATE DRIFT, not the blocking itself. The blocking is CORRECT behavior given the actual exposure.

---

## Verification Checklist

After reconciliation, verify all systems show consistent state:

### 1. Positions Table
```sql
SELECT symbol, side, size, entry_price
FROM positions WHERE closed_at IS NULL;
```
✅ Expected: 1 row (BTCUSDT LONG 0.06013317)

### 2. Risk Manager State
```bash
curl -s http://localhost:8002/health | jq '.total_exposure, .open_positions'
```
✅ Expected: exposure ≈ 3006.56, positions = 1

### 3. Orders History
```sql
SELECT
    SUM(CASE WHEN side='buy' THEN filled_size ELSE 0 END) as buy,
    SUM(CASE WHEN side='sell' THEN filled_size ELSE 0 END) as sell
FROM orders WHERE status='filled' AND created_at >= '2026-01-17 14:15:00';
```
✅ Expected: buy = 0.06013317, sell = 0.00000000

### 4. State Consistency
```
Positions Table Exposure = Risk Manager Exposure = Orders Net Position × Current Price
3006.56 USD ≈ 3006.56 USD ≈ 0.06013317 BTC × ~50,004 USD/BTC
```
✅ All systems agree on position state

---

## Rollback Plan

If reconciliation causes issues:

### Option 1: Clear Positions Table
```sql
-- Delete reconciled positions
DELETE FROM positions WHERE id >= 1;
```
**Result:** Returns to empty state (but risk service will FAIL safety gate)

### Option 2: Revert Code Changes
```bash
git revert aa1691b  # Revert positions writer + reconciliation commit
docker compose up -d --build cdb_risk cdb_db_writer
```
**Result:** Returns to pre-fix behavior (no positions writer, no bootstrap)

### Option 3: Manual Position Close
```sql
-- Mark position as closed
UPDATE positions
SET closed_at = NOW(), size = 0
WHERE symbol = 'BTCUSDT' AND closed_at IS NULL;
```
**Result:** Position removed from risk calculations

---

## Related Files

1. **Migration Script:** `infrastructure/scripts/reconcile_positions.py`
2. **Risk Bootstrap:** `services/risk/service.py:141-273` (bootstrap_state_from_db)
3. **Fix Documentation:** `reports/shadow_mode/SCENARIO_A_FIX_2026-01-19.md`
4. **Original Diagnosis:** `reports/shadow_mode/SCENARIO_A_DIAGNOSIS_2026-01-19.md`

---

## Timeline

| Time | Event |
|------|-------|
| 2026-01-17 14:15:00 | Shadow Mode starts, risk service starts with empty state |
| 2026-01-17 14:15:xx - 21:17:02 | 287 BUY orders fill, positions accumulate |
| 2026-01-17 21:17:03 | Exposure limit breached (3005.47 >= 3000.00) |
| 2026-01-19 16:00:00 | State mismatch identified (positions empty, orders show net) |
| 2026-01-19 16:30:00 | **Reconciliation script execution** |
| 2026-01-19 16:35:00 | Risk service restart with correct state |

---

**Status:** ✅ READY FOR DEPLOYMENT
**Risk Level:** LOW (read-only migration, idempotent, fail-safe)
**Execution Time:** < 1 minute

---

*Positions Reconciliation Evidence - Claire de Binare Trading Bot*
*Generated: 2026-01-19 17:00 UTC*
