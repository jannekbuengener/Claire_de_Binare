---
title: Incident Response Playbook
status: draft
owner: security
date: 2025-12-19
---
# Incident Response Playbook

## Purpose
Define a minimal, actionable incident response flow for Claire de Binare.

## Scope
- Services: cdb_core, cdb_risk, cdb_execution, cdb_ws, cdb_db_writer
- Infrastructure: PostgreSQL, Redis, Docker host, CI/CD

## Detection
- Alerts from Grafana/Prometheus
- Log anomalies (error spikes, auth failures, crash loops)
- CI/CD security alerts (gitleaks, trivy, dependabot)

## Triage
1. Confirm alert validity and impact scope.
2. Identify affected services and data.
3. Classify severity: SEV1 (prod outage), SEV2 (degraded), SEV3 (minor).

## Escalation Matrix
- SEV1: immediate paging of on-call + lead
- SEV2: on-call + notify lead within 30 minutes
- SEV3: ticket and notify lead in daily sync

## Communication
- Internal status updates every 30 minutes (SEV1) / 60 minutes (SEV2)
- External communications only after lead approval

## Recovery Procedures
- Contain: isolate affected services or networks
- Eradicate: remove malicious configs or rotate secrets
- Recover: restore services, verify health checks
- Validate: run smoke tests and confirm metrics normal

## Post-Incident
- Write summary (what/when/impact/root cause)
- Track action items in GitHub issues
- Review and update this playbook if gaps found

## Checklist (SEV1/SEV2)
- [ ] Identify incident start time
- [ ] Snapshot relevant logs/metrics
- [ ] Contain affected services
- [ ] Rotate credentials if required
- [ ] Restore service health
- [ ] Validate data integrity
- [ ] Publish summary and follow-ups
