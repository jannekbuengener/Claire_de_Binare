# Session Log: 2026-04-17 — Issue #1730 Control Doc Reconciliation

## Auftrag

Issue #1730 bearbeiten: Reconcile control docs after PR #1729 workflow changes.
Anschliessend PR #1732 mergen und Queue post-merge neu triagieren.

## Ausgangslage

- PR #1729 gemerged: `fix(workflows): suppress digest-only architecture follow-up noise (#1726)`
- Scanner-Logik in `.github/scripts/post_merge_followup_scanner.py` geaendert
- Auto-Follow-up #1730 via `runbook_evidence_followup_drift` erzeugt
- Betroffen laut Issue: `post_merge_followup_scanner.py`, `docs/runbooks/CONTROL_REGISTER.md`

## Befund (real drift)

`docs/runbooks/CDB_POST_MERGE_FOLLOWUP_SCANNER.md`: Regel 1 (`architecture_service_catalog_drift`) enthielt keinen Hinweis auf die neue Suppression-Bedingung (digest-only Image-Pin, semantischer Tag unveraendert).

`docs/runbooks/CONTROL_REGISTER.md`: Scanner-Workflow-Zeile beschrieb kein Suppression-Verhalten.

`CURRENT_STATUS.md`: Kein Session-Ledger-Eintrag fuer PR #1729 vorhanden.

Navpack (`ENTRYPOINTS.yaml`, `CHEATSHEET.md`): kein Scanner-Bezug → kein Drift.

## Implementierung

Drei Dateien geaendert (docs-only):

| Datei | Aenderung |
|---|---|
| `docs/runbooks/CDB_POST_MERGE_FOLLOWUP_SCANNER.md` | Suppression-Note zu Regel 1 ergaenzt |
| `docs/runbooks/CONTROL_REGISTER.md` | Suppression-Hinweis + PR-Ref in Scanner-Zeile; `Letzte Aktualisierung` auf 2026-04-17 |
| `CURRENT_STATUS.md` | Session-Ledger-Eintrag fuer PR #1729 ergaenzt; Header-Daten auf 2026-04-17 |

## Branch-Kontamination (Zwischenproblem)

Erster Branch (`docs/1730-reconcile-control-docs-after-1729`) enthielt PR #1729-Commits (lokales main war hinter origin/main).
Policy Gate klassifizierte PR #1731 als `core/service` wegen `.github/scripts/*.py`.
Fix: `git cherry-pick` des Docs-Commits auf frischen Branch `docs/1730-reconcile-v2` von `origin/main`.
PR #1731 geschlossen, PR #1732 eroeffnet.

## PR #1732

- Alle 9 Checks gruen (Policy Gate, CI, Docs Conflict Guard, lr021-replay-smoke, etc.)
- Copilot Review Thread (CURRENT_STATUS.md Datum-Strings) resolved nach Minimal-Fix
- Squash-merged als `55de6984`
- Issue #1730 via `Closes #1730` im PR-Body geschlossen

## Post-Merge Queue (2026-04-17)

Offene PRs: keine.
Neues Auto-Follow-up vom Scanner fuer #1732: keines (docs-only PR, erwartetes Verhalten).

Offene Issues (aktiv, nicht geparkt):
- #1718 — [SECURITY][TRIVY] Redis CVE-2026-22184 (upstream-blocked, prio:must)
- #1725 — [SECURITY][TRIVY] OpenSSL CVEs auf cdb_execution + cdb_signal (prio:should)
- #1727 — Weekly hygiene: Branch-Deletion 408-contract-precommit-hook (manual-approval)
- #1636 — [VALIDATION] primary_breakout_v1 Evidence/Evaluation-Luecken (prio:should)
- #1645 — [HARDENING][GIT] Git/Worktree-State + Branch-Sprawl (prio:must)
- #1649 — [SECURITY][EPIC] Code-Scanning Konsolidierung (prio:must)

## Status

**erledigt** — Issue #1730 geschlossen, PR #1732 gemerged, Queue triagiert.
