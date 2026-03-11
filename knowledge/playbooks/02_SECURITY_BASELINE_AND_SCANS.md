# 02 — Security Baseline & Scans (Runbook)

## Ziel
- Sicherheitszustand versioniert festhalten
- CVE-Fixes reproduzierbar ausrollen
- CI-Scans so konfigurieren, dass sie Regressionen stoppen, aber nicht permanent nerven

## Baseline (Was gilt als “akzeptiert”?)
Eine Security Baseline ist dann “kanonisch”, wenn sie folgendes enthält:
- Commit Hash / PR Link des Fixes
- betroffene Services/Images
- CVE IDs + Severity
- Fix-Mechanik (z.B. pip bump, base image pin)
- Verify Commands + erwartete Outputs
- Accept-Risk Einträge: Begründung + Upstream Tracking + Re-Check Datum

## Scan Gate Philosophie
- **Custom Images**: fail on **NEW** High/Critical (Regressionen blocken)
- **Base Images**: nicht hart failen, aber dokumentieren (Upstream gosu etc.)

## Canonical Verify Commands
### pip Version in Container prüfen
```powershell
docker exec cdb_execution pip --version
```
Erwartung: definierte Version (z.B. pip 25.3).

### Base Image Versionen prüfen
```powershell
docker exec cdb_redis redis-server --version
docker exec cdb_postgres postgres --version
```

## Wenn GitHub “Found vulnerability on default branch” meldet
Das ist meist Dependabot / Advisory – nicht zwingend ein Build-Blocker.
Vorgehen:
1) Link öffnen (Advisory)
2) Betroffene dependency identifizieren
3) Entscheiden: hotfix vs scheduled upgrade
4) Baseline aktualisieren (wenn accepted)

## DoD (Security Change)
- Baseline-Doku aktualisiert
- Verify Commands laufen lokal
- CI-Scan Verhalten verstanden: was blockt, was nicht
