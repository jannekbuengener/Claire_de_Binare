# enforce-root-baseline.ps1

Purpose: validate the consolidated Working Repo baseline after retiring the split Docs-Hub default.

## What It Checks

- Required local canon directories exist:
  - `agents/` — canonical agent registry
  - `docs/` — navigation, runbooks, archive
  - `governance/` — operational governance files (DELIVERY_APPROVED.yaml, SECRETS_POLICY.md etc.); tracked at root; not listed in `docs/meta/WORKING_REPO_CANON.md` canon matrix but validated here as a required presence
  - `knowledge/` — canonical knowledge hub
  - `mcp_navpack_working_repo/` — active navigation pack

Note: `docs/meta/WORKING_REPO_CANON.md` is the canonical authority for the active path matrix.
This script checks structural presence; the canon document defines what is authoritative.
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
