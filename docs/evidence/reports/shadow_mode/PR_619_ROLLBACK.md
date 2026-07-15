# PR #619 Rollback Procedure

**PR:** https://github.com/jannekbuengener/Claire_de_Binare/pull/619
**Fix:** Hard Exposure Gate (service.py:642-689)
**Risk:** Low (stricter check, no behavior change for compliant orders)

---

## Rollback Trigger

Rollback ONLY if:
1. **False Positives:** Valid orders blocked incorrectly (check logs for projected vs actual)
2. **Performance Degradation:** Gate check causes measurable latency (unlikely, simple arithmetic)
3. **Unexpected Deadlock:** All orders blocked despite valid exposure state

**DO NOT rollback if:**
- Hard gate is working as designed (blocking over-limit orders)
- Auto-unwind still triggers (this is recovery, not the gate)

---

## Rollback Steps

**1. Revert commit:**
```bash
git checkout main
git pull origin main
git revert d0654eb  # Revert PR #619 commit
git push origin main
```

**2. Rebuild + Restart Risk Service:**
```bash
# Rebuild risk service with reverted code
docker compose build cdb_risk

# Restart risk service
docker compose restart cdb_risk

# Verify service is running
docker logs cdb_risk --tail 50
```

**3. Verify rollback:**
```bash
# Check service is processing signals
docker logs cdb_risk --since 2m | grep "Signal empfangen"

# Check exposure behavior (should revert to PR #617/#618 state)
docker logs cdb_risk --since 5m | grep "Exposure"
```

---

## Post-Rollback State

**After rollback:**
- Returns to PR #618 state (price fallback + reservation)
- Exposure check at `service.py:568` (BEFORE order creation)
- Race condition re-introduced (check cannot see new order)
- Auto-unwind remains active as recovery

**Expected behavior:**
- May see occasional "Max Exposure erreicht" events (1-2 per day)
- Auto-unwind will correct (reactive recovery)
- No hard blocks on valid orders

---

## Alternative: Adjust Limit

If rollback triggered by **overly strict enforcement**, consider:

**Temporary increase exposure limit:**
```bash
# Edit config (if test_balance used)
# Or adjust max_total_exposure_pct in services/risk/config.py

# Example: 3000 → 3050 USDT (+1.7% headroom)
# Rebuild + restart as above
```

**Note:** Limit adjustment should be temporary. Re-apply PR #619 after validation.

---

## Escalation

If rollback does NOT resolve issue:
1. Check for regression in PR #617/#618 (reservation logic)
2. Verify `test_balance` or `use_real_balance` config
3. Inspect Redis state: `docker exec cdb_redis sh -c 'redis-cli -a $(cat /run/secrets/redis_password) XREVRANGE stream.orders + - COUNT 10'`

---

**Rollback Approval:** User decision required (no automated rollback)
