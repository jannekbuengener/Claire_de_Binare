# Alerting Digest Fix - Grafana UI Configuration

**Date:** 2026-01-17
**Issue:** Alert E-Mail Spam + DatasourceError
**Solution:** UI-only changes (no code deployment)
**Impact:** CRITICAL alerts remain immediate, non-CRITICAL grouped to 24h digest

---

## Problem Statement

### Current Issues
1. **DatasourceError Spam:** Alert rules `cdb_error_rate_high` + `cdb_circuit_breaker_active` have broken expressions causing every-minute error logs
2. **E-Mail Spam:** All alerts (CRITICAL + INFO) send individual emails every 5 minutes
3. **No Digest Logic:** Notification Policy lacks grouping interval for non-critical alerts

### Root Causes
- **DatasourceError:** Multi-query alert expressions reference non-existent Query A
- **Spam:** Default `group_interval=5m` sends every evaluation as separate email
- **Log Evidence:**
  ```
  logger=ngalert.scheduler rule_uid=cdb_error_rate_high
    error="failed to parse expression 'C': invalid math command type: expr: non existent function A"
  ```

---

## Solution Overview

### Phase 1: Fix DatasourceError (15 minutes)
Fix broken alert rule expressions via Grafana UI

### Phase 2: Implement Daily Digest (10 minutes)
Configure notification policy for 24h grouping of non-critical alerts

### Phase 3: Verification (5 minutes)
Test critical vs non-critical routing

**Total Time:** ~30 minutes
**Risk Level:** LOW (UI config only, fully reversible)

---

## Phase 1: Fix DatasourceError

### Step 1.1: Access Alert Rules
1. Navigate to Grafana: `http://localhost:3000`
2. Login: admin / (password from secret)
3. Left sidebar → **Alerting** (bell icon) → **Alert rules**

### Step 1.2: Fix `cdb_error_rate_high`

**Current State:** Expression C references missing Query A

**Fix Steps:**
1. Search for alert: `cdb_error_rate_high`
2. Click **Edit** button
3. In Query section, you'll see:
   - Expression A: (missing or broken)
   - Expression C: Math/Reduce operation referencing A

**Option A - Replace with Direct PromQL (RECOMMENDED):**
1. Delete all existing queries/expressions
2. Add new Query:
   - **Data source:** Prometheus
   - **Query type:** Code (PromQL)
   - **Expression:**
     ```promql
     (rate(execution_orders_rejected_total[5m]) / rate(execution_orders_received_total[5m])) * 100 > 5
     ```
3. Set this query as **Alert condition**
4. Keep existing settings:
   - **Evaluation:** 5 minutes
   - **Pending period:** 0s
   - **Severity:** warning
5. Click **Save and exit**

**Option B - Rebuild Multi-Query (if original intent known):**
1. Query A: `rate(execution_orders_rejected_total[5m])`
2. Query B: `rate(execution_orders_received_total[5m])`
3. Expression C: Math `$A / $B * 100 > 5`
4. Set C as alert condition
5. Save

### Step 1.3: Fix `cdb_circuit_breaker_active`

**Repeat same process:**
1. Search: `cdb_circuit_breaker_active`
2. Edit → Delete broken queries
3. Add new Query:
   ```promql
   circuit_breaker_active == 1
   ```
4. Set as alert condition
5. Keep:
   - **Evaluation:** immediate (0s)
   - **Severity:** critical
6. Save and exit

### Step 1.4: Verify Fix

**Check Grafana Logs:**
```bash
# Wait 2 minutes after save, then check:
docker logs cdb_grafana 2>&1 | grep -i "failed to parse expression" | tail -20

# Expected: NO new errors
# Old errors will still show in history, but timestamp should stop updating
```

**Success Criteria:**
- ✅ No new "failed to parse expression" errors after save time
- ✅ Alert rules show "Normal" or "Pending" state (not "Error")
- ✅ Alert evaluation happens without errors in logs

---

## Phase 2: Daily Digest Configuration

### Step 2.1: Review Current Notification Policy

1. Grafana → **Alerting** → **Notification policies**
2. You should see **Root policy** (default):
   - **Receiver:** email-main
   - **Group by:** grafana_folder, alertname
   - **Group interval:** 5m (or default)

**Problem:** This sends every evaluation cycle as separate email

### Step 2.2: Modify Root Policy (Default Route)

**Strategy:**
- Root policy handles **non-critical** alerts with 24h digest
- Child route handles **critical** alerts with immediate delivery

**Root Policy Changes:**
1. Click **Edit** on Root policy (gear icon)
2. Update timing settings:
   - **Group wait:** `30s` (unchanged)
   - **Group interval:** `24h` ← **KEY CHANGE**
   - **Repeat interval:** `24h` ← **KEY CHANGE**
3. Keep:
   - **Receiver:** email-main
   - **Group by:** grafana_folder, alertname
4. Click **Update**

### Step 2.3: Add Critical Alert Override Route

**Create Child Route:**
1. On Root policy, click **New nested policy**
2. Configure:
   - **Matching labels:**
     - Label: `severity`
     - Operator: `=`
     - Value: `critical`
   - **Contact point:** email-main (or create new `email-critical`)
   - **Override grouping:** Yes
   - **Group by:** grafana_folder, alertname
   - **Group wait:** `10s` ← immediate
   - **Group interval:** `1m` ← frequent checks
   - **Repeat interval:** `1h` ← re-send if not resolved
   - **Continue matching siblings:** **NO** ← stops propagation to root
3. Click **Save policy**

**Policy Tree Should Look Like:**
```
Root Policy (default)
├─ Receiver: email-main
├─ Group interval: 24h
├─ Repeat: 24h
│
└─ Child: severity=critical
   ├─ Receiver: email-main
   ├─ Group interval: 1m
   ├─ Repeat: 1h
   └─ Continue: NO
```

### Step 2.4: Alternative - Separate Contact Points (Optional)

**If you want distinct "Critical" vs "Digest" receivers:**

1. **Create new Contact Point:**
   - Alerting → **Contact points** → **New contact point**
   - Name: `email-critical`
   - Type: Email
   - Addresses: (same as email-main)
   - Save

2. **Update Child Route:**
   - Use `email-critical` instead of `email-main`
   - Benefit: Clear separation in logs/UI

---

## Phase 3: Verification & Testing

### Test 3.1: Check DatasourceError Stopped

```bash
# Monitor logs for 5 minutes:
docker logs -f cdb_grafana 2>&1 | grep -i "error"

# Expected: No recurring "failed to parse expression" errors
# Occasional errors are OK (other unrelated issues)
```

### Test 3.2: Verify Notification Policy Active

1. Grafana → Alerting → Notification policies
2. Verify policy tree shows:
   - Root: 24h intervals
   - Child: severity=critical with 1m intervals

### Test 3.3: Simulate Critical Alert (Optional)

**Trigger Test Critical Alert:**
1. Temporarily edit `cdb_circuit_breaker_active` alert
2. Change condition to always-fire:
   ```promql
   vector(1) == 1  # Always true
   ```
3. Wait 1 minute
4. Check email inbox → Should receive IMMEDIATE email
5. Revert condition to original:
   ```promql
   circuit_breaker_active == 1
   ```

### Test 3.4: Simulate Non-Critical Alert (Optional)

**Trigger Test Warning Alert:**
1. Edit `cdb_error_rate_high` alert
2. Change condition to always-fire:
   ```promql
   vector(1) > 0
   ```
3. Wait 5 minutes
4. Check email → Should NOT receive immediate email
5. Wait 24h → Should receive SINGLE digest email with grouped alerts
6. Revert condition after test

---

## Acceptance Criteria

### Must-Have (BLOCKING)
- ✅ DatasourceError logs stopped (no new "failed to parse" after fix)
- ✅ CRITICAL alerts (severity=critical) send email within 1 minute
- ✅ NON-CRITICAL alerts (severity=warning/info) do NOT send individual emails
- ✅ Within 24h window, max 1 digest email for non-critical alerts

### Should-Have (IMPORTANT)
- ✅ Alert rules show "Normal" state in UI (not "Error")
- ✅ Grafana logs clean (no recurring errors every minute)
- ✅ Email subject distinguishes Critical vs Digest emails

### Nice-to-Have
- ✅ Separate contact points for critical vs digest
- ✅ Notification policy visible in UI policy tree
- ✅ Test alerts sent successfully

---

## Rollback Plan

### If Digest Breaks Critical Alerts:

**Immediate Rollback:**
1. Grafana → Notification policies
2. Edit Root policy:
   - Group interval: `5m` (restore original)
   - Repeat interval: `4h` (restore original)
3. Delete child route (severity=critical)
4. Save

**Result:** Reverts to original behavior (all alerts send immediately)

### If Alert Rules Broken After Fix:

**Restore from UI:**
1. Alerting → Alert rules → Find broken rule
2. Edit → Revert to previous query
3. Or delete + recreate from original config

**No git history needed** - all changes in Grafana database only

---

## Daily Orders Summary (Future Work)

**NOT INCLUDED in UI-only fix** - requires new service deployment

### Recommendation for Phase 4 (Optional):
- Create `services/reports/` with Python cron job
- Query DB: `SELECT * FROM orders WHERE created_at >= NOW() - INTERVAL '24h'`
- Send daily summary email via same SMTP credentials
- Schedule: 08:00 UTC daily

**Estimated effort:** 2-3 hours (Dockerfile + Python + compose integration)
**Priority:** NICE-TO-HAVE (current alerts cover operational issues)

---

## Troubleshooting

### Issue: Digest emails not arriving after 24h

**Check:**
```bash
# Verify alerts are firing:
docker logs cdb_grafana 2>&1 | grep "Sending alerts to local notifier"

# Check notification policy active:
curl -s http://localhost:3000/api/v1/provisioning/policies \
  -u "admin:PASSWORD" | jq
```

**Common causes:**
- No alerts fired in 24h window (check alert rule conditions)
- Group interval not saved (re-edit policy)
- SMTP credentials expired (check secrets)

### Issue: Critical alerts delayed

**Check child route:**
1. Notification policies → Verify child route exists
2. Ensure "Continue matching" = NO
3. Check group_interval = 1m (not 24h)

**Test:**
```bash
# Trigger test alert:
curl -X POST http://localhost:3000/api/v1/provisioning/alert-rules \
  -u "admin:PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{"condition": "vector(1)==1", "severity": "critical", ...}'
```

### Issue: DatasourceError returns after fix

**Root cause:** Alert rule not saved correctly

**Fix:**
1. Re-edit alert rule
2. Ensure "Save and exit" clicked (not just "Back")
3. Check alert rule version incremented (visible in UI)
4. Restart Grafana if persists:
   ```bash
   docker restart cdb_grafana
   ```

---

## References

- **Alert Rules:** `cdb_error_rate_high`, `cdb_circuit_breaker_active`, `cdb_orders_rejected`
- **Contact Point:** `email-main` (UID: dfabzv9fdgmpse)
- **SMTP Config:** `infrastructure/compose/base.yml:82-88`
- **Secrets Path:** `~/Documents/.secrets/.cdb/SMTP_*`
- **Evidence Docs:** `reports/shadow_mode/EMAIL_ALERTING_STATUS.md`

---

**Status:** Ready for execution
**Next Steps:**
1. Execute Phase 1 (fix DatasourceError) - 15 min
2. Execute Phase 2 (configure digest) - 10 min
3. Monitor for 24h - verify digest behavior
4. (Optional) Implement Orders Summary service in future sprint

**Estimated Alert Spam Reduction:** 95%+ (only CRITICAL send immediately)
