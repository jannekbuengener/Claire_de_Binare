---
title: Incident Response Playbook
status: draft
owner: maintainer (solo)
date: 2025-12-19
updated: 2026-03-30
---
# Incident Response Playbook

> **Betriebsrealität:** Solo-Maintainer-Setup. Kein On-call-Team, kein Incident Commander,
> keine Mehrpersonen-Eskalation. Alle Schritte werden vom Maintainer selbst ausgeführt.
> KI-Agenten unterstützen bei Analyse, aber der Maintainer entscheidet und handelt.

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

## Reaktionszeiten (Solo-Maintainer)
- SEV1: sofortige Bearbeitung, Kill-Switch aktivieren, Grafana/Logs prüfen
- SEV2: innerhalb 30 Minuten, Ursache isolieren, ggf. betroffenen Service neustarten
- SEV3: GitHub-Issue anlegen, im nächsten Arbeitsfenster bearbeiten

## Kommunikation
- Statusdokumentation via GitHub-Issue (öffentlich) oder Session-Log (intern)
- Keine externen Stakeholder, die benachrichtigt werden müssen

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
