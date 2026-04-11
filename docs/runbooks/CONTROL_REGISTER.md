# Control Register

**Letzte Aktualisierung:** 2026-04-11
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
| `governance-audit.yml` | manuell | Governance-Audit |
| `cdb-control-followup-classifier.yml` | manuell | Human-in-the-loop Klassifikation repo-backed Control-Findings |
| `cdb-post-merge-followup-scanner.yml` | bei gemergten PRs + manuell | Repo-backed Post-Merge-Scan fuer kleine Nachzugspakete; Kommentar nach `#1445` oder enges dedupe-sicheres Follow-up-Issue |
| `gemini-scheduled-triage.yml` | manuell (geparkt fail-closed) | Gemini-Triage |
| `project_reconcile_daily.yml` | täglich | Board-Reconciliation |
| `control_board_upsert.yml` | Mo 02:30 UTC | GitHub Project #8 Upsert |

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
