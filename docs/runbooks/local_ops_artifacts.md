# Runbook: Local Artifact Policy

## Scope

This note defines which artifacts stay local, which outputs are generated at
runtime, and which paths are canonical repo source that should only be ignored
with explicit intent.

## Policy Classes

- Local-only runtime and secrets stay out of git.
- Generated runtime output and scratch data stay out of git unless a runbook
  explicitly promotes them into a canonical evidence path.
- Repo source and canonical docs stay tracked by default.
- Evidence and reports are commit-worthy only when they live in a canonical
  reviewable path and are intentionally produced for audit or review.

## Local-Only Runtime And Secrets

- Keep `.env`, `*.env.runtime`, `.secrets/`, `.mcp.json`, and
  `infrastructure/actions-runner/.env.runner` local-only.
- Do not relax secret-related ignore rules unless the tracking impact is fully
  understood.

## Local Cache And Tooling State

- Typical local-only examples are `.venv/`, `.pytest_cache/`,
  `.ruff_cache/`, `__pycache__/`, `.worktrees/`, `.claude/`, `.gemini/`,
  `.auto-claude/`, and `.local/`.
- These paths exist to reduce local noise and should not become canonical repo
  storage.

## Generated Runtime Output

- Generated logs, rendered compose files, runtime bundles, and local reports
  are local-only by default.
- Typical examples are `logs/`, `*.log`, `..cdb_local.compose_rendered.yml`,
  `reports/decision_contract/`, and ad-hoc root reports such as
  `P1_RUNTIME_DOD_REPORT.md`.
- Root scratch directories such as `temp/`, `tmp/`, and `artifacts/` are
  operationally local today even when some ignore behavior still comes from
  developer-local excludes.

## Repo Source And Canonical Paths

- Shared source and canonical documentation stay tracked by default.
- Canonical source roots include `agents/`, `knowledge/`, `docs/`, `.github/`,
  `infrastructure/`, `services/`, `tests/`, `tools/`, and tracked team scripts.
- If a file under one of these paths is ignored by historical broad patterns,
  treat that as drift to review, not as a reason to add more broad ignores.

## Evidence And Report Rule

- Evidence may be committed when a runbook or issue explicitly calls for a
  canonical, reviewable artifact path.
- Prefer canonical evidence locations under `docs/` or another documented
  tracked path over root-level ad-hoc report files.
- Ephemeral local reports should stay local and be attached externally when
  review needs them but repo history does not.

## Current Repo Drift Notes

- Some obvious local-only artifacts are still ignored via `.git/info/exclude`
  or nested tool-generated `.gitignore` files instead of the repo-root
  `.gitignore`.
- Current examples include `/artifacts/`, `/tmp/`, `/temp/`,
  `/CODEX_RUN_REPORT.md`, and tool-generated cache markers under
  `.pytest_cache/` and `.ruff_cache/`.
- Treat those paths as local-only for now, but prefer repo-visible policy for
  stable shared conventions when a later cleanup can do so safely.

## Local-Only Helper Exception

- `scripts/cdb_ops.ps1` is a local-only helper script.
- It is intentionally untracked and ignored by Git.
- It typically contains workstation-specific paths and environment assumptions.
- It may include sensitive local operational context that is not suitable for
  repository history.
- It is not a canonical, supported automation entry point for shared team
  workflows.

## Supported Alternatives (tracked paths)

- `scripts/manage_secrets.ps1` for secrets/ops setup tasks.
- `scripts/setup_testnet.ps1` for testnet environment setup.
- `scripts/activate_live_data.ps1` for live-data activation workflow.
- `scripts/milestone-assignment.ps1` and `scripts/bulk-issue-labeling.ps1` for project/issue automation.

## Placement Rule for Personal Helpers

- Put personal/local scripts under `.local/` or outside the repository.
- If a helper should become team-supported, promote it as a tracked script with
  runbook documentation and normal PR review.
