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
  - GitHub App auth path (optional).
- `CDB_GH_APP_PRIVATE_KEY`:
  - GitHub App private key (optional, required with app id).
- `CDB_GH_APP_INSTALLATION_ID`:
  - Optional explicit installation id for app path.

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
