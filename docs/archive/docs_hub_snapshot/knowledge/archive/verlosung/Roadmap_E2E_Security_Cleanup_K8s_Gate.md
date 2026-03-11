# Roadmap – E2E Stabilization, Security Hygiene, Cleanup Routine, Kubernetes Gate

**Projekt:** Claire de Binare  
**Version:** 1.0  
**Datum:** 2025-12-26  
**Status:** PLANNING ONLY – Keine Implementation  

---

## 1. Executive Summary

- **E2E-Tests sind P0**: Keine weiteren Architektur-Änderungen, bis alle kritischen Pfade grün sind
- **Docker Compose bleibt Source-of-Truth** bis E2E stabil (≥95% Pass-Rate, 0 Critical Flaky)
- **Security-Hygiene priorisiert nach Risiko**: 6 kritische CVEs in Postgres/Redis sofort, Rest nach E2E
- **Kubernetes hinter Go/No-Go Gate**: Erst nach E2E-Stabilität, Cleanup, und Security-Baseline
- **Cleanup-Routine etablieren**: 3.66 GB Build-Cache + 92 MB Volumes freigeben, monatlicher Cadence

---

## 2. Guiding Principles

| Prinzip | Bedeutung |
|---------|-----------|
| **E2E-First** | Kein Feature-Code, keine Architektur-Änderung, bis E2E grün |
| **Minimal Risk** | Änderungen nur mit Rollback-Plan; Named Volumes niemals automatisch löschen |
| **Reversible Steps** | Jede Aktion muss rückgängig machbar sein; Snapshots vor destruktiven Ops |
| **Single Source of Truth** | `docker-compose.yml` ist kanonisch; K8s-Manifeste sind Derivate |
| **Sicherheit vor Profit** | Gemäß MANIFEST.md – keine Kompromisse bei Security-Kritisch |

---

## 3. Workstream A: E2E Tests (P0) — PRIMARY

### 3.1 Current State

| Kategorie | Status | Notizen |
|-----------|--------|---------|
| **Unit Tests** | ⚠️ Unbekannt | Baseline erfassen |
| **Integration Tests** | ⚠️ Unbekannt | Service-zu-Service-Kommunikation |
| **E2E Tests** | 🔴 Nicht stabil | Kritischer Pfad muss definiert werden |
| **Test-Infrastruktur** | ⚠️ Docker-basiert | Compose-Profile für Test-Environment fehlen ggf. |
| **CI Pipeline** | ⚠️ Vorhanden | Automatische E2E-Ausführung prüfen |

**Bekannte Gaps (aus Projektkontext):**
- Health-Check-Endpunkte: `/health` muss in allen Services implementiert sein
- Redis Pub/Sub: Message-Flow E2E verifizieren
- PostgreSQL: Persistence-Tests (Crash-Recovery, Data-Integrity)
- Paper-Trading-Flow: Kompletter Zyklus Signal → Execution → DB-Write

### 3.2 Phases

#### Phase A.1: Test-Inventory & Baseline (Week 1)

- [ ] Alle existierenden Tests inventarisieren (`pytest --collect-only`)
- [ ] Test-Kategorien taggen: `unit`, `integration`, `e2e`, `slow`, `flaky`
- [ ] Baseline-Report erstellen: Pass/Fail/Skip-Ratio
- [ ] Kritischen Pfad definieren (Signal → Risk → Execution → DB)
- [ ] Test-Coverage-Report generieren

#### Phase A.2: Test-Infrastruktur härten (Week 2)

- [ ] `docker-compose.test.yml` Overlay erstellen (isolierte Test-DB, Mock-Exchange)
- [ ] Fixtures für deterministische Testdaten (Seed-Daten für PostgreSQL)
- [ ] Redis-Mocking oder Test-Channel-Isolation
- [ ] Health-Check-Waits in Test-Setup integrieren
- [ ] CI-Job: `pytest -m e2e --tb=short --maxfail=5`

#### Phase A.3: Critical Path E2E (Week 3-4)

- [ ] Test: Signal-Engine → Redis Pub → Execution Service
- [ ] Test: Execution Service → Risk Manager Validation
- [ ] Test: Order → (Paper) Exchange → DB-Writer Persistence
- [ ] Test: Health-Endpoints aller Services (Prometheus Targets)
- [ ] Test: Graceful Shutdown (SIGTERM → Cleanup → Exit 0)

#### Phase A.4: Stabilisierung & Flaky-Elimination (Week 5)

- [ ] Alle flaky Tests identifizieren (3x Retry-Detection)
- [ ] Root-Cause für jeden flaky Test dokumentieren
- [ ] Timing-Issues mit expliziten Waits/Polling beheben
- [ ] Race-Conditions durch Locks oder deterministischen Setup lösen
- [ ] Finale Baseline: ≥95% Pass, 0 Critical Flaky

### 3.3 Acceptance Criteria (Definition of Done)

| Kriterium | Threshold |
|-----------|-----------|
| E2E Pass-Rate | ≥ 95% |
| Critical-Path Tests | 100% Pass |
| Flaky Tests (kritisch) | 0 |
| Test-Execution-Time | < 10 min (Compose-Stack) |
| Coverage (kritischer Pfad) | ≥ 80% |
| CI Integration | Automatisch bei jedem PR |

### 3.4 Verification Commands

```bash
# Baseline erfassen
pytest --collect-only -q 2>&1 | tee test_inventory.txt

# Alle Tests mit Marker-Info
pytest --markers

# E2E Tests ausführen
pytest -m e2e -v --tb=short --maxfail=10

# Coverage-Report
pytest --cov=src --cov-report=html -m "not slow"

# Flaky-Detection (3x Run)
pytest -m e2e --count=3 -x

# Health-Check aller Container
for c in $(docker ps --format '{{.Names}}'); do
  echo "=== $c ===" && docker exec $c curl -sf http://localhost:8080/health || echo "FAIL"
done

# CI Dry-Run lokal
docker compose -f docker-compose.yml -f docker-compose.test.yml up --abort-on-container-exit --exit-code-from test-runner
```

---

## 4. Workstream B: Security Hygiene

### 4.1 Triage-Regeln: Actionable vs Noise

| Severity | Actionable? | Aktion |
|----------|-------------|--------|
| **Critical (CVSS ≥9)** | ✅ Ja | Sofort beheben, Blocker für Release |
| **High (CVSS 7-8.9)** | ✅ Ja | Innerhalb 2 Wochen, P1 |
| **Medium (CVSS 4-6.9)** | ⚠️ Prüfen | Nur wenn exploitbar im Kontext |
| **Low (CVSS <4)** | ❌ Noise | Dokumentieren, nicht blockieren |
| **No Fix Available** | ❌ Defer | Exception-Policy, Review in 30 Tagen |

### 4.2 Fix Now vs Later Rubrik

**Fix NOW (vor E2E-Abschluss):**
- 6 kritische CVEs in PostgreSQL (Go stdlib 1.18.2, libxml2)
- 4 kritische CVEs in Redis
- CVE-2025-45582 in tar (Python-Images) – mittel, aber einfach

**Fix AFTER E2E:**
- Grafana 4 medium (golang/x/crypto, AWS-SDK)
- Prometheus 2 medium
- Python Low-Severity (kein Patch verfügbar)

**Exception-Policy Template:**
```
CVE-ID: CVE-XXXX-XXXXX
Status: DEFERRED
Grund: Kein Patch verfügbar / Nicht exploitbar im Kontext
Review-Datum: [+30 Tage]
Verantwortlich: [Name]
```

### 4.3 Prioritized Actions (aus Vulnerability-Report)

| Priorität | Image | Aktion |
|-----------|-------|--------|
| P0 | `postgres:15.x-alpine` | Upgrade auf `postgres:16-alpine` oder `17-alpine` |
| P0 | `redis:7.4.x-alpine` | Upgrade auf `redis:7.4-alpine3.21` |
| P1 | `python:3.11-slim` | Upgrade auf `python:3.12-slim` (3.14 nach Kompatibilitätstest) |
| P1 | Alle Images | Tags pinnen, kein `:latest` |
| P2 | `grafana/grafana` | Feste Version pinnen, CVE-Patches abwarten |
| P2 | `prom/prometheus` | Feste Version pinnen |

### 4.4 Minimal CI Gate Proposal

```yaml
# .github/workflows/security-scan.yml (Konzept)
name: Security Scan Gate
on: [push, pull_request]
jobs:
  scout-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: docker/scout-action@v1
        with:
          command: cves
          image: ${{ matrix.image }}
          only-severities: critical,high
          exit-code: true  # Fail on critical/high
```

**Gate-Logik:**
- **Block PR** bei: Critical CVEs mit verfügbarem Fix
- **Warn** bei: High CVEs, Medium mit hohem CVSS
- **Pass** bei: Low, oder No-Fix-Available (mit Exception)

---

## 5. Workstream C: Cleanup & Maintenance Routine

### 5.1 Safe Commands + Cadence

| Cadence | Befehl | Effekt | Risiko |
|---------|--------|--------|--------|
| **Wöchentlich** | `docker image prune -f` | Dangling Images entfernen | ⚪ Niedrig |
| **Wöchentlich** | `docker container prune -f` | Gestoppte Container entfernen | ⚪ Niedrig |
| **Nach Release** | `docker builder prune -f` | Build-Cache leeren (~3.66 GB) | ⚪ Niedrig |
| **Monatlich** | `docker system df` | Speicher-Audit | ⚪ Info only |
| **Nie automatisch** | `docker volume prune` | Unbenutzte Volumes löschen | 🔴 Hoch |
| **Nie automatisch** | `docker system prune -a --volumes` | Alles löschen | 🔴 Kritisch |

### 5.2 Guardrails

**NIEMALS automatisch löschen:**
- Named Volumes: `cdb_postgres_data`, `cdb_redis_data`, `cdb_grafana_data`
- Aktive Images (in `docker-compose.yml` referenziert)
- Build-Cache während eines laufenden Builds

**VOR jedem Cleanup:**
```bash
# Snapshot der Volume-Liste
docker volume ls > volume_snapshot_$(date +%Y%m%d).txt

# Aktive Container prüfen
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Compose-Stack stoppen (optional für Deep Clean)
docker compose down  # OHNE -v Flag!
```

**Safe Cleanup Script (Konzept):**
```bash
#!/bin/bash
# stack_clean_safe.sh - Sicherer Cleanup
set -e

echo "=== CDB Safe Cleanup ==="
echo "Dangling images..."
docker image prune -f

echo "Stopped containers..."
docker container prune -f

echo "Build cache (after confirmation)..."
read -p "Clear build cache? (y/N) " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker builder prune -f
fi

echo "=== Cleanup complete ==="
docker system df
```

### 5.3 Monitoring Integration

- Prometheus-Metrik für Docker-Disk-Usage (via cAdvisor oder Node Exporter)
- Alert bei: Disk Usage > 80% auf Docker-Volume-Mount
- Grafana-Dashboard: Container-Count, Image-Count, Cache-Size

---

## 6. Workstream D: Kubernetes Go/No-Go Gate

### 6.1 Prerequisites Checklist (KEINE Implementation)

| # | Prerequisite | Status | Blocker für Go? |
|---|--------------|--------|-----------------|
| 1 | E2E Tests ≥95% Pass-Rate | ⬜ Offen | ✅ Ja |
| 2 | 0 Critical CVEs | ⬜ Offen | ✅ Ja |
| 3 | Alle Images Tag-gepinnt (kein :latest) | ⬜ Offen | ✅ Ja |
| 4 | Docker Compose vollständig dokumentiert | ⬜ Offen | ✅ Ja |
| 5 | Cleanup-Routine etabliert | ⬜ Offen | ⚠️ Empfohlen |
| 6 | CI Security-Gate aktiv | ⬜ Offen | ⚠️ Empfohlen |
| 7 | Runbook für Rollback vorhanden | ⬜ Offen | ✅ Ja |
| 8 | Budget für Cloud-K8s geklärt (falls Cloud) | ⬜ Offen | ✅ Ja (für Cloud) |
| 9 | Helm/Kustomize Template-Struktur definiert | ⬜ Offen | ⚠️ Empfohlen |
| 10 | Team-Schulung K8s-Basics | ⬜ Offen | ⚠️ Empfohlen |

### 6.2 Minimal Cost Logic: Local vs Cloud

| Option | Setup-Kosten | Laufende Kosten | Empfehlung |
|--------|--------------|-----------------|------------|
| **Minikube (lokal)** | 0€ | 0€ (Hardware vorhanden) | ✅ Für Dev/Test |
| **kind (lokal)** | 0€ | 0€ | ✅ Für CI |
| **Docker Desktop K8s** | 0€ | 0€ | ✅ Für lokales Prototyping |
| **DigitalOcean K8s** | ~0€ | ~$12/Monat (1 Node) | ⚠️ Für Staging |
| **AWS EKS** | ~0€ | ~$72/Monat + Nodes | ❌ Overhead für CDB |
| **GKE Autopilot** | ~0€ | ~$60/Monat (minimal) | ⚠️ Alternative |

**Empfehlung:** Lokal starten (Minikube/kind), Cloud erst bei Bedarf für Staging/Prod.

### 6.3 Go/No-Go Decision Criteria

**GO wenn:**
- [ ] Alle Blocker-Prerequisites (1-4, 7-8) sind ✅
- [ ] E2E Pass-Rate stabil ≥95% über 2 Wochen
- [ ] Kein offener P0-Bug im Backlog
- [ ] Compose-Architektur dokumentiert und stabil
- [ ] Team-Kapazität für K8s-Migration vorhanden
- [ ] Klarer Business-Case (Skalierung, Multi-Node, HA)

**NO-GO wenn:**
- [ ] E2E instabil oder <95%
- [ ] Critical CVEs offen
- [ ] Compose-Architektur noch in Flux
- [ ] Kein Rollback-Plan dokumentiert
- [ ] Budget ungeklärt (bei Cloud-Option)

**Review-Intervall:** Nach E2E-Stabilisierung (ca. Week 6), dann monatlich.

---

## 7. Issue Backlog

### Format
```
[ID] Title
Workstream: A/B/C/D | Priority: P0/P1/P2 | Labels: [...] | Milestone: [...]
Description: ...
Acceptance Criteria: ...
Verification: ...
```

---

### Workstream A: E2E Tests

**[A-01] Create Test Inventory Baseline**
- Workstream: A | Priority: P0 | Labels: `testing`, `documentation`
- Milestone: E2E-Phase-1
- Description: Alle existierenden Tests erfassen, kategorisieren (unit/integration/e2e), Pass/Fail/Skip dokumentieren.
- Acceptance Criteria: `test_inventory.md` existiert mit vollständiger Liste
- Verification: `pytest --collect-only -q | wc -l` gibt Anzahl zurück

**[A-02] Tag All Tests with Markers**
- Workstream: A | Priority: P0 | Labels: `testing`, `tech-debt`
- Milestone: E2E-Phase-1
- Description: Pytest-Marker (`@pytest.mark.e2e`, `@pytest.mark.slow`, etc.) auf alle Tests anwenden.
- Acceptance Criteria: `pytest -m e2e` läuft ohne Warnings
- Verification: `pytest --markers | grep -E "(e2e|slow|flaky)"`

**[A-03] Create docker-compose.test.yml Overlay**
- Workstream: A | Priority: P0 | Labels: `testing`, `infrastructure`
- Milestone: E2E-Phase-2
- Description: Isoliertes Test-Environment mit eigener DB, Mock-Exchange, deterministischen Ports.
- Acceptance Criteria: `docker compose -f docker-compose.yml -f docker-compose.test.yml up` startet Test-Stack
- Verification: `docker ps | grep test` zeigt Test-Container

**[A-04] Implement PostgreSQL Test Fixtures**
- Workstream: A | Priority: P0 | Labels: `testing`, `database`
- Milestone: E2E-Phase-2
- Description: Seed-Daten und Cleanup-Fixtures für deterministische Tests.
- Acceptance Criteria: Tests starten mit bekanntem DB-State, Cleanup nach Test
- Verification: `pytest -m e2e -k db --setup-show`

**[A-05] E2E Test: Signal → Execution Flow**
- Workstream: A | Priority: P0 | Labels: `testing`, `critical-path`
- Milestone: E2E-Phase-3
- Description: End-to-End Test des Signal-Flows von Engine über Redis bis Execution.
- Acceptance Criteria: Test verifiziert Message-Delivery und Execution-Trigger
- Verification: `pytest tests/e2e/test_signal_flow.py -v`

**[A-06] E2E Test: Risk Manager Validation**
- Workstream: A | Priority: P0 | Labels: `testing`, `critical-path`, `risk`
- Milestone: E2E-Phase-3
- Description: Test dass Risk-Manager Orders korrekt validiert/ablehnt.
- Acceptance Criteria: Invalid Orders werden rejected, Valid Orders passieren
- Verification: `pytest tests/e2e/test_risk_validation.py -v`

**[A-07] E2E Test: Order → DB Persistence**
- Workstream: A | Priority: P0 | Labels: `testing`, `critical-path`, `database`
- Milestone: E2E-Phase-3
- Description: Verifizieren dass ausgeführte Orders korrekt in PostgreSQL persistiert werden.
- Acceptance Criteria: Order in DB, alle Felder korrekt, Timestamps valide
- Verification: `pytest tests/e2e/test_order_persistence.py -v`

**[A-08] E2E Test: Health Endpoints All Services**
- Workstream: A | Priority: P1 | Labels: `testing`, `monitoring`
- Milestone: E2E-Phase-3
- Description: Alle `/health` Endpoints antworten mit 200 OK.
- Acceptance Criteria: Alle Services haben Health-Endpoint, alle grün
- Verification: `pytest tests/e2e/test_health_endpoints.py -v`

**[A-09] E2E Test: Graceful Shutdown**
- Workstream: A | Priority: P1 | Labels: `testing`, `reliability`
- Milestone: E2E-Phase-3
- Description: SIGTERM führt zu sauberem Shutdown, keine verlorenen Messages.
- Acceptance Criteria: Exit-Code 0, keine Pending-Messages, Logs zeigen Cleanup
- Verification: `pytest tests/e2e/test_graceful_shutdown.py -v`

**[A-10] Flaky Test Detection & Fix**
- Workstream: A | Priority: P0 | Labels: `testing`, `stability`
- Milestone: E2E-Phase-4
- Description: Alle flaky Tests identifizieren (3x Run), Root-Cause dokumentieren, beheben.
- Acceptance Criteria: 0 flaky Tests nach 3x consecutive Runs
- Verification: `pytest -m e2e --count=3 -x` alle Runs grün

**[A-11] CI Pipeline E2E Integration**
- Workstream: A | Priority: P0 | Labels: `ci`, `testing`
- Milestone: E2E-Phase-4
- Description: E2E Tests laufen automatisch bei jedem PR.
- Acceptance Criteria: GitHub Action/GitLab Job existiert, Fail blockt Merge
- Verification: PR erstellen, CI-Run beobachten

---

### Workstream B: Security Hygiene

**[B-01] Upgrade PostgreSQL to postgres:16-alpine**
- Workstream: B | Priority: P0 | Labels: `security`, `critical`, `database`
- Milestone: Security-Sprint
- Description: 6 kritische CVEs in aktueller Version; Upgrade auf 16 oder 17.
- Acceptance Criteria: Neues Image in Compose, alle Tests grün, DB-Migration erfolgreich
- Verification: `docker scout cves postgres:16-alpine | grep -c CRITICAL` = 0

**[B-02] Upgrade Redis to redis:7.4-alpine3.21**
- Workstream: B | Priority: P0 | Labels: `security`, `critical`, `cache`
- Milestone: Security-Sprint
- Description: 4 kritische CVEs; Upgrade auf aktuellste Alpine-Version.
- Acceptance Criteria: Neues Image in Compose, alle Tests grün
- Verification: `docker scout cves redis:7.4-alpine3.21 | grep -c CRITICAL` = 0

**[B-03] Pin All Image Tags**
- Workstream: B | Priority: P1 | Labels: `security`, `best-practice`
- Milestone: Security-Sprint
- Description: Kein `:latest` Tag; alle Images mit spezifischer Version oder Digest.
- Acceptance Criteria: `grep -r ":latest" docker-compose.yml` = 0 Treffer
- Verification: `grep -E "image:.*:latest" docker-compose*.yml`

**[B-04] Upgrade Python Base Image**
- Workstream: B | Priority: P1 | Labels: `security`, `python`
- Milestone: Security-Sprint
- Description: Von 3.11-slim auf 3.12-slim (CVE-2025-45582 in tar).
- Acceptance Criteria: Alle Python-Services bauen, Tests grün
- Verification: `docker scout cves cdb_execution:latest | grep tar`

**[B-05] Create CVE Exception Policy Document**
- Workstream: B | Priority: P1 | Labels: `security`, `documentation`
- Milestone: Security-Sprint
- Description: Template für "No Fix Available" CVEs mit Review-Datum.
- Acceptance Criteria: `docs/security/CVE_EXCEPTIONS.md` existiert
- Verification: Datei vorhanden, Format korrekt

**[B-06] Implement CI Security Gate**
- Workstream: B | Priority: P2 | Labels: `ci`, `security`
- Milestone: Post-E2E
- Description: GitHub Action mit Docker Scout, blockt bei Critical.
- Acceptance Criteria: CI Job existiert, Critical CVE blockt PR
- Verification: PR mit vulnerable Image erstellen, Gate triggert

**[B-07] Pin Grafana/Prometheus Versions**
- Workstream: B | Priority: P2 | Labels: `security`, `monitoring`
- Milestone: Post-E2E
- Description: Feste Versions-Tags statt latest/floating.
- Acceptance Criteria: Konkrete Versions in Compose
- Verification: `grep -E "grafana|prometheus" docker-compose.yml | grep -v latest`

---

### Workstream C: Cleanup & Maintenance

**[C-01] Create Safe Cleanup Script**
- Workstream: C | Priority: P1 | Labels: `maintenance`, `scripts`
- Milestone: Cleanup-Phase
- Description: `stack_clean.sh` mit Safe-Mode (schützt Volumes) und Deep-Clean mit Confirmation.
- Acceptance Criteria: Script existiert, dokumentiert, getestet
- Verification: `./stack_clean.sh --dry-run`

**[C-02] Execute Build Cache Prune**
- Workstream: C | Priority: P1 | Labels: `maintenance`, `storage`
- Milestone: Cleanup-Phase
- Description: ~3.66 GB Build-Cache freigeben nach erfolgreichem Build.
- Acceptance Criteria: `docker system df` zeigt reduzierten Cache
- Verification: `docker builder prune -f && docker system df`

**[C-03] Audit and Document Volumes**
- Workstream: C | Priority: P1 | Labels: `maintenance`, `documentation`
- Milestone: Cleanup-Phase
- Description: Alle Named Volumes dokumentieren (Purpose, Service, Backup-Need).
- Acceptance Criteria: `docs/infrastructure/VOLUMES.md` existiert
- Verification: Datei vorhanden, alle Volumes gelistet

**[C-04] Remove Unused Volumes (Manual)**
- Workstream: C | Priority: P2 | Labels: `maintenance`, `storage`
- Milestone: Cleanup-Phase
- Description: ~92 MB unbenutzte Volumes nach manueller Prüfung entfernen.
- Acceptance Criteria: Nur bestätigt unbenutzte Volumes entfernt
- Verification: `docker volume ls | wc -l` vor/nach vergleichen

**[C-05] Add Storage Metrics to Monitoring**
- Workstream: C | Priority: P2 | Labels: `monitoring`, `infrastructure`
- Milestone: Post-E2E
- Description: Prometheus-Metriken für Docker Disk Usage (cAdvisor/Node Exporter).
- Acceptance Criteria: Grafana-Dashboard zeigt Disk-Usage
- Verification: Grafana Query: `container_fs_usage_bytes`

**[C-06] Establish Monthly Cleanup Cadence**
- Workstream: C | Priority: P2 | Labels: `maintenance`, `process`
- Milestone: Post-E2E
- Description: Recurring Task im Projektmanagement für monatlichen Cleanup.
- Acceptance Criteria: Kalender-Event/Issue-Template existiert
- Verification: Recurring Reminder aktiv

---

### Workstream D: Kubernetes Gate

**[D-01] Document Compose Architecture Completely**
- Workstream: D | Priority: P1 | Labels: `documentation`, `architecture`
- Milestone: K8s-Prerequisites
- Description: ARCHITEKTUR.md mit allen Services, Ports, Volumes, Networks.
- Acceptance Criteria: Dokument vollständig, aktuell, reviewed
- Verification: Review durch zweite Person

**[D-02] Create Rollback Runbook**
- Workstream: D | Priority: P1 | Labels: `documentation`, `operations`
- Milestone: K8s-Prerequisites
- Description: Step-by-Step Anleitung für Rollback von K8s zu Compose.
- Acceptance Criteria: `docs/operations/ROLLBACK_K8S_TO_COMPOSE.md` existiert
- Verification: Dry-Run der Schritte

**[D-03] Define K8s Budget Decision**
- Workstream: D | Priority: P1 | Labels: `planning`, `budget`
- Milestone: K8s-Prerequisites
- Description: Entscheidung: Local-Only (Minikube) vs Cloud; Budget dokumentieren.
- Acceptance Criteria: Entscheidung in `docs/architecture/K8S_DECISION.md`
- Verification: Dokument vorhanden mit Begründung

**[D-04] Helm/Kustomize Structure Definition**
- Workstream: D | Priority: P2 | Labels: `planning`, `kubernetes`
- Milestone: K8s-Prerequisites
- Description: Template-Struktur definieren (Helm Charts vs Kustomize Overlays).
- Acceptance Criteria: Decision Record dokumentiert
- Verification: ADR vorhanden

**[D-05] K8s Go/No-Go Review Meeting**
- Workstream: D | Priority: P1 | Labels: `planning`, `milestone`
- Milestone: K8s-Gate
- Description: Formelles Review aller Prerequisites; Go/No-Go Entscheidung.
- Acceptance Criteria: Meeting stattgefunden, Entscheidung dokumentiert
- Verification: Meeting-Notes vorhanden

---

## 8. Next 3 Moves

```
1. Erstelle Test-Inventory-Baseline: pytest --collect-only > test_inventory.txt && kategorisiere nach unit/integration/e2e
2. Upgrade Postgres auf 16-alpine und Redis auf 7.4-alpine3.21 – Gordon-Prompt vorbereiten für Image-Pull und Compose-Update
3. Führe docker builder prune -f aus nach dem nächsten erfolgreichen Build (3.66 GB freigeben)
```

---

**Dokument-Ende**

*Erstellt von: Claude (IT-Chef)*  
*Freigabe durch: Jannek (Projektleiter)*  
*Nächstes Review: Nach E2E-Phase-1 Abschluss*
