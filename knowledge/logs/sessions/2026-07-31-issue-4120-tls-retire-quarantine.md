# Session Log — 2026-07-31 — Issue #4120 TLS Overlay RETIRE_QUARANTINE

**Status:** DONE_SLICE_ADDED_TO_BATCH_PR (delivery; no merge / no issue close)
**Branch:** `batch/ci-tooling-issue-4120`
**Base:** `origin/main` @ `e96f724c6a6615fea8bda8adc707b51fbd6bcf84`
**LR:** NO-GO (unchanged)

## Brain Evidence

- brain_source: repo-only
- brain_status: not-used
- context_tool_status: absent (only cursor-cloud MCP)
- repo_fallback_reason: unavailable
- records_found: none

## Decision

`RETIRE_QUARANTINE` — confirmed: no CI/operator start path, SERVICE_CATALOG +
BLUE/RED topology already non-canonical, TLS_SETUP previously contradicted canon
with `.cdb_local/tls` and “Implemented/kanonisch” wording.

## Delivered

- Quarantine banner on `infrastructure/compose/tls.yml` (body mounts unchanged)
- `infrastructure/tls/TLS_SETUP.md` rewritten as quarantined historical guide;
  DOCKER_STACK_RUNBOOK link fixed to `knowledge/operations/DOCKER_STACK_RUNBOOK.md`
- `docs/env/index.md`: POSTGRES_SSLMODE no longer points at TLS_SETUP as canon
- Canon reconcile: INV-022, ARCHITECTURE_MAP, SERVICE_CATALOG, blue_red topology
- `stack_up.ps1` `-TLS` fail-closed (does not attach tls.yml)
- Contract tests extended for quarantine (#4120)

## Validation

- `pytest -q tests/unit/infra/test_tls_network_contract.py --noconftest` → 17 passed
- `python -m tools.validate_readme_links` → OK
- `python -m tools.validate_root_layout` → PASS
- `git diff --check` → clean after whitespace fix
- gitleaks: run at commit stage

## Non-goals / Boundaries

- No Docker install, no cert generation/read, no SECRETS_PATH mutation
- No Full Fast-CI, no `cdb-local-ci`, no merge, no issue close
- Forbidden wave paths untouched (README, CURRENT_STATUS, CONTROL_REGISTER, …)

## Routing

- `python -m tools.pr_routing route --issue 4120` → `CREATE_NEW_BATCH_PR`
- target_branch: `batch/ci-tooling-issue-4120`, lane: `ci-tooling`
