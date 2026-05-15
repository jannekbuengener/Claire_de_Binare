# Security Alert Triage Runbook

> Epic: #1649 | Issue: #1654
> Scope: Trivy, Gitleaks, CodeQL
> Ziel: Security-Backlog klein, relevant und umsetzbar halten.

---

## 1. Scanner-Übersicht

| Scanner | Workflow | Trigger | SARIF-Upload |
|---------|----------|---------|-------------|
| **Trivy FS** | `trivy.yml` | Push (services/, infrastructure/), weekly | Ja |
| **Trivy Image** | `security-scan.yml` | Push, weekly Monday | Ja |
| **Gitleaks** | `gitleaks.yml` | Push main, weekly Sunday | Ja |
| **CodeQL** | `codeql-python.yml` (custom) | Push main, PR, weekly | Ja (auto) |

---

## 2. Triage-Entscheidungslogik

Jeder neue Alert wird in **eine** der vier Klassen eingeordnet:

| Klasse | Kriterium | Aktion |
|--------|-----------|--------|
| **Echter Fix** | Vulnerability in produktivem Code/Dependency; CVE hat Fix verfügbar | Fix-Issue erstellen, PR erstellen |
| **Historischer Noise** | Alert aus non-produktivem Pfad (artifacts/, logs/, reports/, tmp/, governance_work/); oder aus Commit-History ohne aktiven Code | Dismiss mit Cluster-Kommentar (siehe §4) |
| **False Positive** | Pattern-Match ohne tatsächliches Risiko (Platzhalter, Test-Fixture, Env-Var-Referenz) | Dismiss + allowlist/ignore-Eintrag ergänzen |
| **Needs Review** | Unklare Quelle, unklares Risiko, kein Fix verfügbar | Tracking-Issue erstellen, Severity dokumentieren |

---

## 3. Priorisierung nach Severity

| Severity | Zeitrahmen | Verantwortung |
|----------|-----------|---------------|
| **CRITICAL** | Sichten innerhalb 48h | Lead-Maintainer |
| **HIGH** | Bündeln pro Sprint/Batch | Lead-Maintainer |
| **MEDIUM** | Quartalsweise Batch-Review | Maintainer |
| **LOW / INFO** | Nur bei konkretem Anlass | Optional |

---

## 4. Standardisierte Dismiss-Kommentare

**Format:**
```
Cluster: <CLUSTER_NAME>
Rationale: <Begründung in 1-2 Sätzen>
Scope: <betroffener Pfad/Kontext>
Reviewed: <YYYY-MM-DD> | Issue: #<NUMMER>
```

**Vorlagen:**

### Cluster: non-prod-path
```
Cluster: non-prod-path
Rationale: Finding in non-produktivem Verzeichnis (artifacts/, logs/, reports/, governance_work/, tmp/).
Kein Produktiv-Code betroffen; keine exploitierbare Angriffsfläche.
Scope: artifacts/ | Reviewed: YYYY-MM-DD | Issue: #1651
```

### Cluster: gosu-base-image
```
Cluster: gosu-base-image
Rationale: Go stdlib CVEs in gosu-Binary der Redis/Postgres-Basisimages.
Startup-only Binary ohne Netzwerk-Exposition. Upstream-Tracking aktiv (docker-library/{redis,postgres}).
Dokumentiert in: docs/security/TRIAGE_RUNBOOK.md (§5) | Reviewed: YYYY-MM-DD | Issue: #1651
```

### Cluster: test-fixture-secret
```
Cluster: test-fixture-secret
Rationale: Pattern-Match in Test-Fixture oder Beispieldatei.
Kein echtes Secret; Pattern ist Platzhalter/synthetisch.
Scope: tests/ | Reviewed: YYYY-MM-DD | Issue: #1653
```

### Cluster: historic-commit
```
Cluster: historic-commit
Rationale: Historischer Fund in altem Commit, betroffene Datei existiert nicht mehr oder wurde bereinigt.
Kein aktives Risiko im aktuellen Repo-Stand.
Commit: <SHA> | Reviewed: YYYY-MM-DD | Issue: #1653
```

---

## 5. Trivy Alert-Cluster-Strategie (#1651)

### Alert-Export
```bash
gh api --paginate \
  '/repos/{owner}/{repo}/code-scanning/alerts?tool_name=Trivy&state=open&per_page=100' \
  | jq '.[] | {rule: .rule.id, path: .most_recent_instance.location.path, severity: .rule.severity}' \
  > trivy-alerts-export.json
```

### Cluster-Bildung
Gruppierung nach:
1. **Pfad-Präfix** — Welche Top-Level-Dir? (`artifacts/`, `services/`, etc.)
2. **Regel/CVE** — Welches CVE / welche Regel?
3. **Paket** — Welches Python-Paket / Base-Image-Komponente?

### Entscheidungsmatrix Trivy
| Pfad | Klasse | Aktion |
|------|--------|--------|
| `services/*/requirements.txt` CVE ohne Fix | Needs Review | Issue erstellen |
| `services/*/requirements.txt` CVE mit Fix | Echter Fix | Update Dependency |
| Non-prod Pfad (artifacts/, logs/ etc.) | Historischer Noise | Dismiss + Kommentar |
| Base image gosu | Historischer Noise | Dismiss + Kommentar (→ Cluster: gosu-base-image, §4) |
| `.trivyignore`-würdiger unfixbarer CVE | False Positive | `.trivyignore`-Eintrag + Kommentar |

### Stop-Regel
**Kein Bulk-Dismiss ohne Cluster-Nachweis.** Jeder Dismiss-Batch muss:
1. eine dokumentierte Cluster-Zuordnung haben
2. einen standardisierten Kommentar tragen
3. auf dieses Runbook oder ein konkretes Issue verlinken

---

## 6. Gitleaks Secret-Handling (#1653)

### Echter Secret-Fund (unbekanntes aktives Credential)
1. **Sofort rotieren/revoken** — nicht auf Fix warten
2. GitHub-Secret-Scanning Alert schließen (nach Rotation)
3. In `.gitleaksignore` eintragen mit SHA + Kommentar
4. Incident dokumentieren (intern, kein öffentliches Issue)

### Artefakt-/Report-Fund
1. Prüfen ob Datei noch im aktuellen Checkout existiert
2. Wenn Pfad in `gitleaks.toml` Allowlist: Allowlist-Eintrag prüfen/ergänzen
3. Wenn historischer Commit: `.gitleaksignore`-Eintrag mit SHA
4. Dismiss mit Kommentar `Cluster: non-prod-path` oder `Cluster: historic-commit`

---

## 7. Triage-Kadenz

| Ereignis | Wann | Aktion |
|----------|------|--------|
| Neuer CRITICAL Alert | Sofort (GitHub-Notification) | Triage nach §2 |
| Weekly Scanner-Run | Montag/Dienstag | Neue Alerts sichten, clustern |
| Sprint-Start | Alle 2 Wochen | HIGH-Alerts bündeln, Batch-Fix |
| Quartals-Review | Alle 3 Monate | Scanner-Config review, `.trivyignore` aufräumen |

---

## 8. Ownership

| Scanner | Primary Owner | Eskalation |
|---------|--------------|-----------|
| Trivy | Lead-Maintainer | — |
| Gitleaks | Lead-Maintainer | Sofort bei echtem Secret |
| CodeQL | Lead-Maintainer | — |

---

## 9. Automated Readout Workflow (#2289)

### Zweck

Das Workflow `.github/workflows/security-alert-readout.yml` läuft automatisch
**Mo / Mi / Fr um 06:15 UTC** und kann jederzeit manuell ausgelöst werden.  
Es kombiniert zwei Read-only-Skripte:

| Skript | Zweck |
|--------|-------|
| `scripts/audit/github_security_quality_readout.py` | Fetcht Code Scanning, Dependabot, Secret Scanning (aggregiert) via `gh api`; schreibt JSON + Markdown nach `docs/security/readouts/YYYY-MM-DD/`. |
| `scripts/audit/security_alert_delta.py` | Vergleicht das aktuelle Readout-JSON mit dem letzten vorhandenen; emittiert Delta-JSON + Markdown. |

### Publish-Modus (artifacts-only + optionale PR-Persistenz)

Der Workflow operiert standardmäßig im **Artifacts-only-Modus** (`dry_run`).
Kein direkter Commit, kein Push in `main`.

Optional kann via `workflow_dispatch` mit `persist_via_pr=true` ein Branch + PR erstellt werden,
der den Readout in den Repo persistiert. Kein Auto-Merge. Kein Direct Push auf `main`.

| Modus | Wann | Wirkung |
|-------|------|---------|
| `dry_run` | Schedule (Standard) + manuell wählbar | Artifact + Job-Summary; kein Commit, kein Push. |
| ~~`publish`~~ | ~~Manuell via `workflow_dispatch`~~ | **Entfernt** — Direct-Push auf `main` ist nicht governance-kompatibel (GH006: Branch Protection). |
| `persist_via_pr=true` | Manuell via `workflow_dispatch` | Branch `chore/security-readout/YYYY-MM-DD` + PR gegen `main`; kein Auto-Merge; Human-Review erforderlich. |

**Hintergrund:** Manueller Run `25632071704` (2026-05-10) scheiterte bei Schritt
`Commit readout to repository` mit GH006 — geschützter Branch verlangt PR-Weg.
Der Direct-Push-Pfad wurde in `fix/security-readout-disable-direct-publish-2289`
entfernt.

**Validierter Dry-Run:** Run `25632038888` (2026-05-10, `main@f227aa42`) —
erfolgreich; 3 Artefakte, Schema `security_alert_delta.v1`, PARTIAL korrekt
behandelt, kein Secret-Payload, kein Repo-Write, 6 High-Eskalationen.

### PR-basierter Persistenzpfad (`persist_via_pr`)

Auslösung:

```
workflow_dispatch → persist_via_pr = true
```

Ablauf:

1. `security-readout`-Job läuft vollständig (Readout + Delta + Artifacts).
2. `persist-via-pr`-Job (job-level `contents: write, pull-requests: write`) startet danach.
3. Dedupe-Check: Falls ein offener PR für `chore/security-readout/YYYY-MM-DD` bereits
   existiert, wird übersprungen (kein PR-Spam).
4. Branch `chore/security-readout/YYYY-MM-DD` wird von `main` abgezweigt.
5. Readout-JSON + Markdown werden committed (`[skip ci]`).
6. Branch wird gepusht; PR wird via `gh pr create` eröffnet.

PR-Eigenschaften:

| Eigenschaft | Wert |
|---|---|
| Branch | `chore/security-readout/YYYY-MM-DD` |
| Titel | `chore(security): persist alert readout YYYY-MM-DD` |
| Base | `main` |
| Auto-Merge | nein |
| Direct Push | nein |
| Issue-Close | nein |
| Alert-Dismissal | nein |

Permissions sind nur job-scoped und nur aktiv, wenn `persist_via_pr=true` gesetzt ist.
Der `security-readout`-Job bleibt unverändert `contents: read`.

### Epic-Ledger-Kommentar auf #2289 (Status/Audit, kein Remediation-Automatismus)

Nach **jedem** Workflow-Run (Schedule + manuell) wird ein kompakter Ergebnis-Kommentar
auf GitHub Issue **#2289** gepostet.

- Zweck: Audit-/Ledger-Signal (Run-Metadaten + Status + Artefaktpfade), nicht Remediation.
- Dedupe-Marker pro Run: `<!-- cdb-security-alert-readout-run:${{ github.run_id }} -->`
- Sicherheitsgrenzen:
  - keine neuen Issues
  - keine Alert-Dismissals
  - kein Auto-Merge
  - Secret Scanning bleibt redacted/status-only
  - keine LR-/Live-/Echtgeld-Ableitung

Permissions:
- Top-Level bleibt read-only (`contents: read`, `security-events: read`).
- `issues: write` wird **nur** im separaten Job `comment-epic` verwendet.

### Eskalationslogik

- `security_alert_delta.py` gibt **Exit-Code 2** zurück, wenn neue offene Alerts mit Severity `critical`, `high` oder `error` (CodeQL) gefunden werden.
- Der Workflow setzt dann eine `::warning::`-Annotation und dokumentiert die Eskalation im Job-Summary.
- Aktuell kein automatisches Issue-Öffnen (DRY-RUN-Slice; Issue-Automation folgt in einem separaten PR).

### Secret Scanning

- Die Readout-Skripte rufen die Secret-Scanning-API **absichtlich nicht** auf.  
  Surface-Status in JSON ist immer `"status": "redacted"`.
- Das Delta-Skript vergleicht ausschließlich den Surface-Status (ok/redacted), niemals Payload-Felder.

### Artefakte

Nach jedem Run werden hochgeladen:

```
docs/security/readouts/YYYY-MM-DD/
  github_security_quality_readout.json   # machine-readable readout (schema v1)
  github_security_quality_summary.md     # human-readable Markdown

artifacts/security-alert-readout/delta/
  security_alert_delta.json              # delta schema (security_alert_delta.v1)
```

Die Delta-Ausgabe ist absichtlich JSON-only. Keine Markdown-Zusammenfassung und
keine stdout-Summary aus dem Delta-Skript.

Alle Artefakte werden als GitHub-Actions-Artifacts hochgeladen (30 Tage Retention).
Kein direkter Commit in das Repository (artifacts-only-Modus, siehe Publish-Modus-Tabelle oben).

### Interpretation eines Readout-Reports

1. **Status** `PASS` — alle drei Surfaces gelesen (Secret Scanning: nur Status).
2. **Status** `PARTIAL` — mindestens eine Surface nicht lesbar (Permission/API-Fehler).
3. **`escalation_needed: true`** im Delta → neuen High/Critical-Alert innerhalb des
   nächsten Sprints triagen (§3).
4. **`new_groups`** im Delta → neue Regel-/Advisory-Cluster; ggf. Dismiss-Kommentar
   nach §4 vorbereiten oder Batch-Fix planen.

---

## 10. Issue Automation — Neue Alert-Gruppen (#2289)

### Zweck

Der `issue-automation`-Job in `.github/workflows/security-alert-readout.yml` liest
`security_alert_delta.json` und erstellt pro neuer, eskalationsrelevanter Alert-Gruppe
genau ein GitHub-Issue.  Er läuft nach dem `security-readout`-Job und ist fail-closed:
ein Fehler beim Dedupe-Check verhindert die Erstellung (kein stillen Fehlern).

### Invarianten

- **Kein Auto-Close.** Einmal erstellte Issues werden nur durch menschliche Triage
  geschlossen.
- **Keine Alert-Dismissals** durch den Automation-Layer.
- **Keine LR-/Live-/Echtgeld-Ableitung.**
- **Secret-Scanning** wird im `security_alert_issue_candidates.py`-Layer gefiltert
  und nie automatisiert als Issue angelegt.
- **`comparison_skipped`-Quellen** (z. B. Dependabot ohne Token) werden im
  Automation-Layer gefiltert — keine Issue-Erstellung für PARTIAL-Sources.

### Eskalationsschwelle

Nur Kandidaten mit `severity_band == "high"` (deckt `critical`, `high`, `error` ab)
werden zu Issue-Kandidaten.  `medium`, `low`, `note`, `unknown` werden übersprungen.

### Dedupe-Mechanismus

Jedes Issue enthält einen HTML-Kommentar als Dedupe-Marker:

```
<!-- cdb-security-alert-group:<fingerprint> -->
```

Der Fingerprint ist ein SHA-256[:16] der kanonisierten Felder
`source|severity_band|subject|affected_component|branch`.

Vor jeder Issue-Erstellung prüft das Skript per GitHub-GraphQL-Suche, ob ein
Issue mit diesem Marker bereits existiert.  Bei Lookup-Fehler: fail-closed (kein
Create, Exit 2).

**Hinweis:** GitHub-Suche ist eventually consistent (Indexierungs-Lag möglich).
Der Marker ist primäre Dedupe-Wahrheit; die Suche ist ein Best-Effort-Guard.

### Dry-run vs. Live-Modus

| Trigger | Modus |
|---------|-------|
| `schedule` | immer dry-run — kein Issue-Spam auf geplanten Runs |
| `workflow_dispatch` ohne `issue_automation_live=true` | dry-run |
| `workflow_dispatch` mit `issue_automation_live=true` | live — erstellt echte Issues |

Im Dry-run werden alle Candidates geloggt (`DRY-RUN: would create issue: …`),
aber keine GitHub-Writes durchgeführt.

### CLI-Referenz

```bash
# Dry-run (default)
python3 scripts/audit/security_issue_automation.py \
  --delta-json artifacts/security-alert-readout/delta/security_alert_delta.json \
  --repo owner/repo

# Live-Modus (nur bewusst aktivieren)
python3 scripts/audit/security_issue_automation.py \
  --delta-json artifacts/security-alert-readout/delta/security_alert_delta.json \
  --repo owner/repo \
  --live-mode
```

### Exit-Codes

| Code | Bedeutung |
|------|-----------|
| `0` | ok — alle Candidates verarbeitet (erstellt oder übersprungen) |
| `1` | Input-Fehler — Delta-JSON fehlt oder ungültig |
| `2` | Partial-Failure — mindestens eine Issue-Erstellung oder ein Dedupe-Lookup fehlgeschlagen |

### Verknüpfte Skripte

- `scripts/audit/security_issue_automation.py` — CLI, Automation-Loop, GitHub-Writes
- `scripts/audit/security_alert_issue_candidates.py` — Kandidatengenerierung (kein GitHub-API)

### Stop-Regeln für manuellen Betrieb

- Bei `exit 2`: Logs prüfen, betroffene Fingerprints identifizieren, manuell nacharbeiten.
- Nie `--live-mode` auf geplanten Runs aktivieren — Workflow-Guard verhindert das, aber
  auch manuell nicht umgehen.
- Kein Commit der Ausgaben; das Skript schreibt keine Dateien.

---

## Verknüpfte Issues

- #1649 — [EPIC] Code-Scanning konsolidieren
- #1650 — Trivy Scan-Scope reduzieren
- #1651 — Historische Trivy-Noise-Cluster triage
- #1652 — CodeQL Klartext-Log-Fix
- #1653 — Gitleaks Secret-Scanning schärfen
- #1654 — Dieses Runbook
- #2289 — [EPIC] Security Alert Monitoring (Automated Readout)
