# Working Repo Navpack Cheat Sheet

## Where to start

- Read `README.md` first for the repo-wide picture and the current live-readiness framing.
- Jump to `docs/index.md` if you want the shortest local navigation page instead of the long root overview.
- **New developer visual start:** `docs/onboarding/DEVELOPER_VISUAL_START_HERE.md` — Mermaid flow, examples, templates.
- **Developer setup:** `DEVELOPER_ONBOARDING.md` plus `infrastructure/compose/README.md` for local setup and stack bring-up.
- **Repo Brain / Context Intelligence:** `docs/surrealdb/README.md` + `make context-doctor`.
- Check `.github/workflows/ci.yml` and `Makefile` together to understand what CI enforces and what you can run locally.
- Read `AGENTS.md` before assuming docs ownership; it resolves to the local canonical registry at `agents/AGENTS.md`.
- **Navpack:** `mcp_navpack_working_repo/ENTRYPOINTS.yaml` (machine-readable read order) and this CHEATSHEET.

## Safety

- LR bleibt **NO-GO**. Board-Stage `trade-capable` ist kein Live-Go. Kein Echtgeld-Go.
- `CURRENT_STATUS.md` is a ledger, not live truth. GitHub live and repo live win.
- No runtime, Docker, trading, or LR changes are authorized by this navpack.

## Common locations

- `core/` for shared runtime logic, config, safety, replay helpers, and utilities.
- `services/` for service implementations and service-specific entrypoints.
- `infrastructure/compose/` for compose fragments and stack overlays.
- `infrastructure/scripts/` for stack bootstrap, verification, backup, and DR scripts.
- `docs/` for working-repo indices, runbooks, env/db pointers, and live-readiness support docs.
- `docs/runbooks/README.md` and `docs/surrealdb/README.md` for runbook and SurrealDB context indexes.
- `tests/` for unit, integration, replay, smoke, and e2e tests.
- `tools/` for diagnostics, stack checks, MCP validation, hooks, and secrets helpers.
- `scripts/` for guards, testnet setup, live-data activation, and project automation.
- `.codex/cdb_skills/` and `.opencode/skills/` for repo-local agent skill packs (replaces removed `cdb_agent_sdk/` as of PR #2994).
- `tests/fixtures/` for deterministic MCP and test seed assets.

## Top commands

- `Get-Content README.md -TotalCount 120` — fast repo overview from PowerShell.
- `Get-Content docs/index.md -TotalCount 120` — short local navigation entry.
- `Get-Content DEVELOPER_ONBOARDING.md -TotalCount 160` — setup and bring-up checklist.
- `make help` — command surface; requires `make`.
- `Get-ChildItem .github/workflows` — enumerate CI and automation workflows.
- `Get-Content .github/workflows/ci.yml -TotalCount 160` — inspect the main CI contract.
- `docker compose -f infrastructure/compose/compose.blue.yml -f infrastructure/compose/compose.red.yml ps` — inspect the canonical BLUE+RED runtime stack; requires Docker.
- `python tools/validate_mcp_config.py tests/fixtures/mcp_smoke_config.json` — validate MCP config resolution; requires Python deps.
- `pytest -q tests/smoke/test_mcp_runtime.py::test_mcp_time_server_runtime` — run the MCP smoke test; requires pytest and MCP deps.
- `rg -n "TRADING_MODE|LIVE_TRADING_CONFIRMED" core docs` — find the safety gate and its docs; requires `rg`.
- `rg -n "mcpServers|MCP_CONFIG_PATHS" .` — trace MCP config sources; requires `rg`.
- `rg -n "docker compose|stack_up|stack_verify" infrastructure tools scripts` — find stack bring-up and verification flows; requires `rg`.
- `Get-ChildItem services` — list service roots quickly.
- `Get-Content core/config/trading_mode.py -TotalCount 200` — inspect fail-close runtime mode logic.
- `Get-Content tools/README.md -TotalCount 160` — review the local utility surface.

## Gotchas

- `AGENTS.md` here is a root pointer only; the canonical registry now lives in `agents/AGENTS.md` inside this repo.
- The root `README.md` mixes status framing with repo structure; for navigation, `docs/index.md` is usually faster.
- The main CI workflow excludes `test_mcp_time_server_runtime` from the bulk test step, so MCP runtime debugging needs the explicit smoke test.
- The canonical operator runtime is `compose.blue.yml + compose.red.yml`; `base.yml + dev.yml` are CI/testing-only and must not be used as a runtime path.
- `core/config/trading_mode.py` will hard-exit on live mode without `LIVE_TRADING_CONFIRMED=yes`.
- Root contains many historical governance/evidence work directories and zip bundles; they are noise for code/runtime navigation.
