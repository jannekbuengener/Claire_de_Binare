# Tools

Utility scripts for local maintenance, diagnostics, and validation.

## Core scripts

- `install_hooks.ps1` - Install repo-local git hooks (pre-commit).
  - `pwsh -File tools/install_hooks.ps1`
- `hooks/pre-commit.sh` - Pre-commit hook for baseline + contract validation.
- `validate_contract.py` - Validate payloads against contract schemas.
  - `python tools/validate_contract.py market_data --file docs/contracts/examples/market_data_valid.json`
- `check_ci_health.ps1` - Summarizes recent GitHub Actions runs and flags billing/failure degradation.
  - `pwsh -File tools/check_ci_health.ps1 -Limit 10`
- `verify_stack.ps1` - Verify Docker stack health (services, volumes, networks).
  - `pwsh -File tools/verify_stack.ps1 -Verbose`
- `cdb-stack-doctor.ps1` - Diagnose Docker stack health and show logs for unhealthy services.
  - `pwsh -File tools/cdb-stack-doctor.ps1`
- `cdb-service-logs.ps1` - Tail logs for a specific service.
  - `pwsh -File tools/cdb-service-logs.ps1 -Service cdb_execution`
- `cdb-secrets-sync.ps1` - Sync secrets into expected locations.
  - `pwsh -File tools/cdb-secrets-sync.ps1`
- `enforce-root-baseline.ps1` - Verify repo root structure and baseline files.
  - `pwsh -File tools/enforce-root-baseline.ps1`
- `stack_boot.ps1` - Bootstraps the local stack.
  - `pwsh -File tools/stack_boot.ps1`
- `install-git-hooks.ps1` - Install repo-local Git hooks (baseline enforcement).
  - `pwsh -File tools/install-git-hooks.ps1`
- `set_secrets.ps1` - Create or update local secrets files.
  - `pwsh -File tools/set_secrets.ps1`
- `link_check.py` - Validate internal links.
  - `python tools/link_check.py`
- `provenance_hash.py` - Create a provenance hash for artifacts.
  - `python tools/provenance_hash.py`
