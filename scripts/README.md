# Scripts

## Grafana API helpers

These scripts provide a deterministic Grafana HTTP API path without MCP changes.

Requirements:
- Grafana reachable at GF_URL (default: http://localhost:3000)
- API token via GRAFANA_TOKEN or %SECRETS_PATH%\grafana_api_token
- SECRETS_PATH default: C:\Users\janne\Documents\.secrets\.cdb

Inventory dump:
```powershell
pwsh -File scripts/grafana_inventory_dump.ps1
```

Function usage:
```powershell
. scripts/grafana_api.ps1
Get-GrafanaHealth
Get-GrafanaDatasources
Get-GrafanaFolders
Search-GrafanaDashboards -Query "Claire"
Export-GrafanaDashboardByUid -Uid "<uid>"
```
