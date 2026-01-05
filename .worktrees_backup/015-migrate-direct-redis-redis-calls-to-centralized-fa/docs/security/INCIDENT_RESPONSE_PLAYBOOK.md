# Incident Response Playbook - Claire de Binare

**Version:** 1.0
**Status:** Active
**Issue:** #102
**Last Updated:** 2025-12-28

---

## 1. Incident Classification

### Severity Levels

| Level | Name | Description | Response Time | Examples |
|-------|------|-------------|---------------|----------|
| **SEV-1** | Critical | Trading system completely down or major financial exposure | < 15 min | Kill-switch failure, Exchange API down, Data breach |
| **SEV-2** | High | Partial system failure or significant risk exposure | < 1 hour | Circuit breaker triggered, Service crash loop |
| **SEV-3** | Medium | Degraded performance or minor issues | < 4 hours | Slow market data, Missing metrics |
| **SEV-4** | Low | Cosmetic or monitoring issues | < 24 hours | Dashboard not loading, Log rotation failed |

---

## 2. Detection Procedures

### Automatic Detection

| Source | What It Detects | Alert Channel |
|--------|-----------------|---------------|
| **Circuit Breaker** | Daily loss > threshold | Kill-switch auto-activate + Grafana alert |
| **Health Checks** | Service unavailable | Docker restart + Grafana alert |
| **Risk Service** | Exposure limit breach | Kill-switch + Prometheus counter |
| **Log Monitoring** | ERROR pattern spike | Loki alert rule |
| **Trivy Scanner** | New CRITICAL CVE | GitHub Security advisory |

### Manual Detection Triggers

- Unusual P&L movement
- Customer/user reports
- Exchange status announcements
- Third-party monitoring alerts

### Key Metrics to Monitor

```promql
# Kill-switch state
cdb_kill_switch_active

# Order rejections (circuit breaker)
cdb_orders_blocked_total

# Service health
up{job=~"cdb_.*"}

# Error rate
rate(cdb_errors_total[5m])
```

---

## 3. Triage Guidelines

### Initial Assessment (First 5 Minutes)

1. **Acknowledge** the alert/report
2. **Identify** the affected component(s)
3. **Determine** severity level (see classification above)
4. **Check** kill-switch status:
   ```powershell
   Get-Content .cdb_kill_switch.state
   ```
5. **Decision**: Activate kill-switch? (default: YES for SEV-1/SEV-2)

### Triage Decision Tree

```
Is trading actively losing money?
├── YES → Activate Kill-Switch → SEV-1
└── NO
    └── Is any service completely down?
        ├── YES → SEV-2 (1 service) or SEV-1 (core services)
        └── NO
            └── Is performance degraded?
                ├── YES → SEV-3
                └── NO → SEV-4
```

### Triage Checklist

- [ ] Kill-switch status checked
- [ ] Severity assigned
- [ ] Incident commander identified (for SEV-1/SEV-2)
- [ ] Communication initiated
- [ ] Initial findings documented

---

## 4. Escalation Matrix

| Severity | Primary Contact | Escalation (if no response in 15 min) | Executive Notify |
|----------|-----------------|---------------------------------------|------------------|
| **SEV-1** | On-call Engineer | Tech Lead → CTO | Yes (immediate) |
| **SEV-2** | On-call Engineer | Tech Lead | If > 1 hour |
| **SEV-3** | Assigned Engineer | On-call Engineer | No |
| **SEV-4** | Engineering Queue | No escalation | No |

### Contact Information

| Role | Primary | Backup |
|------|---------|--------|
| **On-call Engineer** | Rotation (PagerDuty) | #engineering-oncall |
| **Tech Lead** | [TBD] | #tech-leads |
| **CTO** | [TBD] | Direct call |

---

## 5. Communication Plan

### Internal Communication

| Channel | When to Use | Audience |
|---------|-------------|----------|
| **#incidents** (Slack/Discord) | All SEV-1/SEV-2 | Engineering team |
| **#engineering** | SEV-3/SEV-4 updates | Full engineering |
| **Email** | Post-incident summary | Stakeholders |
| **War Room** (Video call) | Active SEV-1 | Incident responders |

### Communication Templates

**Initial Alert (SEV-1/SEV-2):**
```
🚨 INCIDENT: [Brief Description]
Severity: SEV-X
Status: Investigating
Impact: [What is affected]
Kill-Switch: Active/Inactive
Next Update: [Time]
Commander: [Name]
```

**Status Update:**
```
📊 INCIDENT UPDATE: [Brief Description]
Status: [Investigating/Mitigating/Resolved]
Progress: [What was done]
Next Steps: [What's planned]
Next Update: [Time]
```

**Resolution:**
```
✅ INCIDENT RESOLVED: [Brief Description]
Duration: [Total time]
Root Cause: [Brief summary]
Action Items: [Follow-ups]
Post-mortem: [Scheduled date]
```

---

## 6. Response Procedures by Type

### 6.1 Kill-Switch Activated (Automatic)

**See:** [EMERGENCY_STOP_SOP.md](../EMERGENCY_STOP_SOP.md)

1. Acknowledge alert
2. Check reason: `Get-Content .cdb_kill_switch.state`
3. Investigate root cause
4. Resolve underlying issue
5. Follow deactivation procedure (with approval)
6. Monitor for 30 minutes post-resume

### 6.2 Service Crash Loop

1. Check Docker status: `docker ps -a`
2. Check logs: `docker logs cdb_[service] --tail 100`
3. Check resource usage: `docker stats`
4. If memory issue: Restart with limits adjusted
5. If code issue: Rollback to last known good image
6. Document and create follow-up issue

### 6.3 Exchange API Failure

1. Check exchange status page
2. Verify API credentials
3. Check rate limits: `docker logs cdb_market | grep 429`
4. If exchange down: Activate kill-switch (EXCHANGE_ERROR)
5. Wait for exchange recovery
6. Resume trading after stability confirmed (15+ min stable)

### 6.4 Security Incident (Potential Breach)

1. **Immediate:** Activate kill-switch (AUTH_FAILURE)
2. **Isolate:** Disconnect affected systems from network
3. **Preserve:** Capture logs, do not modify evidence
4. **Escalate:** Notify CTO immediately
5. **Investigate:** Determine scope of breach
6. **Remediate:** Rotate all credentials
7. **Document:** Detailed incident report required

---

## 7. Recovery Procedures

### Pre-Recovery Checklist

- [ ] Root cause identified
- [ ] Fix deployed or rolled back
- [ ] All services healthy
- [ ] Metrics baseline normal
- [ ] Kill-switch ready to deactivate

### Recovery Steps

1. **Verify Health:**
   ```powershell
   docker ps --format "table {{.Names}}\t{{.Status}}"
   # All 9 services should show "healthy"
   ```

2. **Check Metrics:**
   - Error rate < 0.1%
   - Response time < normal + 20%
   - No pending alerts

3. **Deactivate Kill-Switch (if active):**
   ```python
   from core.safety import KillSwitch
   ks = KillSwitch()
   ks.deactivate("operator@email", "Justification: [details]")
   ```

4. **Monitor (30 min window):**
   - Watch first 10 trades execute successfully
   - Monitor for re-trigger of circuit breaker
   - Check logs for new errors

5. **Declare Resolved:**
   - Post resolution message
   - Schedule post-mortem (within 48h for SEV-1/SEV-2)

---

## 8. Post-Incident

### Post-Mortem Requirements

| Severity | Post-Mortem Required | Deadline |
|----------|---------------------|----------|
| SEV-1 | Yes | 48 hours |
| SEV-2 | Yes | 1 week |
| SEV-3 | Optional | 2 weeks |
| SEV-4 | No | N/A |

### Post-Mortem Template

```markdown
# Incident Post-Mortem: [Title]

**Date:** YYYY-MM-DD
**Severity:** SEV-X
**Duration:** X hours Y minutes
**Commander:** [Name]

## Summary
[1-2 sentence summary]

## Timeline
- HH:MM - Event 1
- HH:MM - Event 2
...

## Root Cause
[Detailed explanation]

## Impact
- Trading halted for X hours
- X orders affected
- X USD exposure during incident

## What Went Well
- Item 1
- Item 2

## What Went Poorly
- Item 1
- Item 2

## Action Items
| Action | Owner | Deadline | Issue |
|--------|-------|----------|-------|
| Fix X | @name | YYYY-MM-DD | #XXX |

## Lessons Learned
[Key takeaways]
```

---

## 9. Training & Drills

### Drill Schedule

| Drill Type | Frequency | Last Run | Next Scheduled |
|------------|-----------|----------|----------------|
| Kill-switch test | Monthly | TBD | TBD |
| Failover test | Quarterly | TBD | TBD |
| Full incident drill | Semi-annual | TBD | TBD |

### Drill Procedure

1. Announce drill in #engineering (24h notice)
2. Simulate incident scenario
3. Time response metrics
4. Review and document findings
5. Update playbook based on learnings

---

## 10. Related Documents

- [EMERGENCY_STOP_SOP.md](../EMERGENCY_STOP_SOP.md) - Kill-switch operations
- [SECURITY_BASELINE.md](./SECURITY_BASELINE.md) - Security posture
- [STACK_LIFECYCLE.md](../STACK_LIFECYCLE.md) - Service management
- [HEALTH_CONTRACT.md](../HEALTH_CONTRACT.md) - Health check specifications
- [HITL_RUNBOOK.md](../HITL_RUNBOOK.md) - Human-in-the-loop procedures

---

## Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Author | Claude (Session Lead) | 2025-12-28 | ✅ |
| Reviewer | [TBD] | | |
| Approver | [TBD] | | |

---

**Document Control:**
- Created: 2025-12-28 (Issue #102)
- Review Cycle: Quarterly
- Owner: Security Team
