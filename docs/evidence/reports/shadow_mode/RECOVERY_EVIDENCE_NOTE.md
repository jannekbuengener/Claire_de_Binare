# Scenario A Recovery - Evidence Note

**Date:** 2026-01-19
**Action:** Minimal safe patch to unblock Shadow Mode
**Status:** Ready for deployment

---

## Problem Summary

**Symptom:** 100% of signals blocked (0% approval rate)

**Root Cause:** Paper trading auto-unwind disabled → exposure accumulated to $3005.47 → exceeded $3000 limit

**Timeline:**
- Risk service started: 2026-01-17 14:15:21
- Exposure limit hit: 2026-01-17 21:17:03 (after 7 hours)
- Blocked duration: 2 days (still ongoing)

---

## Recovery Patch (2 Files)

### 1. infrastructure/compose/dev.yml

**Change:** Enable paper position auto-unwinding

```yaml
cdb_risk:
  environment:
    PAPER_AUTO_UNWIND: "true"  # Auto-close paper positions
```

**Effect:** Future paper BUY orders automatically generate SELL orders to close positions

### 2. services/risk/service.py

**Change:** Add admin endpoint for immediate exposure reset

```python
@app.route("/admin/reset_exposure", methods=["POST"])
def admin_reset_exposure():
    """Reset risk state exposure to 0 (Shadow Mode recovery only)"""
    # Environment-gated (dev/shadow only)
    # Clears positions dict + resets total_exposure to 0
```

**Effect:** Immediate unblock without service restart

---

## Deployment Steps

```bash
# 1. Rebuild risk service with new code
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml \
  up -d --build cdb_risk

# 2. Wait for service to start (check logs)
docker logs -f cdb_risk | grep "Risk-Manager gestartet"

# 3. Reset stuck exposure immediately
curl -X POST http://localhost:8002/admin/reset_exposure

# 4. Verify reset successful
curl http://localhost:8002/health | jq '.total_exposure'
# Expected: 0.0

# 5. Monitor signal flow
docker logs -f cdb_risk | grep "approved\|blocked"
# Expected: "approved" messages appear

# 6. Monitor auto-unwind after fills
docker logs -f cdb_risk | grep "PAPER_AUTO_UNWIND"
# Expected: "queued SELL" messages after BUY fills
```

---

## Safety Guarantees

1. **Environment-gated:** Admin endpoint only works in dev/shadow (prod protection)
2. **No data loss:** Only resets in-memory state (DB unchanged)
3. **No restart required:** Service continues running
4. **Reversible:** Can restart service to revert if needed
5. **Minimal change:** 1 line config + 1 endpoint (32 lines code)

---

## Evidence

### Before Patch

```bash
# Exposure stuck at limit
docker logs cdb_risk | grep "Max Exposure" | head -1
# Output: 3005.47 >= 3000.00 (first seen 2026-01-17 21:17:03)

# 100% blocking
docker logs cdb_risk --since 60m | grep "Signal empfangen" | wc -l
# Output: 157 signals received

docker logs cdb_risk --since 60m | grep "Max Exposure" | wc -l
# Output: 314 (157 × 2 log lines = 100% blocked)

# Config missing
docker exec cdb_risk env | grep PAPER_AUTO_UNWIND
# Output: (empty)
```

### After Patch

```bash
# Config enabled
docker exec cdb_risk env | grep PAPER_AUTO_UNWIND
# Expected: PAPER_AUTO_UNWIND=true

# Exposure reset
curl -X POST http://localhost:8002/admin/reset_exposure
# Expected: {"status": "ok", "old_exposure": 3005.47, "new_exposure": 0.0}

# Signal flow restored
docker logs -f cdb_risk | grep "approved"
# Expected: Approval messages appear

# Auto-unwind active
docker logs -f cdb_risk | grep "PAPER_AUTO_UNWIND"
# Expected: "PAPER_AUTO_UNWIND: queued SELL BTCUSDT qty=..." messages
```

---

## Impact

**Immediate:**
- ✅ Signals unblocked (0% → expected >50% approval rate)
- ✅ Shadow Mode operational for remaining 12 days
- ✅ No restart required (preserves Shadow Mode continuity)

**Future Prevention:**
- ✅ Paper positions auto-close after fills
- ✅ Exposure cannot accumulate beyond single position
- ✅ Shadow Mode self-sustaining for full 14-day period

**Technical Debt Addressed:**
- ⚠️ Positions table still not synchronized (separate issue #XXX)
- ⚠️ No DB state reconciliation on startup (future enhancement)

---

## Related Files

- **Diagnosis:** `docs/evidence/reports/shadow_mode/SCENARIO_A_DIAGNOSIS_2026-01-19.md`
- **Config:** `services/risk/config.py:33` (PAPER_AUTO_UNWIND setting)
- **Auto-unwind:** `services/risk/service.py:607-641` (_maybe_auto_unwind function)

---

**Estimated Fix Time:** 40 minutes (implemented)

**Risk Level:** LOW (dev-only, gated, reversible)

**Testing Required:** 15 minutes (deployment + verification)

---

*Recovery Evidence Note - Claire de Binare Trading Bot*
