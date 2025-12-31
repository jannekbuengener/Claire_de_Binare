# Tools

Utility scripts for local maintenance, diagnostics, and validation.

## Core scripts

- `check_ci_health.ps1` - Summarize GitHub Actions runs and flag CI degradation.
- `validate_contract.py` - Validate payloads against contract schemas.
- `verify_stack.ps1` - Verify Docker stack health (services, volumes, networks).
- `install_hooks.ps1` - Install repo-local git hooks (contract validation).
- `hooks/pre-commit.sh` - Pre-commit hook for baseline + contract validation.
- `install-git-hooks.ps1` - Install repo-local git hooks (baseline enforcement).
- `cdb-stack-doctor.ps1` - Diagnose Docker stack health and show logs.
- `cdb-service-logs.ps1` - Tail logs for a specific service.
- `cdb-secrets-sync.ps1` - Sync secrets into expected locations.
- `enforce-root-baseline.ps1` - Verify repo root structure and baseline files.
- `enforce-root-baseline.README.md` - Usage notes for baseline enforcement.
- `stack_boot.ps1` - Bootstraps the local stack.
- `set_secrets.ps1` - Create or update local secrets files.
- `link_check.py` - Validate internal links.
- `provenance_hash.py` - Create a provenance hash for artifacts.

## Tool directories

- `cleanup/` - Cleanup utilities.
- `paper_trading/` - Paper trading runner and helpers.
- `replay/` - Replay tooling for deterministic runs.
- `research/` - Research scripts and experiments.
