# Root Information Architecture

Status: Canonical
Issue: #1231
Date: 2026-03-20

## Purpose

This file defines what belongs in the repo root and what should be redirected
elsewhere. It is a root hygiene policy for the working repo, not a bulk move
plan. It complements `tools/enforce-root-baseline.ps1` by defining root
placement rules beyond the existing local-canon presence checks.

## Root Keep Policy

The repo root should contain only these classes of entries:

1. Canonical entrypoints and short discoverability pointers
2. Project manifests, build/config files, and contribution metadata
3. Durable top-level domain directories for active code, docs, infra, tools,
   tests, reports, and artifacts

Everything else should be treated as migration, archive, output, or local-only
material and should not grow in root by default.

## Current Root Classes

| Class | Root policy | Representative entries | Notes |
| --- | --- | --- | --- |
| Canonical entrypoints | Keep | `README.md`, `AGENTS.md`, `CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md`, `CURRENT_STATUS.md`, `PROJECT_STATUS.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `LICENSE` | Top-level navigation is intentional here. |
| Legacy discoverability pointers | Keep only if short and internally redirected | `LEGACY_FILES.md`, `ORCHESTRATOR_PACK_144.md`, `360-SYSTEMCHECK.md`, `DOCS_MOVED_TO_DOCS_HUB.md` | Allowed only when they resolve to a local repo target or explicitly declare historical-only status. |
| Active project/config surface | Keep | `pyproject.toml`, `requirements*.txt`, `pytest.ini`, `Makefile`, `.gitignore`, `.dockerignore`, `.pre-commit-config.yaml`, `.gitattributes`, `.env.example`, `.env.memory.example` | Active repo operation/config belongs here. |
| Active top-level domains | Keep | `.github/`, `agents/`, `artifacts/`, `core/`, `docs/`, `governance/`, `infrastructure/`, `knowledge/`, `k8s/`, `logs/`, `mcp_navpack_working_repo/`, `reports/`, `scripts/`, `services/`, `tests/`, `tools/`, `examples/`, `third_party/`, `cdb_agent_sdk/` | Durable domains with clear repo-wide ownership or existing root-baseline guard coverage. |
| Historical reports and dated snapshots | Should leave root | `CODEX_RUN_REPORT.md`, `EVIDENCE_BACKFILL_REPORT.md`, `governance-audit-2026-01-15.md`, `MERGE_921_REPORT.md`, `MERGE_922_REPORT.md`, `PASS35_REPORT.md`, `PASS36_MAINLINK_SWAP_REPORT.md`, `PASS45_PLACEHOLDER_CLEANUP_REPORT.md`, `PASS661_EVIDENCE_CLOSE_REPORT.md`, `PASS749_ADD_SNAPSHOT_LINK_REPORT.md`, `PASS749_NEXUS_POLISH_REPORT.md`, `PASS749_SNAPSHOT_LINK_SWAP_REPORT.md` | Prefer `reports/` or `docs/archive/` after per-file reference checks. |
| Runtime, log, and output artifacts | Should leave root | `e2e_run.log`, `e2e-smoke.log`, `emoji.log`, `gitleaks.log`, `lint.log`, `run.log`, `run_*.log`, `secret_scan.log`, `emoji-report.json`, `runtime_evidence_bundle_P1.json` | Prefer `logs/`, `artifacts/`, `reports/`, or ignored local-only storage. |
| Local or laptop-specific helper artifacts | Should leave root / stay ignored | `..cdb_local.compose_rendered.yml`, `Makefile_fixed.tmp`, `tmp_pr947_threads_query.graphql`, `.local/`, `.auto-claude/`, `.claude/`, `.gemini/`, `.venv/`, `.worktrees/` | Do not normalize these as long-term root canon. |
| Workdirs, addenda, and triage-needed directories | Triage before move | `_analysis_2026-02-16/`, `_cip_addendum_2026-02-19/`, `_zip_addendum_2026-02-19/`, `emoji-report/`, `evidence-run/`, `governance_*_work/`, `run_20683890826/`, `temp/`, `tmp/`, `tmp_artifacts/` | Require owner/purpose/reference review before relocation or deletion. |

## Immediate Guidance

- Do not add new dated reports, logs, or temporary outputs to root.
- Prefer existing domain targets before inventing new structure:
  `reports/`, `docs/archive/`, `logs/`, `artifacts/`, or ignored local-only
  paths.
- When a root file is kept only for discoverability, it must stay short and
  point to the local canonical location.
- Before moving an existing tracked root artifact, verify live references with
  repo search and preserve any discoverability path that external links may use.

## Reference-Checked Exceptions (2026-03-20)

- Keep in place for now because active repo references still exist:
  - `governance-audit-2026-01-15.md` is linked from `README.md`.
  - `P1_RUNTIME_DOD_REPORT.md` and `runtime_evidence_bundle_P1.json` are linked
    from `docs/governance/README.md` and
    `docs/governance/MARKET_STATE_CONTRACT_V1.md`.
  - `evidence-run/` is referenced from `governance/p5_canary_readiness.yaml`,
    `docs/live-readiness/LR-020-STATE.yaml`,
    `docs/live-readiness/LR-020-EVIDENCE.md`, and
    `scripts/lr020_tier2_evidence_capture.py`.
- Already-correct root pointer cases:
  - `LEGACY_FILES.md`, `ORCHESTRATOR_PACK_144.md`, and
    `360-SYSTEMCHECK.md` are already short local discoverability pointers.
- Low-risk move candidates once a destination is chosen and external-link
  compatibility is handled:
  - `CODEX_RUN_REPORT.md`, `EVIDENCE_BACKFILL_REPORT.md`,
    `MERGE_921_REPORT.md`, `MERGE_922_REPORT.md`, `PASS35_REPORT.md`,
    `PASS36_MAINLINK_SWAP_REPORT.md`, `PASS45_PLACEHOLDER_CLEANUP_REPORT.md`,
    `PASS661_EVIDENCE_CLOSE_REPORT.md`, `PASS749_ADD_SNAPSHOT_LINK_REPORT.md`,
    `PASS749_NEXUS_POLISH_REPORT.md`, and
    `PASS749_SNAPSHOT_LINK_SWAP_REPORT.md` had no active repo-internal
    references in the current spot check outside this policy file.

## First Triage Queue

These are the highest-signal root clutter classes for follow-up, but are not
moved by this issue:

1. Dated pass/merge/governance reports in root
2. Tracked root log/output artifacts
3. Dated workdirs and addendum directories with unclear ownership

## Out of Scope

- Repo-wide status SSOT redesign (`#1232`)
- Snapshot/archive/docs-hub consolidation (`#1235`)
- TODO/placeholder governance cleanup (`#1236`)
- Large move series without per-file reference verification
