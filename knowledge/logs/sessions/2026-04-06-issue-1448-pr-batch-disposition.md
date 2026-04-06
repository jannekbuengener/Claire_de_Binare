# Session 35 — Issue #1448: PR-Batch Disposition (#1392–#1397, #1446)

**Datum:** 2026-04-06
**Issue:** #1448 — stability: resolve control PR backlog and merge-decision drift
**Branch:** chore/session-35-close

---

## Ziel

Saubere Disposition des offenen PR-Batches #1446 und #1392–#1397 gegen aktuelles `main`.

---

## Erledigte Arbeit

### Verifikation

- Drift auf `main` direkt verifiziert durch Lesen der Zieldateien:
  - `knowledge/operating_rules/HITL_RUNBOOK.md`: 3-Stufen-Eskalation (Stufe 1/2/3) noch vorhanden → #1392 real offen
  - `knowledge/roadmap/M7_TESTNET_PLAN.md`: "Active Refinement" + Multi-Team-Sprache → #1394 real offen
  - `knowledge/roadmap/M8_SECURITY_PLAN.md`: "Active Refinement" + Security-Lead/pentest → #1395 real offen
  - `knowledge/ACTIVE_ROADMAP.md`: `knowledge/roadmap/` ohne HISTORICAL-Marker → #1393 real offen
  - `docs/runbooks/CONTROL_REGISTER.md`: existierte nicht → #1446/#1454 real nötig
- Mergeability aller PRs: #1392–#1396 BEHIND/MERGEABLE, #1446 DIRTY/CONFLICTING

### Merges

- #1392 `fix(ops): align HITL runbook escalation to solo-maintainer reality` → MERGED (0a4ac9ea)
- #1393 `docs(knowledge): frame historical M7/M8/M9 milestones in entrypoints` → MERGED (132eafe7)
- #1394 `docs(roadmap): frame M7 testnet plan as historical` → MERGED (7b40c0ca)
- #1395 `docs(roadmap): frame M8 security plan as historical` → MERGED (b583e0a2)
- #1454 `docs(control): add CONTROL_REGISTER.md` (narrowed successor zu #1446) → MERGED (c3e5b6da)

Technischer Ablauf pro PR:
- `gh pr update-branch` (strict: true — BEHIND blockiert auto-merge)
- 11 Copilot-Review-Threads via GraphQL resolved (required_conversation_resolution: true)
- auto-merge aktiv für #1392/#1393; für #1394/#1395 aktiviert via `gh pr merge --auto --squash`

### #1446 Narrowing

- PR #1446 war CONFLICTING: Branch `chore/session-32-33-close` enthielt stale CURRENT_STATUS.md-Konflikte + Session-Log-Artefakte
- CONTROL_REGISTER.md-Inhalt aus Branch gelesen (`git show origin/chore/session-32-33-close:...`)
- Neuer Branch `docs/1446-control-register` von `main` erstellt
- Nur `docs/runbooks/CONTROL_REGISTER.md` committed + gepusht
- PR #1454 erstellt + auto-merged
- PR #1446 geschlossen (superseded)

### Holds

- **#1396** `docs(dr): replace host-specific paths in DR docs` — HOLD
  - Blocker: `knowledge/operations/disaster_recovery/RESTORE_GUIDE.md` enthält snapshot-spezifischen Kontext (2025-12-31); PR generalisiert auf `<BACKUP_DIR>`, aber Abbildung auf aktuellen Front-Door-Canon (`F:\Claire_Backups`, `make backup`) nicht verifiziert
  - Action: DR-Docs gegen aktuellen Backup-Canon prüfen, dann Entscheidung

- **#1397** `fix(dr): replace hardcoded host paths in DR helper scripts` — HOLD / policy-blocked
  - Blocker: policy-gate FAIL (PowerShell-Scripts kategorisiert als core/service-Änderung, Label fehlt)
  - RCA gehört zu #1449; keine Untersuchung in dieser Session

---

## Ergebnis

- main bei `7b40c0ca` — 5 PRs sauber gemergt
- `docs/runbooks/CONTROL_REGISTER.md` auf main (SSOT für Control-System-Register)
- #1396 und #1397 mit explizitem Blocker gehalten
- Dispositionskommentar in #1448 gepostet

---

## Restunsicherheiten

- HITL_RUNBOOK.md nach #1392: Copilot hatte Wording-Inkonsistenz gemeldet (residuales "Genehmigung"-Sprache neben der neuen Solo-Maintainer-Sektion) — threads resolved, kein Follow-up-Issue angelegt
- #1396: unklar ob `<BACKUP_DIR>`-Generalisierung ausreichend ist oder ob `F:\Claire_Backups` explizit referenziert werden muss
