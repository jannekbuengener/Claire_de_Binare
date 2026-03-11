# enforce-root-baseline.ps1

Purpose: validate the consolidated Working Repo baseline after retiring the split Docs-Hub default.

## What It Checks

- Required local canon directories exist:
  - `agents/`
  - `docs/`
  - `governance/`
  - `knowledge/`
  - `mcp_navpack_working_repo/`
- Required local entrypoints exist:
  - `README.md`
  - `AGENTS.md`
  - `docs/index.md`
  - `docs/meta/WORKING_REPO_CANON.md`
- Key navigation files do not still point to a retired external docs source as the default path.

## Usage

```powershell
.\tools\enforce-root-baseline.ps1
.\tools\enforce-root-baseline.ps1 -DryRun
```

## Exit Codes

- `0` = baseline valid
- `1` = missing local canon paths or stale split-repo references detected

## Rationale

This repo is no longer `execution only`.
The baseline now protects the opposite invariant:

- active canon lives in this working repo
- local `docs/archive/docs_hub_snapshot/` is the only retained legacy archive

See `docs/meta/WORKING_REPO_CANON.md` for the canonical path matrix.
