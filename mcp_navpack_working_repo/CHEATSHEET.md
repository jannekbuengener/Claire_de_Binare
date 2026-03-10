# Working Repo Navpack Cheat Sheet

## Where to start

- Read `README.md` first for the repo-wide picture and the current live-readiness framing.
- Jump to `docs/index.md` if you want the shortest local navigation page instead of the long root overview.
- Use `DEVELOPER_ONBOARDING.md` plus `infrastructure/compose/README.md` for local setup and stack bring-up.
- Check `.github/workflows/ci.yml` and `Makefile` together to understand what CI enforces and what you can run locally.
- Read `AGENTS.md` before assuming docs ownership; the canonical AGENTS registry lives in the separate Docs Hub repo.

## Common locations

- `core/` for shared runtime logic, config, safety, replay helpers, and utilities.
- `services/` for service implementations and service-specific entrypoints.
- `infrastructure/compose/` for compose fragments and stack overlays.
- `infrastructure/scripts/` for stack bootstrap, verification, backup, and DR scripts.
- `docs/` for working-repo indices, runbooks, env/db pointers, and live-readiness support docs.
- `tests/` for unit, integration, replay, smoke, and e2e tests.
- `tools/` for diagnostics, stack checks, MCP validation, hooks, and secrets helpers.
- `scripts/` for guards, testnet setup, live-data activation, and project automation.
- `cdb_agent_sdk/` for the separate SDK-style subproject.
- `tests/fixtures/` for deterministic MCP and test seed assets.

## Top commands

- `Get-Content README.md -TotalCount 120` — fast repo overview from PowerShell.
- `Get-Content docs/index.md -TotalCount 120` — short local navigation entry.
- `Get-Content DEVELOPER_ONBOARDING.md -TotalCount 160` — setup and bring-up checklist.
- `make help` — command surface; requires `make`.
- `Get-ChildItem .github/workflows` — enumerate CI and automation workflows.
- `Get-Content .github/workflows/ci.yml -TotalCount 160` — inspect the main CI contract.
- `docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml ps` — inspect the dev stack; requires Docker.
- `python tools/validate_mcp_config.py tests/fixtures/mcp_smoke_config.json` — validate MCP config resolution; requires Python deps.
- `pytest -q tests/smoke/test_mcp_runtime.py::test_mcp_time_server_runtime` — run the MCP smoke test; requires pytest and MCP deps.
- `rg -n "TRADING_MODE|LIVE_TRADING_CONFIRMED" core docs` — find the safety gate and its docs; requires `rg`.
- `rg -n "mcpServers|MCP_CONFIG_PATHS" .` — trace MCP config sources; requires `rg`.
- `rg -n "docker compose|stack_up|stack_verify" infrastructure tools scripts` — find stack bring-up and verification flows; requires `rg`.
- `Get-ChildItem services` — list service roots quickly.
- `Get-Content core/config/trading_mode.py -TotalCount 200` — inspect fail-close runtime mode logic.
- `Get-Content tools/README.md -TotalCount 160` — review the local utility surface.

## Gotchas

- `AGENTS.md` here is a pointer only; canonical agent charters live in the sibling `Claire_de_Binare_Docs` repo.
- The root `README.md` mixes status framing with repo structure; for navigation, `docs/index.md` is usually faster.
- The main CI workflow excludes `test_mcp_time_server_runtime` from the bulk test step, so MCP runtime debugging needs the explicit smoke test.
- Compose fragments in `infrastructure/compose/` are the preferred stack path; root-level legacy compose is only a fallback.
- `core/config/trading_mode.py` will hard-exit on live mode without `LIVE_TRADING_CONFIRMED=yes`.
- Root contains many historical governance/evidence work directories and zip bundles; they are noise for code/runtime navigation.
