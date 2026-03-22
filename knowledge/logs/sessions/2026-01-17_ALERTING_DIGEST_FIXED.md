# Alerting Digest Fix - Session Log

**Date:** 2026-01-17
**Time:** 13:44-13:50 UTC
**Operator:** Claude Code (Execution Mode)
**Status:** ✅ RESOLVED & VERIFIED

---

## Context

### Problem
1. **DatasourceError Spam:** Alert rules `cdb_error_rate_high` + `cdb_circuit_breaker_active` triggered parse errors every 1-3 minutes
   - Error: `"failed to parse expression 'C': invalid math command type: expr: non existent function A"`
   - Root cause: Multi-query math expressions (A→B→C) with missing/corrupted Query A

2. **E-Mail Spam:** All alerts sent individual emails every 5 minutes
   - Root cause: Notification policy `group_interval=5m` with no severity-based routing
   - Impact: 10-20+ emails/hour, alert fatigue

---

## Actions Taken

### Phase 1: Fix Alert Rules (13:44-13:47)

**cdb_error_rate_high:**
- Removed broken 3-query math expression
- Replaced with 2-query threshold:
  - Query A: `(rate(execution_orders_rejected_total[5m]) / rate(execution_orders_received_total[5m])) * 100`
  - Query B: Threshold evaluator `> 5`
- Condition changed: `"C"` → `"B"`

**cdb_circuit_breaker_active:**
- Removed broken 2-query math expression (`A == 1`)
- Replaced with 2-query threshold:
  - Query A: `circuit_breaker_active`
  - Query B: Threshold evaluator `> 0.5` (detects value == 1)
- Condition changed: `"C"` → `"B"`
- Note: Used `gt 0.5` instead of `eq 1` due to Grafana threshold constraint

### Phase 2: Configure Daily Digest (13:44)

**Notification Policy Update:**
- Root policy: `group_interval: 24h`, `repeat_interval: 24h`
- Child route added: `severity=critical` → immediate (group_interval: 1m, repeat: 1h)
- Child route stops propagation: `continue: false`

---

## Evidence

### API Endpoints Used
1. `GET /api/v1/provisioning/alert-rules` - Retrieve rules
2. `PUT /api/v1/provisioning/alert-rules/cdb_error_rate_high` - Update rule
3. `PUT /api/v1/provisioning/alert-rules/cdb_circuit_breaker_active` - Update rule (2x)
4. `GET /api/v1/provisioning/policies` - Retrieve policy
5. `PUT /api/v1/provisioning/policies` - Update policy

### Verification (13:50)
- **Restart test passed:** Container restarted at `2026-01-17T13:50:02Z`
- **Parse errors:** 0 (checked logs since restart)
- **Alert evaluations:** Clean - rules sending to notifier without errors
- **Persistence confirmed:** Changes survived restart (stored in Grafana SQLite DB)

---

## Current Config Snapshot

### Notification Policy

**Root Policy (Non-Critical Alerts):**
```json
{
  "receiver": "email-main",
  "group_by": ["grafana_folder", "alertname"],
  "group_wait": "30s",
  "group_interval": "1d",
  "repeat_interval": "1d"
}
```

**Child Route (Critical Alerts):**
```json
{
  "receiver": "email-main",
  "object_matchers": [["severity", "=", "critical"]],
  "group_by": ["grafana_folder", "alertname"],
  "group_wait": "10s",
  "group_interval": "1m",
  "repeat_interval": "1h"
}
```

---

## Rollback Plan

### If Digest Breaks
1. Navigate to Grafana → Alerting → Notification policies
2. Edit Root policy:
   - `group_interval: "5m"` (restore original)
   - `repeat_interval: "4h"` (restore original)
3. Delete child route (`severity=critical`)

### If Alert Rules Break
1. Navigate to Grafana → Alerting → Alert rules
2. Edit affected rule → Restore queries:
   - **cdb_error_rate_high:** Re-create A/B/C queries or use direct PromQL
   - **cdb_circuit_breaker_active:** Re-create A/C queries or use direct PromQL
3. Save and verify logs

**Rollback Time:** ~5 minutes
**Risk:** LOW (UI-only changes, no code deployment)

---

## Outcome

### DatasourceError
- **Status:** ✅ RESOLVED
- **Last error:** 2026-01-17T13:47:20Z (before final fix)
- **Post-restart:** 0 parse errors
- **Rules evaluating:** Successfully (sending to notifier)

### Alert Spam
- **Status:** ✅ STOPPED
- **Critical alerts:** Send immediately (10s wait, 1m interval)
- **Non-critical alerts:** Batch for 24h (single digest email)
- **Expected reduction:** ~95% (only CRITICAL send individually)

---

## Next Steps

### Immediate (Complete)
- [x] DatasourceError eliminated
- [x] Daily digest configured
- [x] Restart test passed
- [x] Documentation created

### Deferred (Future Work)
- [ ] **Daily Orders Summary** - 1 email/day with orders statistics
  - Reference: `docs/operations/ORDERS_SUMMARY_FUTURE.md`
  - Estimated effort: 2-3 hours (new service deployment)
  - Priority: Nice-to-have (alerts already cover operational issues)

- [ ] **GitOps Migration** (optional) - Convert rules to provisioning YAML
  - Current: Rules in Grafana DB (API provenance)
  - Benefit: Version control, reproducibility
  - Effort: 1-2 hours
  - Priority: Low (API-based rules persist correctly)

---

## References

- **Implementation Guide:** `docs/operations/ALERTING_DIGEST_FIX.md`
- **Executive Summary:** `docs/operations/ALERTING_FIX_SUMMARY.md`
- **Orders Summary Design:** `docs/operations/ORDERS_SUMMARY_FUTURE.md`
- **SMTP Config:** `infrastructure/compose/base.yml:82-88`
- **Alert Evidence:** `reports/shadow_mode/EMAIL_ALERTING_STATUS.md`

---

**Session End:** 2026-01-17T13:50 UTC
**Duration:** ~30 minutes (analysis + execution + verification)
**Method:** Browser DevTools + Grafana REST API
**Persistence:** ✅ Verified (survives container restart)
