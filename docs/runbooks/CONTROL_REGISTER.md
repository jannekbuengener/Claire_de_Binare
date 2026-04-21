# Control Register

**Letzte Aktualisierung:** 2026-04-21
**SSOT Live-Readiness:** `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
**Verdict:** NO-GO
**Control-Board Stage:** `trade-capable` (ratifiziert 2026-04-08 via Issue `#1492`)

---

## Cockpit-Einstieg

1. GitHub Issue `[CONTROL] Claire de Binare — Operatives Cockpit (dauerhaft offen)` — **#1445**
2. GitHub Issue `#1492` — ratifizierter Stage-Uebergang `stability -> trade-capable`
3. `CURRENT_STATUS.md` — Repo/Engineering-Status, Session-Ledger
4. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — Live-Readiness-Verdikt

---

## Aktueller Stage-Stand

- Board-/Projekt-Stage: `trade-capable`
- Ratifikation: 2026-04-08 via Issue `#1492`
- Guardrails bleiben unveraendert:
  - shadow/mock only
  - kein Live-Kapital
  - kein Grafana-Gate
  - keine Strategie-Validierung
  - `LR-050` bleibt `NO-GO`

---

## SSOT-Grenzen

| Quelle | Zuständigkeit |
|---|---|
| `docs/runbooks/CONTROL_REGISTER.md` | Control-Board-Cockpit, aktueller Stage-/Operating-Focus |
| `CURRENT_STATUS.md` | Repo-Stand, Session-Ledger, offene PRs |
| `LR-AUDIT-STATUS-2026-03-05.md` | Live-Readiness-Phasenstatus, Go/No-Go-Verdikt |
| `ACTIVE_ROADMAP.md` | Pointer auf beide SSoTs |

Regel: Phasen-Status nie in CURRENT_STATUS eintragen. LR-Verdikt nie aus einer Board-Stage ableiten. Board-Stage nie als implizites LR-GO lesen.

---

## Wiederkehrende Drift-Vektoren

| Drift-Typ | Prüfung | Kontext-Issues |
|---|---|---|
| Solo-Maintainer in SOPs | kein Mehrpersonen-Eskalationspfad in aktiven Docs | #1372 |
| Terminologie BLACK | Risk Service / cdb_risk statt BLACK | #1373, #1388 |
| Stack-Canon single-compose | compose.blue.yml + compose.red.yml | #1371 |
| Secrets-Canon | SECRETS_PATH / ~/Documents/.secrets/.cdb/ | #1411 |
| Runbook legacy stack_up | keine base+dev Referenz in aktiven Runbooks | #1410 |
| Discovery-Surfaces | ENTRYPOINTS.yaml / CHEATSHEET aktuell | #1413 |
| ARCHITECTURE_MAP | bei Service-Change nachziehen | #1409 |
| GitHub Actions UI Workflow-Count > Repo-Count | `state: active` in API ≠ ausführbar; gelöschte Dateien behalten historische Registrierung; platform-managed dynamic Workflows (Copilot/Dependabot/CodeQL) zählen zusätzlich; erwartet, kein Risiko | #1666 |

Kontext-Issue-Nummern sind historische Anker (alle CLOSED) — nicht als offene Aufgaben interpretieren.

---

## Governance-Anker

- **Human Gate GRANTED:** 2026-04-04
  Artefakt: `reports/p5_canary/2026-04-04/decision_record.yaml`
  Gilt für: P5 prestart only — kein Echtgeld-Trading ohne erneuten expliziten Gate

---

## Aktive Infra-Workflows

| Workflow | Trigger | Zweck |
|---|---|---|
| `weekly_digest.yml` | wöchentlich | Issue-/Status-Digest |
| `weekly_digest_failure_alert.yml` | nach `weekly_digest.yml` | Failure-Eskalation als `report:weekly-fail` Issue nur bei echtem Fehler |
| `cdb-weekly-control-hygiene-classifier.yml` | Mo/Do/Fr 07:30 UTC + manuell | Weekly hygiene/reconciliation fuer `#1445`; dedupe-sicherer Wochenkommentar, branch-obsolescence Klassifikation (repo-backed) und lokaler/manual worktree-cleanup handoff; optional max 0..2 enge Follow-up-Issues |
| `cdb-daily-delta-triage.yml` | Di/Mi/Fr/So 06:20 UTC + manuell | Daily fresh-delta triage fuer `#1445`; delta-only gegen letzten Daily-Marker, optional max 0..1 enges Follow-up-Issue |
| `cdb-backlog-curation.yml` | `issues.labeled` (qualifizierte Labels only) | Artifact-only Companion-Workflow fuer implementation-relevante Issues; erzeugt agent-readable JSON unter `artifacts/backlog-curation/issue-<number>.json`, ohne Labels/Kommentare/Issues zu mutieren |
| `cdb-backlog-anomaly-escalation.yml` | `workflow_run` (nach `cdb-backlog-curation`) + manuell | Separate Phase-1-Eskalationslane fuer starke typed backlog-curation Anomalien; klassifiziert fail-closed (`report_only` / `follow_up_issue` / `unclear`), blockiert sensitive/private Findings fuer public auto-issueing und emittiert dedupe-safe max 0..1 Follow-up-Issue |
| `governance-audit.yml` | manuell | Governance-Audit |
| `cdb-control-followup-classifier.yml` | manuell | Human-in-the-loop Klassifikation repo-backed Control-Findings |
| `cdb-post-merge-followup-scanner.yml` | bei gemergten PRs + manuell | Repo-backed Post-Merge-Scan fuer kleine Nachzugspakete; Kommentar nach `#1445` oder enges dedupe-sicheres Follow-up-Issue; `architecture_service_catalog_drift` wird unterdrueckt fuer digest-only Image-Pin-Aenderungen (semantischer Tag unveraendert, nur `@sha256`-Digest aktualisiert — PR #1729) |
| `gemini-scheduled-triage.yml` | manuell (geparkt fail-closed) | Gemini-Triage |
| `project_reconcile_daily.yml` | täglich | Board-Reconciliation |
| `control_board_upsert.yml` | Mo 02:30 UTC | GitHub Project #8 Upsert |

---

## Workflow-Control-Notizen

- `security-scan.yml`: Trivy-SARIF-Uploads muessen explizit stabile Kategorien verwenden (`trivy-base-*`, `trivy-custom-*`), damit Digest-/Tag-Bumps keine neuen Code-Scanning-Baselines aufspalten. Security-Triage und Dismiss-Cluster bleiben im `docs/security/TRIAGE_RUNBOOK.md` verankert.
- `security-scan.yml` (PR #1768): Redis-Digest-Refresh — `redis:7.4.8-alpine`-Digest in `trivy-scan-base`- und `scan-base-images`-Matrix aktualisiert (digest-only, semantischer Tag unveraendert). Trivy-SARIF-Kategorie `trivy-base-redis` bleibt stabil; kein neues Security-Triage-Item.
- `emoji-bot.yml`: Kommentarinhalt aus `issue_comment` bleibt untrusted Input und darf nur ueber `env`/kontrollierte Uebergaben in Shell- oder Python-Schritte fliessen. Der Workflow ist ein Operator-Helfer, keine Evidenz- oder Freigabe-Surface. Bekannte Residual-Haertung fuer multiline-Outputs an `$GITHUB_OUTPUT` bleibt separater Folgescope und wird hier nicht ueberdehnt.
- `.github/scripts/advanced-emoji-filter.py`: Emoji-Erkennung laeuft fail-closed primaer ueber `emoji.emoji_list(...)`; die frueheren breiten Unicode-Range-Regexe wurden im CodeQL-Nachzug aus PR #1757 entfernt. Der Script bleibt ein Operator-Helper fuer Kommentarhygiene; keine LR-/Freigabe-Evidenz ableiten.
- Workflow-Permissions aus PR #1749: `.github/workflows/stale.yml` nutzt explizit `issues: write` + `pull-requests: write`, `emoji-filter.yml` fuehrt top-level `contents: read` plus job-spezifisches `contents: write`, `emoji-bot.yml` setzt fuer `help-command` explizit `issues: write`, `gemini-dispatch.yml` bleibt mit `permissions: {}` fail-closed. Diese Grants sind eng auf den jeweiligen Automationszweck begrenzt.
- Action-Dependency-Bumps (PRs #1788, #1789, #1790, #1792, 2026-04-21): Vier Dependabot-Bumps ohne operative Control-Aenderung — `actions/cache` 5.0.4→5.0.5 (`trivy.yml`, PR #1788); `actions/upload-artifact` 4.6.2→7.0.1 (alle Artifact-produzierenden Workflows inkl. aller Control-Workflows, PR #1789, SHA-gepinnt auf den Commit zu v7.0.1); `github/codeql-action` 4.35.1→4.35.2 (`gitleaks.yml`, `security-scan.yml`, `trivy.yml`, PR #1790, SARIF-Kategorien und Security-Triage-Postur unveraendert); `docker/build-push-action` 6.18.0→7.1.0 (`docker-publish.yml`, PR #1792, kein Control-Workflow). Keine Aenderung an Artifact-Upload-Semantik, SARIF-Kategorien oder Control-Surface-Verhalten.
- `lr021_replay_smoke.yml` (PR #1834): Summary-Schritt semantisch geschaerft — `replay_execution_status` spiegelt den Workflow-/Pipeline-Pass, `gate_status` das fachliche Strategie-Gate; beide Werte sind nicht zu verwechseln und kein LR-/Live-Signal. Die gekoppelte Replay-Surface (Workflow-`workflow_dispatch` + Makefile-Target `replay-shadow-run`) wird fail-closed durch `tests/unit/scripts/test_lr021_replay_surface.py` abgesichert.

---

## Manuelle HITL-Klassifikation

- Workflow: `.github/workflows/cdb-control-followup-classifier.yml`
- Prompt-Canon: `.github/prompts/cdb-control-followup.prompt.yml`
- Ausführung: nur `workflow_dispatch`, kein Auto-Issueing, keine automatische Repo-Mutation
- Ausgabe: immer Step Summary + Artefakt; optional zusätzlicher Kommentar auf ein bewusst gesetztes Ziel-Issue
- Guardrail: fail-closed bei ungueltigem JSON, bei `summary_and_issue_comment` ohne `issue_number`, oder bei nicht numerischer `issue_number`

---

## Monatlicher Audit
Spätestens bis 3. des Monats → Audit-Kommentar in Issue #1445 anhängen.
Audit-Template: s. Issue #1445 Body.
