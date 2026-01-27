# tools/metrics/metrics-smoke.ps1
<#
Purpose:
  Quick "are we blind?" check before running longer drills.
  - Prometheus targets reachable?
  - Grafana health ok?
  - Optional: detect "No data" by running a minimal query (TODO hook)

This is a lightweight helper, not a full monitoring test suite.
#>

[CmdletBinding()]
param(
  [string]$PromUrl = "http://127.0.0.1:19090",
  [string]$GrafanaUrl = "http://127.0.0.1:3000",
  [string]$OutDir = ".\evidence\metrics_smoke"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Write-Json($path, $obj) {
  $obj | ConvertTo-Json -Depth 8 | Out-File -FilePath $path -Encoding utf8
}

$report = [ordered]@{
  ts = (Get-Date).ToString("o")
  prometheus = @{}
  grafana = @{}
  notes = @()
}

try {
  $targets = Invoke-RestMethod -Uri "$PromUrl/api/v1/targets" -Method GET -TimeoutSec 10
  $report.prometheus.targets_active = @($targets.data.activeTargets).Count
  $report.prometheus.targets_dropped = @($targets.data.droppedTargets).Count
  Write-Json (Join-Path $OutDir "prometheus_targets.json") $targets
} catch {
  $report.prometheus.error = $_.Exception.Message
}

try {
  $g = Invoke-RestMethod -Uri "$GrafanaUrl/api/health" -Method GET -TimeoutSec 10
  $report.grafana = $g
  Write-Json (Join-Path $OutDir "grafana_health.json") $g
} catch {
  $report.grafana = @{ error = $_.Exception.Message }
}

Write-Json (Join-Path $OutDir "report.json") $report
Write-Host "OK: wrote $OutDir\report.json"
