# Session Log — 2026-04-06 — Issue #1391 / PR #1398 compose canon drift close

## Kontext

- Issue: #1391 — compose canon drift in active PS1 scripts
- PR: #1398 — `fix(scripts): reconcile compose canon drift in active PS1 scripts`
- Ziel: PR vollstaendig merge-ready machen und mergen

## Was getan wurde

Read-only Review bestaetigte: PR hatte nur `infrastructure/scripts/` repariert; `scripts/*` root copies und aktive Docs blieben stale.

Plan erstellt (zweifach tightened): fail-closed korrekt platzieren, verify-before-plan fuer $secretDir und cdb.ps1-Pfad, Validierungshierarchie primary-first.

**Verifikationen vor Aenderung:**
- `setup_blue_red.ps1` legt `cdb_network` selbst an (Zeile 52–62) — `.\tools\cdb.ps1 runtime up` sicher als Restart-Hint
- `compose.blue.yml` Zeile 346: canonical secrets path = `~/Documents/.secrets/.cdb`
- `scripts/manage_secrets.ps1` $secretDir = `.cdb_local/.secrets` — falsch

**Aenderungen (Commit 41adc2ed auf PR-Branch):**
- `infrastructure/scripts/setup_testnet.ps1`: exit 1 nach if-($Help)-Block — wirklich fail-closed; --Help exit 0 intakt
- `infrastructure/scripts/manage_secrets.ps1`: Rotate-Hint von `docker compose -f ... --force-recreate` auf `.\tools\cdb.ps1 runtime up` (verifiziert)
- `scripts/activate_live_data.ps1`: fail-closed stub, nur kanonische Front Doors
- `scripts/setup_testnet.ps1`: fail-closed stub, nur kanonische Front Doors
- `scripts/manage_secrets.ps1`: $secretDir korrigiert; Rotate-Hint synchronisiert
- `docs/runbooks/local_ops_artifacts.md`: fail-closed Scripts aus Supported Alternatives entfernt
- `knowledge/operations/TESTNET_SETUP.md`: LEGACY NOTICE header; stale Entrypoints durch kanonische ersetzt

**Merge main + Konflikt:**
- Branch war 10 Commits hinter main (strict: true)
- Merge-Konflikt in CURRENT_STATUS.md geloest

**Checks:**
- ci: PASS
- policy-gate: zuerst FAIL (scripts/* → core/service); Label `manual-approval` gesetzt → Re-Run PASS
- Docs Conflict Guard: PASS, LR-021 Replay Smoke: PASS
- mergeStateStatus: CLEAN
- 3 Copilot-Inline-Threads resolved

**Merge:** 26d91693 auf main, 2026-04-06T01:33:08Z
- Issue #1391: auto-closed
- Issue #1442 (Follow-up-Tracker): manuell geschlossen

## Primaere Verifikationen

- Alle 4 fail-closed Scripts: exit 1, --Help exit 0
- scripts/manage_secrets.ps1 $secretDir = canonical path
- kein docker-compose in manage_secrets.ps1 Kopien
- TESTNET_SETUP.md: kein docker-compose up, kein scripts/setup_testnet

## Restunsicherheiten

Keine im Scope dieses PRs.

## Offene Issues (nicht dieser Session)

- #1375: noch OPEN, faktisch supersediert
- #1285, #1237, #1217, #1207: unveraendert offen
