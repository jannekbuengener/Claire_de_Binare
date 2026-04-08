# Control Register

**Letzte Aktualisierung:** 2026-04-06
**SSOT Live-Readiness:** `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
**Verdict:** NO-GO

---

## Cockpit-Einstieg

1. GitHub Issue `[CONTROL] Claire de Binare — Operatives Cockpit (dauerhaft offen)` — **#1445**
2. `CURRENT_STATUS.md` — Repo/Engineering-Status, Session-Ledger
3. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — Live-Readiness-Verdikt

---

## SSOT-Grenzen

| Quelle | Zuständigkeit |
|---|---|
| `CURRENT_STATUS.md` | Repo-Stand, Session-Ledger, offene PRs |
| `LR-AUDIT-STATUS-2026-03-05.md` | Live-Readiness-Phasenstatus, Go/No-Go-Verdikt |
| `ACTIVE_ROADMAP.md` | Pointer auf beide SSoTs |

Regel: Phasen-Status nie in CURRENT_STATUS eintragen. Verdikt nie aus CURRENT_STATUS ableiten.

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
| `governance-audit.yml` | manuell | Governance-Audit |
| `gemini-scheduled-triage.yml` | geplant | Gemini-Triage |
| `project_reconcile_daily.yml` | täglich | Board-Reconciliation |
| `control_board_upsert.yml` | Mo 02:30 UTC | GitHub Project #8 Upsert |

---

## Monatlicher Audit
Spätestens bis 3. des Monats → Audit-Kommentar in Issue #1445 anhängen.
Audit-Template: s. Issue #1445 Body.
