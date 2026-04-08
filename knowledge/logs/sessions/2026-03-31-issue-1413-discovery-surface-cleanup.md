# Session: Issue #1413 — Discovery Surface Cleanup

**Datum:** 2026-03-31
**Issue:** #1413 docs(discovery): remove remaining legacy/external secrets and ops pointers from active discovery surfaces
**Commit:** 24336365

## Geänderte Dateien

- `mcp_navpack_working_repo/CHEATSHEET.md` — Top-command auf BLUE+RED umgestellt; Gotcha CI/testing-only klargestellt
- `mcp_navpack_working_repo/REPO.map.json` — key_entrypoints: base.yml/dev.yml/stack_up.ps1 entfernt, compose.blue.yml/compose.red.yml/setup_blue_red.ps1 hinzugefügt
- `tools/secrets/README.md` — LEGACY COMPAT → DEPRECATED; .secrets/ und .cdb_local als LEGACY markiert
- `docs/env/index.md` — stack_up.ps1 aus SECRETS_PATH Canon-Pointer-Spalte entfernt
- `knowledge/content/ONBOARDING_LINKS.md` — Entry Chain: COMPOSE_LAYERS.md/QUICK_START.md → ACTIVE_ROADMAP.md
- `knowledge/content/ONBOARDING_QUICK_START.md` — gleiche Entry-Chain-Korrektur
- `knowledge/ARCHITECTURE_COCKPIT.md` — Runbook-Block: bare docker compose → explizite compose.blue.yml+compose.red.yml Befehle
- `tools/test_pack/integrations/cdb-stack-adapter.ps1` — Header: LEGACY BRIDGE, DO NOT USE, scripts\stack_up.ps1 existiert nicht mehr
- `README.md` — base.yml+dev.yml: „sekundaerer Dev-/Kompatibilitaetspfad" → „CI/Testing-only"

## Bewusst nicht angefasst

- `tools/README.md` — bereits sauber gegliedert
- `knowledge/README.md`, `docs/index.md`, `AGENTS.md` — kein Drift
- `mcp_navpack_working_repo/DOCS_HUB.pointer.md` — bereits als „Read-only legacy archive" markiert
- `tools/enforce-root-baseline.ps1` — kein Discovery-Pointer
- `docs/runbooks/local_ops_artifacts.md` — keine aktive Discovery-Navigation mit Legacy-Defaults
