# Session Log — 2026-04-07 — Batch: Drift / Canon / SSOT / Secrets

**Branch:** `docs/status-session-40`
**PR:** #1485 (OPEN, noch nicht gemergt)
**Status am Session-Ende:** merge-ready, CI ausstehend

---

## Issues abgearbeitet

### #1481 — docs(lr): reconcile LR-AUDIT-STATUS with tracker state
- Commit: `3db1993f`
- LR-050 / P5 Status: `OPEN` → `NO-GO` an 3 Stellen in LR-AUDIT-STATUS
- Section D: `OPEN / Next Tasks` → `Conservative Holds / Next Tasks`
- GO_NO_GO.md: #780 LR-011 → `CLOSED` (PR #1106)
- Reconciliation-Datum: 2026-04-07

### #1482 — dr: reconcile backup/restore canon
- Commit: `2da6e6b1`
- DR README + QUICK_START: Backup-Scope auf Postgres + Redis + optional SurrealDB
- `make backup-health` nicht mehr als Restore-Verifikationsschritt
- Historische Scripts (create_backup.ps1, restore_volumes.ps1, verify_restore.ps1): Banner
- PR #1396: bereits CLOSED (superseded by #1470)
- PR #1397: geschlossen mit Dispositionskommentar

### #1483 — infra: enforce-root-baseline.ps1 repo-relativ
- Commit: `931fe1b9`
- `WorkingRepoPath` Default: `D:\Dev\...` → `$PSScriptRoot/..` via Resolve-Path
- Legacy-Pattern: `D:\\Dev\\...\\Claire_de_Binare_Docs` → `[A-Za-z]:\\.*Claire_de_Binare_Docs`
- DryRun validiert: Repo-Root, externer CWD, Override — alle PASS

### #1484 — infra(secrets): harden compose canon
- Commit: `43badaef`
- compose.blue.yml + compose.red.yml: `:-C:/Users/janne/...` → `:?SECRETS_PATH must be set`
- setup_blue_red.ps1: SECRETS_PATH-Guard + Smoke-Test-Fix
- bootstrap_local.ps1: SECRETS_PATH-Guard vor docker compose
- Makefile docker-up (Linux + Windows): SECRETS_PATH-Default + Fail-Closed
- Negativtest: `EXIT:1` + klare Meldung wenn SECRETS_PATH fehlt

---

## Offene Punkte

### PR #1485 Merge-Status
- Branch ist up-to-date mit origin
- CI noch nicht durchgelaufen (kurz nach Push)
- Bot-Review-Threads (Sourcery, Copilot) müssen nach CI resolved werden
- PR-Titel noch `docs(lr): reconcile LR-AUDIT-STATUS...` (aus erstem Commit) — für Batch unschön, aber nicht blockierend

### Potenzielle Folge-Issues
- **`tools/cdb.ps1` + SECRETS_PATH**: Kanonischer Windows-Front-Door nicht geprüft
  - Voraufklärung wurde im letzten Teil der Session gestartet, aber durch User-Interrupt abgebrochen
  - Nicht in #1485 enthalten
  - Falls `cdb.ps1` SECRETS_PATH nicht setzt, fällt es jetzt fail-closed durch (korrekt, aber evtl. Convenience-Issue für nächsten Session)

---

## Nächste Session: Was zu tun ist

**Priorität 1:** PR #1485 CI-Status prüfen
- `gh pr checks 1485 --repo jannekbuengener/Claire_de_Binare`
- Bot-Threads resolven falls vorhanden
- Merge ausführen

**Priorität 2:** tools/cdb.ps1 SECRETS_PATH prüfen
- Datei lesen: `tools/cdb.ps1`
- Prüfen ob `SECRETS_PATH` gesetzt oder vorausgesetzt wird vor `docker compose` Aufrufen
- Falls Lücke: kleines Issue anlegen (Titel ca. `infra(secrets): ensure cdb.ps1 sets SECRETS_PATH before compose invocations`)
- Falls kein Problem: Issue-Kommentar in #1484 mit "cdb.ps1 geprüft, kein Follow-up nötig"

**Priorität 3:** CURRENT_STATUS.md nach Merge aktualisieren (Session-Ledger-Eintrag)

---

## Dateien geändert in PR #1485

- `CURRENT_STATUS.md` (Session-40-Entry)
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- `docs/live-readiness/GO_NO_GO.md`
- `knowledge/operations/disaster_recovery/README.md`
- `knowledge/operations/disaster_recovery/QUICK_START.md`
- `knowledge/operations/disaster_recovery/create_backup.ps1`
- `knowledge/operations/disaster_recovery/restore_volumes.ps1`
- `knowledge/operations/disaster_recovery/verify_restore.ps1`
- `tools/enforce-root-baseline.ps1`
- `infrastructure/compose/compose.blue.yml`
- `infrastructure/compose/compose.red.yml`
- `infrastructure/scripts/setup_blue_red.ps1`
- `infrastructure/scripts/bootstrap_local.ps1`
- `Makefile`
