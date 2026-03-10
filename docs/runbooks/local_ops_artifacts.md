# Runbook: Local Ops Artifacts

## Scope

This note defines local-only helper artifacts that must not be versioned.

## Local-Only Artifact

- `scripts/cdb_ops.ps1` is a local-only helper script.
- It is intentionally untracked and ignored by Git.

## Why Local-Only

- It typically contains workstation-specific paths and environment assumptions.
- It may include sensitive local operational context that is not suitable for repository history.
- It is not a canonical, supported automation entry point for shared team workflows.

## Supported Alternatives (tracked paths)

- `scripts/manage_secrets.ps1` for secrets/ops setup tasks.
- `scripts/setup_testnet.ps1` for testnet environment setup.
- `scripts/activate_live_data.ps1` for live-data activation workflow.
- `scripts/milestone-assignment.ps1` and `scripts/bulk-issue-labeling.ps1` for project/issue automation.

## Placement Rule for Personal Helpers

- Put personal/local scripts under `.local/` or outside the repository.
- If a helper should become team-supported, promote it as a tracked script with runbook documentation and normal PR review.
