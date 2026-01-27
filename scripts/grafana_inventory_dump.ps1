#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Dump Grafana inventory to JSON files.
.DESCRIPTION
    Writes health, datasources, folders, and dashboard search results to
    .cdb_agent_workspace/grafana_inventory/<timestamp>/
#>

$ErrorActionPreference = "Stop"

$scriptRoot = $PSScriptRoot
$repoRoot = Resolve-Path (Join-Path $scriptRoot "..")
$outputRoot = Join-Path $repoRoot ".cdb_agent_workspace" "grafana_inventory"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outputDir = Join-Path $outputRoot $timestamp

. (Join-Path $scriptRoot "grafana_api.ps1")

function Write-JsonFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [object]$Value
    )

    $json = $Value | ConvertTo-Json -Depth 10
    $json | Out-File -FilePath $Path -Encoding utf8
}

New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

$health = Get-GrafanaHealth
if (-not $health) {
    Write-Error "Grafana health query failed."
    exit 1
}
Write-JsonFile -Path (Join-Path $outputDir "health.json") -Value $health

$datasources = Get-GrafanaDatasources
if ($null -eq $datasources) {
    Write-Error "Grafana datasources query failed."
    exit 1
}
Write-JsonFile -Path (Join-Path $outputDir "datasources.json") -Value $datasources

$folders = Get-GrafanaFolders
if ($null -eq $folders) {
    Write-Error "Grafana folders query failed."
    exit 1
}
Write-JsonFile -Path (Join-Path $outputDir "folders.json") -Value $folders

$dashboards = Search-GrafanaDashboards
if ($null -eq $dashboards) {
    Write-Error "Grafana dashboard search failed."
    exit 1
}
Write-JsonFile -Path (Join-Path $outputDir "dashboards_search.json") -Value $dashboards

Write-Host "Grafana inventory written to: $outputDir"
