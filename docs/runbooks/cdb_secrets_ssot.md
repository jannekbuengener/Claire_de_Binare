# CDB Secrets SSOT Runbook

## SSOT Rule
- Source of truth for all CDB secrets is external only:
  - `C:\Users\janne\Documents\.secrets\.cdb\`
- Secret files stay there permanently.
- Never store secret values in repository files, commits, or logs.
- GitHub repo secrets are derived copies and must be synced from SSOT locally.

## Local Manifest (external, not in repo)
- Path:
  - `C:\Users\janne\Documents\.secrets\.cdb\secrets.manifest.json`
- Manifest format (names only, no values):

```json
{
  "repo": "jannekbuengener/Claire_de_Binare",
  "secrets": {
    "ADD_TO_PROJECT_PAT": "GH_CLI_PROJECTS.txt",
    "CDB_GH_APP_ID": "CDB_GH_APP_ID.txt",
    "CDB_GH_APP_PRIVATE_KEY": "CDB_GH_APP_PRIVATE_KEY.pem",
    "CDB_GH_APP_INSTALLATION_ID": "CDB_GH_APP_INSTALLATION_ID.txt"
  }
}
```

## Secret Sync
- Script:
  - `scripts/secrets/sync_cdb_secrets.ps1`
- Inputs:
  - `CDB_SECRETS_DIR` (optional env var)
  - default path: `C:\Users\janne\Documents\.secrets\.cdb\`
- Behavior:
  - Reads `secrets.manifest.json`
  - Validates mapped files
  - Sets repo secrets via `gh secret set`
  - Prints only metadata (`OK/FAIL/SKIP` by secret name), never values
  - Supports `-DryRun` and `-Only <NAME1,NAME2>`

### Commands
```powershell
# Dry-run (no mutation)
powershell -File scripts/secrets/sync_cdb_secrets.ps1 -DryRun

# Apply all mapped secrets
powershell -File scripts/secrets/sync_cdb_secrets.ps1
```

## Expected Repo Secret Names
- `ADD_TO_PROJECT_PAT`:
  - Legacy PAT fallback for Projects v2 operations.
- `CDB_GH_APP_ID`:
  - GitHub App auth path (optional). Used by Control-Board / Projects workflows.
  - For #4170 local-ci Check Runs: expected App ID for publisher readback
    (non-secret config). Prefer a **dedicated** local-ci App; do not blindly
    overwrite Control-Board values.
- `CDB_GH_APP_PRIVATE_KEY`:
  - GitHub App private key (optional inline PEM; required with app id for minting
    when path is unset).
  - Never commit; store only in external SSOT.
- `CDB_GH_APP_PRIVATE_KEY_PATH` (local operator input, preferred):
  - Absolute path to PEM in the external SSOT directory (e.g.
    `...\Documents\.secrets\.cdb\cdb-local-ci-app.pem`).
  - Prefer path over inline env when both are available locally.
  - Documented alias: `CDB_GITHUB_APP_PRIVATE_KEY_PATH`.
- `CDB_GH_APP_INSTALLATION_ID`:
  - Optional explicit installation id for app path / Check Run expected ID.
  - Documented alias: `CDB_GITHUB_APP_INSTALLATION_ID` (with
    `CDB_GITHUB_APP_ID` for App ID).
- `CDB_GH_APP_INSTALLATION_TOKEN` (publisher Check Run mode, ephemeral):
  - Short-lived installation token for `--publisher-backend check-run`.
  - Optional override; when unset, `ci.publisher.app_auth` auto-mints from
    App ID + Installation ID + PEM (#4170 Phase C).
  - Never pass as CLI argument; never log. See
    [`cdb_local_ci_app_check_run_cutover.md`](cdb_local_ci_app_check_run_cutover.md).

## Workflow Token Path (control board)
- Workflows resolve auth in this order:
  - GitHub App path (if app id + app key are configured)
  - fallback to `ADD_TO_PROJECT_PAT`
- Resolved token is passed to scripts via `GH_TOKEN`.
- Routing workflow also sets `CDB_AUTH_TOKEN`.

## Security Rules
- Never print token values.
- Never commit secret files.
- Never copy secret values into repository docs.
- Keep toggle default OFF unless running controlled smoke tests.

## Ops Flow For ON Smoke Test
1. Run local secret sync from SSOT.
2. Set `CDB_CONTROL_BOARD_AUTOMATION_ENABLED=true` only for the test window.
3. Execute ON smoke test and capture evidence links.
4. Reset toggle to OFF (`unset` or value not equal to `true`).
