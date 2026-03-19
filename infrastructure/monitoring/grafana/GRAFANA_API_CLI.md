# Grafana API CLI (PowerShell)

Read-only maintainer wrapper for the local Grafana instance and provisioned dashboards.

Script:
- `infrastructure/monitoring/grafana/Invoke-GrafanaApi.ps1`

Current scope:
- `health`: connectivity / `/api/health`
- `list`: list or search dashboards via `/api/search`
- `export`: export dashboard JSON via `/api/dashboards/uid/:uid`

## Quick Start

```powershell
pwsh -File .\infrastructure\monitoring\grafana\Invoke-GrafanaApi.ps1 -Action health
pwsh -File .\infrastructure\monitoring\grafana\Invoke-GrafanaApi.ps1 -Action list
pwsh -File .\infrastructure\monitoring\grafana\Invoke-GrafanaApi.ps1 -Action list -Query claire
pwsh -File .\infrastructure\monitoring\grafana\Invoke-GrafanaApi.ps1 -Action export -Uid cdb-system-health -OutFile .\tmp\cdb_system_health.json
```

## Configuration

Base URL resolution:
1. `-BaseUrl`
2. `GRAFANA_URL`
3. `http://localhost:3000`

Auth resolution for authenticated actions (`list`, `export`):
1. `-Token`
2. `-ApiKey` (alias of `-Token`)
3. `GRAFANA_API_KEY`
4. `GRAFANA_TOKEN`
5. `-Password`
6. `GRAFANA_PASSWORD`
7. `-PasswordFile`
8. `GRAFANA_PASSWORD_FILE`
9. `${SECRETS_PATH}\GRAFANA_PASSWORD`
10. `%USERPROFILE%\Documents\.secrets\.cdb\GRAFANA_PASSWORD`
11. Repo-local fallback: `.cdb_local\.secrets\grafana_password`

Default username for basic auth:
- `admin`

Notes:
- `health` intentionally allows anonymous read because the repo already uses `GET /api/health`
  for container health checks and local runbooks.
- `export` writes the dashboard model only and normalizes `id = null` for repo-friendly JSON.

## Maintainer Workflow

List dashboards and find the UID:

```powershell
pwsh -File .\infrastructure\monitoring\grafana\Invoke-GrafanaApi.ps1 -Action list -Query soak
```

Export a dashboard to compare with the provisioned JSON files under
`infrastructure/monitoring/grafana/dashboards/`:

```powershell
pwsh -File .\infrastructure\monitoring\grafana\Invoke-GrafanaApi.ps1 -Action export `
  -Uid claire-soak-test `
  -OutFile .\tmp\claire_soak_test_v1.export.json
```

For manual UI import/provisioning background, see:
- `infrastructure/monitoring/grafana/DASHBOARD_IMPORT.md`
