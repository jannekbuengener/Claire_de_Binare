# Session: CI SSOT Freeze + Governance Deltas
**Datum:** 2026-04-07  
**Branch:** local/ci-ssot-freeze-docs, local/ci-yaml-legacy-freeze (neue PRs); local/setup-python-6 (Ausgangs-Branch)

---

## Was wurde getan

### #1474 — ci.yaml explicit freeze (patch)
- `.github/workflows/ci.yaml`: Header um 2 LEGACY-FREEZE Kommentarzeilen erweitert
- `docs/runbooks/merge_policy_ci_gate.md`: Sektion `ci.yaml Freeze-Status` hinzugefügt
- `docs/ci/index.md`: ci.yaml-Beschreibung auf intentional frozen aktualisiert
- PRs erstellt: #1475 (docs-only), #1476 (workflows-only)

### #1462 — Dependabot Override Path (patch)
- `docs/runbooks/merge_policy_ci_gate.md`: Sektion `Dependabot / Bot PRs` hinzugefügt
- `.github/LABELS.md`: Hinweis unter `dependencies` dass kein Gate-Override
- Beide in PR #1475 enthalten (docs-only auto-inferred)

### #1463 — github-script Node.js reconcile (read-only)
- Alle 15 Workflows bereits auf `ed597411 # v8.0.0` — kein Altstand belegt
- Kein `##[warning]` Deprecation-Node in policy-gate-Run 2026-04-07
- Einstufung: stale-verdächtig
- Issue-Kommentar gepostet mit expliziter Residual-Unsicherheit (Node.js-Version von v8-Hash nicht aus Repo bestimmbar)

### #1471 — mcp_runtime setup-python v6 verify (reconcile)
- Run `24064060122` vom 2026-04-07T04:19:48Z gelesen
- Runner: `cdb-docker-runner-1`, Version `2.333.1`; Setup Python ✅; alle Steps grün
- Einstufung: operationally resolved
- Issue-Kommentar mit konkreten Evidenzankern gepostet

### #1472 — pre-close Governance-Entscheidung (comment only)
- Entscheidung: manual-only ist intentional
- `agents/roles/CLAUDE.md` Zeile 95 ist ausreichend — kein Repo-Patch
- Issue-Kommentar mit Begründung gepostet

### #1473 — Backup Drill-Vorbereitung (read-only)
- `backup_all.ps1`, `backup_health_check.ps1`, `restore_all.ps1` gelesen
- Reibungspunkte dokumentiert:
  - `make restore` listet nur, kein interaktiver Restore-Flow
  - `restore_all.ps1` stoppt Container während Restore (destruktiv für laufenden Stack)
  - `backup_health_check.ps1` Default MaxAgeHours=2 — FAIL bei täglichem Backup-Rhythmus
- Kein Restore auf produktivem Stack (paper_runner aktiv)
- Issue-Kommentar mit Drill-Vorbereitung und klarem nächstem Schritt gepostet

---

## Was wurde bewusst NICHT getan
- Keine Workflow-Logik geändert (policy-gate.yml, labels.json unberührt)
- Kein Restore-Vollzug (#1473)
- Kein Repo-Patch für #1463 (stale-verdächtig, kein Altstand belegt)
- Kein Repo-Patch für #1471 (nur Evidenz-Kommentar)
- Kein Repo-Patch für #1472 (Governance-Entscheidung per Kommentar)
- Keine CI-Erzwingung für pre-close

---

## Offene Punkte
- #1463: Externe Verifikation ob `ed597411` Node.js 24 nutzt (actions/github-script Changelog)
- #1473: Nächster Drill nur nach expliziter Freigabe + gestopptem Stack
- PRs #1475, #1476: Bot-Threads resolven vor Merge (Sourcery, Copilot)

---

## PRs dieser Session
- #1475: docs(ci) explicit freeze + Dependabot override path — docs-only
- #1476: [workflows-only] ci(legacy) mark ci.yaml as intentional freeze
