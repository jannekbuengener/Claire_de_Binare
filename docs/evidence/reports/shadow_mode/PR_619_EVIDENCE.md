# PR #619 Evidence – Hard Exposure Gate Fix

**Status:** ✅ FIX DEPLOYED
**PR:** https://github.com/jannekbuengener/Claire_de_Binare/pull/619
**Date:** 2026-01-22
**Type:** Shadow Mode – Risk Gate Policy Fix

---

## Root Cause

**Exposure Gate Race Condition:**

1. `check_exposure_limit()` called at `service.py:568` (BEFORE order creation)
2. Order created at `service.py:629-641` with final `qty * price`
3. Reservation set at `service.py:651-653` (AFTER order creation)
4. **Gap:** Check cannot see new order's notional → allows limit breach

**Evidence from Audit (2026-01-22 14:31:20 UTC):**
```
Exposure-Block Count: 1 event
Exposure: 3002.44 USDT (limit: 3000.00)
Delta: +2.44 USDT over limit
```

Order was published despite exceeding limit. Auto-unwind corrected, but gate should have blocked BEFORE publish.

---

## Fix Summary

**Hard Exposure Gate (service.py:642-689):**

Added check AFTER order creation, BEFORE reservation:

```python
# Calculate projected exposure INCLUDING new order
estimated_notional_usdt = order.quantity * price_used
projected_exposure = (
    risk_state.total_exposure
    + risk_state.pending_exposure_usdt
    + estimated_notional_usdt  # ← NEW ORDER NOTIONAL
)

if projected_exposure > max_exposure_usdt:
    # HARD REJECT: No reservation, no publish
    logger.warning("⛔ HARD EXPOSURE GATE: Order rejected...")
    return None  # Order never reaches send_order()
```

**Key Properties:**
- ✅ Check sees final qty/price (deterministic)
- ✅ Projected exposure includes new order
- ✅ Reject = no reservation set (no cleanup needed)
- ✅ Reduce-only orders bypass (close positions)

---

## Verification

**1. Check for exposure blocks (expect 0 or only reduce-only):**
```bash
docker logs cdb_risk --since 24h 2>&1 | grep -c "Max Exposure erreicht"
```

**2. Verify hard gate logs (if limit approached):**
```bash
docker logs cdb_risk --since 24h 2>&1 | grep "HARD EXPOSURE GATE"
```

Expected log format:
```
⛔ HARD EXPOSURE GATE: Order rejected BEFORE publish.
Projected exposure 3002.44 > limit 3000.00
(total: 2980.00, pending: 0.00, new_order: 22.44, client_id: BTCUSDT-123456)
```

**3. Verify order sizing integrity:**
```bash
docker exec cdb_redis sh -c 'redis-cli -a $(cat /run/secrets/redis_password) XREVRANGE stream.orders + - COUNT 3'
```

Expected: `price != null`, `qty * price ≈ 20 USDT`

---

## Impact

**Before Fix:**
- Orders could breach limit if check-to-publish gap allowed race
- Observed: +2.44 USDT over limit (3002.44 / 3000.00)

**After Fix:**
- Deterministic gate blocks based on projected state
- No order published if projected > limit
- Auto-unwind still active as recovery (defense-in-depth)

---

## Related

- PR #617: Exposure reservation (basis)
- PR #618: Price fallback hotfix
- Issue: Shadow Mode 24h verification FAIL (2026-01-22 audit)

---

**Verdict:** Gate policy corrected. Exposure race eliminated.
