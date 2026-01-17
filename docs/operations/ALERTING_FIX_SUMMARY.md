# Alert E-Mail Spam Fix - Executive Summary

**Date:** 2026-01-17
**Analyst:** Claude Code (Session Lead)
**Mode:** Analysis Only (UI Changes, No Code Deployment)

---

## TL;DR (6 Lines)

1. **DatasourceError GEFUNDEN:** Alert Rules `cdb_error_rate_high` + `cdb_circuit_breaker_active` haben kaputte Expressions (C referenziert nicht-existierende Query A) → **FIX: Grafana UI Alert Rules neu anlegen**
2. **Aktueller Spam-Grund:** Alle 3 Alerts gehen sofort an `email-main` Contact Point (kein Grouping, keine Delays außer 5min Evaluation) → **LÖSUNG: Notification Policy mit group_interval=24h für non-critical**
3. **CRITICAL separierbar:** Via severity/label-basiertes Routing → critical bleibt sofort, rest 24h digest
4. **Orders Summary:** DB-Tabellen `orders`/`trades` vorhanden → **Deferred to future sprint** (nice-to-have)
5. **Secrets-Konformität:** Alle SMTP-Secrets bereits als `*__FILE` korrekt implementiert (keine Änderungen nötig)
6. **Zero-Risk Approach:** Alle Änderungen in Grafana UI (kein Git-Diff, kein Deployment, 100% reversibel)

---

## Problem Analysis

### Issue 1: DatasourceError Every Minute
**Symptom:**
```
logger=ngalert.scheduler rule_uid=cdb_error_rate_high
  error="failed to parse expression 'C': invalid math command type: expr: non existent function A"
```

**Root Cause:**
- Alert rules `cdb_error_rate_high` and `cdb_circuit_breaker_active` have multi-query expressions (A→B→C)
- Query A is missing or corrupted
- Expression C tries to reference non-existent A
- Every evaluation (1-5min) logs ERROR and triggers DatasourceError notification

**Impact:**
- Log spam (50+ errors/hour)
- Potential DatasourceError email alerts (if configured)
- Alert rules stuck in ERROR state (not evaluating correctly)

**Evidence:**
- `docker logs cdb_grafana | grep "failed to parse"` → 50+ identical errors
- Affected UIDs: `cdb_error_rate_high`, `cdb_circuit_breaker_active`

---

### Issue 2: Alert E-Mail Spam
**Symptom:**
- Every alert evaluation sends separate email
- No digest/grouping for non-critical alerts
- Inbox flooded with individual notifications

**Root Cause:**
- Notification Policy defaults:
  - `group_interval: 5m` → every evaluation cycle sends email
  - No severity-based routing → all alerts treated equally
  - `repeat_interval: 4h` → re-sends frequently

**Impact:**
- 10-20+ emails per hour (depending on alert frequency)
- Alert fatigue → important alerts missed
- SMTP rate limiting risk (Gmail: 500/day limit)

**Evidence:**
- `reports/shadow_mode/EMAIL_ALERTING_STATUS.md` shows 3 active rules
- `cdb_orders_rejected` (severity: info) fires every 5min when orders rejected
- `cdb_error_rate_high` (severity: warning) fires when >5% rejection rate

---

## Solution Design

### Phase 1: Fix DatasourceError (15 min)

**Action:** Repair broken alert rule expressions in Grafana UI

**Method:**
1. Navigate to Grafana → Alerting → Alert rules
2. Edit `cdb_error_rate_high`:
   - Delete broken multi-query setup
   - Replace with single PromQL:
     ```promql
     (rate(execution_orders_rejected_total[5m]) / rate(execution_orders_received_total[5m])) * 100 > 5
     ```
3. Edit `cdb_circuit_breaker_active`:
   - Replace with single PromQL:
     ```promql
     circuit_breaker_active == 1
     ```
4. Save and verify logs stop showing errors

**Success Criteria:**
- ✅ No new "failed to parse expression" errors in logs
- ✅ Alert rules show "Normal" state (not "Error")
- ✅ Alert evaluation works correctly

---

### Phase 2: Daily Digest Configuration (10 min)

**Action:** Configure notification policy for 24h grouping

**Method:**
1. Grafana → Alerting → Notification policies
2. Modify **Root Policy**:
   - Group interval: **24h** (was 5m)
   - Repeat interval: **24h** (was 4h)
3. Add **Child Route** for CRITICAL:
   - Matcher: `severity = critical`
   - Group interval: **1m** (immediate)
   - Repeat interval: **1h**
   - Continue: **NO** (stop propagation)

**Result:**
- CRITICAL alerts → email within 1 minute
- WARNING/INFO alerts → 1 digest email per 24h (all grouped)

**Success Criteria:**
- ✅ CRITICAL alert sends email < 1 minute
- ✅ Non-critical alerts do NOT send individual emails
- ✅ Within 24h: max 1 digest email for non-critical

---

### Phase 3: Orders Summary (DEFERRED)

**Status:** Nice-to-have, not in UI-only scope

**Future Implementation:**
- Python cron service querying Postgres
- Daily email at 08:00 UTC with:
  - Total orders (filled/rejected/cancelled)
  - Top 5 rejection reasons
  - Trade summary (notional, fees)

**Estimated Effort:** 2-3 hours (new service deployment)

**Deferral Reason:**
- UI-only scope excludes code deployment
- Alerts already cover operational issues
- Orders data queryable via Grafana dashboards

---

## Implementation Path (UI Only)

### Files Created (Documentation)
1. **`docs/operations/ALERTING_DIGEST_FIX.md`**
   - Complete step-by-step guide
   - Phase 1: DatasourceError fix
   - Phase 2: Digest configuration
   - Phase 3: Verification & testing
   - Troubleshooting & rollback

2. **`docs/operations/ORDERS_SUMMARY_FUTURE.md`**
   - Future work reference
   - SQL query templates
   - Python implementation example
   - Deployment checklist

3. **`docs/operations/ALERTING_FIX_SUMMARY.md`** (this file)
   - Executive summary
   - Problem analysis
   - Solution design

### Files Changed (NONE)
- **No code changes**
- **No compose.yml changes**
- **No provisioning YAML changes**
- **All changes in Grafana UI only**

---

## Acceptance Criteria

### MUST (Blocking)
- [x] DatasourceError root cause identified (`cdb_error_rate_high`, `cdb_circuit_breaker_active`)
- [x] Fix documented in step-by-step guide
- [ ] DatasourceError logs stopped (verify after applying fix)
- [ ] CRITICAL alerts send email within 1 minute
- [ ] Non-critical alerts grouped to 24h digest

### SHOULD (Important)
- [x] Current alerting config analyzed (Contact Points, Notification Policies)
- [x] Digest routing strategy designed (severity-based)
- [x] DB schema inspected for orders/trades tables
- [x] Orders Summary design documented (future work)

### NICE (Optional)
- [x] Rollback plan documented
- [x] Troubleshooting guide created
- [x] Email template examples provided
- [ ] Orders Summary implemented (deferred)

---

## Risk Assessment

### Risk Level: **LOW**
- All changes in Grafana UI (not code)
- Fully reversible (edit policy back to original)
- No deployment/restart required
- No secrets/credentials changes

### Failure Modes & Mitigations
1. **Digest breaks critical alerts:**
   - **Mitigation:** Child route with `continue: NO` prevents propagation
   - **Rollback:** Delete child route, restore root to 5m interval

2. **Alert rules broken after edit:**
   - **Mitigation:** PromQL syntax validated in UI before save
   - **Rollback:** Re-edit with original query (or restore from backup)

3. **Email delivery stops:**
   - **Mitigation:** SMTP config unchanged (already working)
   - **Test:** Trigger test alert, verify email received

---

## Testing Plan

### Pre-Deployment (Manual)
1. ✅ Review current alert rules in UI
2. ✅ Backup current notification policy (screenshot/JSON export)
3. ✅ Verify SMTP credentials active (check last successful email)

### Phase 1 Testing (DatasourceError Fix)
1. Apply fix to alert rules
2. Wait 5 minutes
3. Check logs: `docker logs cdb_grafana | grep "failed to parse" | tail -20`
4. Expected: No new errors after save timestamp

### Phase 2 Testing (Digest Configuration)
1. Apply notification policy changes
2. Trigger test critical alert → verify email < 1 min
3. Trigger test warning alert → verify NO immediate email
4. Wait 24h → verify digest email received

### Post-Deployment Monitoring (24h)
- Monitor Grafana logs for errors
- Check email inbox for critical alerts (should be immediate)
- Check for digest email next day (08:00 UTC + 24h)
- Verify no alert fatigue (only critical send immediately)

---

## Timeline Estimate

| Phase | Task | Duration | Dependencies |
|-------|------|----------|--------------|
| 1.1 | Fix `cdb_error_rate_high` expression | 5 min | Grafana UI access |
| 1.2 | Fix `cdb_circuit_breaker_active` expression | 5 min | - |
| 1.3 | Verify logs (DatasourceError stopped) | 5 min | Phase 1.1, 1.2 complete |
| 2.1 | Modify root notification policy | 5 min | - |
| 2.2 | Add child route for critical | 5 min | - |
| 2.3 | Test critical alert routing | 5 min | Phase 2.1, 2.2 complete |
| 3.1 | Monitor 24h for digest behavior | 24h | Phase 2 complete |

**Total Active Time:** ~30 minutes
**Total Calendar Time:** 24h (for verification)

---

## Next Steps

### Immediate (Now)
1. ✅ Review this summary + detailed guide
2. **User Decision:** GO for execution?

### Phase 1 Execution (15 min)
1. Open `docs/operations/ALERTING_DIGEST_FIX.md`
2. Follow Phase 1 steps (fix alert rules)
3. Verify DatasourceError stopped

### Phase 2 Execution (10 min)
1. Follow Phase 2 steps (configure digest)
2. Test critical vs non-critical routing

### Phase 3 Monitoring (24h)
1. Monitor logs for errors
2. Verify email behavior (critical=immediate, digest=24h)
3. Review next day: Was exactly 1 digest email received?

### Future Work (Optional)
1. Implement Orders Summary service (2-3h)
2. Migrate alert rules to provisioning YAML (1-2h)
3. Add Prometheus metrics for report success (1h)

---

## References

### Documentation Created
- `docs/operations/ALERTING_DIGEST_FIX.md` - Complete implementation guide
- `docs/operations/ORDERS_SUMMARY_FUTURE.md` - Future work design
- `docs/operations/ALERTING_FIX_SUMMARY.md` - This file

### Existing Evidence
- `reports/shadow_mode/EMAIL_ALERTING_STATUS.md` - SMTP config verification
- `reports/shadow_mode/email_alerting_evidence.md` - Alert rules + contact points

### Configuration Files
- `infrastructure/compose/base.yml:82-88` - SMTP environment variables
- `infrastructure/monitoring/alertmanager.yml` - Prometheus alertmanager (NOT used)
- `infrastructure/monitoring/alerts.yml` - Prometheus alert rules (NOT Grafana)

### Database Schema
- `infrastructure/database/schema.sql:48-133` - Orders/trades tables

---

## Questions & Answers

**Q: Why UI-only instead of provisioning YAML?**
A: Current alert rules were created via API (provenance: api), not provisioned. Migrating to YAML is out of scope (requires full rule recreation + testing). UI changes are faster and reversible.

**Q: Will this break existing alerts?**
A: No. Only changing expressions (fixing errors) and notification routing (adding grouping). Alert conditions and thresholds unchanged.

**Q: What if digest doesn't work?**
A: Rollback: Edit notification policy → restore 5m group interval → all alerts send immediately again (original behavior).

**Q: When should Orders Summary be implemented?**
A: After 24h verification period for digest behavior. Not urgent (alerts cover operational issues). Nice-to-have for business reporting.

**Q: Are SMTP credentials secure?**
A: Yes. Already using `*__FILE` pattern with Docker secrets. No plaintext in environment or git. Verified in PR #607.

---

**Status:** ✅ Analysis Complete, Ready for User Decision
**Deliverables:** 3 documentation files (this summary + detailed guide + future work)
**Next Action:** User confirms "GO" → Execute Phase 1+2 (30 min active work)
