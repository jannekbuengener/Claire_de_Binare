# enforce-root-baseline.ps1

Purpose: validate the canonical Claire de Binare repository entrypoints and tracked root layout.

## What It Checks

- Required local canon directories and entrypoints exist.
- `python -m tools.validate_root_layout` accepts only the tracked root entries
  declared in `config/repository/root_layout.json`.
- Retired root paths such as `reports/`, `manifests/`, `k8s/`, and
  `mcp_navpack_claire_de_binare_repository/` fail closed if reintroduced.
- Key navigation files do not use the retired external historical documentation material as their default.

Note: `docs/meta/REPOSITORY_CANON.md` is the canonical authority for the active path matrix.
The PowerShell script wraps the cross-platform Python guard and retains the
legacy split-reference checks.

## Usage

```powershell
.\tools\enforce-root-baseline.ps1
.\tools\enforce-root-baseline.ps1 -DryRun
```

## Exit Codes

- `0` = baseline valid
- `1` = root, canon-path, or stale split-repo violation detected

## Rationale

This repo is no longer `execution only`.
The baseline now protects the opposite invariant:

- active canon lives in this Claire de Binare repository
- local `docs/archive/` is the only retained legacy archive

See `docs/meta/ROOT_INFORMATION_ARCHITECTURE.md` for the root decision matrix and
`docs/meta/REPOSITORY_CANON.md` for the canonical path matrix.
