# Session Log — 2026-03-31 — Issue #1404

## Ziel
Legacy-Helper-/Ops-Skripte, die noch auf `.cdb_local/.secrets` und das alte `.env.compose`/`base.yml+dev.yml`-Modell verweisen, aus dem aktiven Tooling-Pfad entfernen.

## Befund
- Alle 5 genannten Dateien sind faktisch Legacy — keines ist der kanonische Entrypoint
- Kanonische Entrypoints: `cdb.ps1 runtime up` -> `setup_blue_red.ps1`, `cdb.ps1 secrets init` -> `init-secrets.ps1`, `tools/cdb-stack-doctor.ps1`
- Aktiver `cdb-stack-doctor.ps1` verwies auf zwei Legacy-Skripte als empfohlene Aktionen

## Umgesetzte Aenderungen

### Als Legacy eingestuft und verschoben nach `infrastructure/scripts/legacy/`
- `infrastructure/scripts/stack_down.ps1` — alte Compose-Topologie, `.cdb_local/.secrets/.env.compose`
- `infrastructure/scripts/stack_doctor.ps1` — alte Container-Liste, alte Secrets-Pfade; ersetzt durch `tools/cdb-stack-doctor.ps1`
- `infrastructure/scripts/generate_stack_scripts.ps1` — generiert Skripte mit `.cdb_local/.secrets`-Pfaden
- `tools/cdb-secrets-sync.ps1` — alter Sync-Flow `.cdb_local/.secrets` -> `.secrets/` + `.env`
- `tools/stack_boot.ps1` — prueft `.secrets/` statt `SECRETS_PATH`; ersetzt durch `cdb.ps1 runtime up`

### Aktiv auf Canon gezogen
- `tools/cdb-stack-doctor.ps1` — Cross-Refs aktualisiert:
  - `./stack_boot.ps1` -> `.\tools\cdb.ps1 runtime up`
  - `./tools/cdb-secrets-sync.ps1` -> `.\tools\cdb.ps1 secrets init`

## Validierung
- `rg` auf alte aktive Pfade: Dateien existieren dort nicht mehr
- `.cdb_local/.secrets` / `.env.compose` Treffer nur noch in `infrastructure/scripts/legacy/`
- `cdb-stack-doctor.ps1` enthaelt keine Referenzen auf Legacy-Skripte mehr

## Restunsicherheiten
- `cdb-stack-doctor.ps1` prueft `.secrets/` (Zeile 38) statt `SECRETS_PATH` — separater Scope (#1406)
- `tools/test_pack/integrations/cdb-stack-adapter.ps1` referenziert noch alte Pfade — selbst als Legacy markiert
- Doku-Pointer in `knowledge/` und `docs/` auf alte Pfade — gehoert zu #1405

## Artefakte
- Commit: d890010
- Branch: fix/1403-knowledge-link-drift
- Issue: #1404 geschlossen
