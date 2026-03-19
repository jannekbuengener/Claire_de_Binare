#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Read-only Grafana API wrapper for common maintainer tasks.

.DESCRIPTION
    Uses the repo's existing Grafana setup and secrets conventions.
    Supported actions:
    - health: check Grafana health/connectivity
    - list: list or search dashboards
    - export: export a dashboard JSON by UID

    Write operations are intentionally out of scope in this first cut.

.PARAMETER Action
    Supported values: health, list, export

.PARAMETER BaseUrl
    Grafana base URL. Defaults to $env:GRAFANA_URL, then http://localhost:3000.

.PARAMETER Token
    Grafana API token or API key. Preferred for authenticated API calls.

.PARAMETER Username
    Grafana username for basic auth. Defaults to admin.

.PARAMETER Password
    Grafana password for basic auth.

.PARAMETER PasswordFile
    Path to a file containing the Grafana password.

.PARAMETER Query
    Optional dashboard search query for -Action list.

.PARAMETER Limit
    Maximum dashboards returned for -Action list. Defaults to 100.

.PARAMETER Uid
    Dashboard UID for -Action export.

.PARAMETER OutFile
    Optional file path for -Action export. If omitted, dashboard JSON is emitted to stdout.

.EXAMPLE
    .\infrastructure\monitoring\grafana\Invoke-GrafanaApi.ps1 -Action health

.EXAMPLE
    .\infrastructure\monitoring\grafana\Invoke-GrafanaApi.ps1 -Action list -Query claire

.EXAMPLE
    .\infrastructure\monitoring\grafana\Invoke-GrafanaApi.ps1 -Action export -Uid cdb-system-health -OutFile .\cdb_system_health.json
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("health", "list", "export")]
    [string]$Action,

    [Parameter(Mandatory = $false)]
    [string]$BaseUrl,

    [Parameter(Mandatory = $false)]
    [Alias("ApiKey")]
    [string]$Token,

    [Parameter(Mandatory = $false)]
    [string]$Username = "admin",

    [Parameter(Mandatory = $false)]
    [string]$Password,

    [Parameter(Mandatory = $false)]
    [string]$PasswordFile,

    [Parameter(Mandatory = $false)]
    [string]$Query,

    [Parameter(Mandatory = $false)]
    [ValidateRange(1, 5000)]
    [int]$Limit = 100,

    [Parameter(Mandatory = $false)]
    [string]$Uid,

    [Parameter(Mandatory = $false)]
    [string]$OutFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." ".." "..")).Path
$script:ResolvedBaseUrl = $null

function Get-DefaultGrafanaSecretCandidates {
    $candidates = [System.Collections.Generic.List[string]]::new()

    if ($env:GRAFANA_PASSWORD_FILE) {
        $candidates.Add($env:GRAFANA_PASSWORD_FILE)
    }

    if ($env:SECRETS_PATH) {
        $candidates.Add((Join-Path $env:SECRETS_PATH "GRAFANA_PASSWORD"))
    }

    if ($env:USERPROFILE) {
        $candidates.Add(
            (Join-Path $env:USERPROFILE "Documents\.secrets\.cdb\GRAFANA_PASSWORD")
        )
    }

    $candidates.Add(
        (Join-Path $script:RepoRoot ".cdb_local\.secrets\grafana_password")
    )

    return $candidates
}

function Resolve-GrafanaBaseUrl {
    if ($BaseUrl) {
        return $BaseUrl.TrimEnd("/")
    }

    if ($env:GRAFANA_URL) {
        return $env:GRAFANA_URL.TrimEnd("/")
    }

    return "http://localhost:3000"
}

function Read-NonEmptyFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Password file not found: $Path"
    }

    $value = Get-Content -LiteralPath $Path -Raw
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Password file is empty: $Path"
    }

    return $value.Trim()
}

function Resolve-GrafanaAuth {
    param(
        [Parameter(Mandatory = $false)]
        [switch]$AllowAnonymous
    )

    if ($Token) {
        return @{
            Mode = "bearer"
            Source = "-Token"
            Secret = $Token
        }
    }

    if ($env:GRAFANA_TOKEN) {
        return @{
            Mode = "bearer"
            Source = "GRAFANA_TOKEN"
            Secret = $env:GRAFANA_TOKEN
        }
    }

    if ($env:GRAFANA_API_KEY) {
        return @{
            Mode = "bearer"
            Source = "GRAFANA_API_KEY"
            Secret = $env:GRAFANA_API_KEY
        }
    }

    if ($Password) {
        return @{
            Mode = "basic"
            Source = "-Password"
            Secret = $Password
        }
    }

    if ($env:GRAFANA_PASSWORD) {
        return @{
            Mode = "basic"
            Source = "GRAFANA_PASSWORD"
            Secret = $env:GRAFANA_PASSWORD
        }
    }

    $checkedPaths = [System.Collections.Generic.List[string]]::new()

    if ($PasswordFile) {
        $checkedPaths.Add($PasswordFile)
        return @{
            Mode = "basic"
            Source = $PasswordFile
            Secret = (Read-NonEmptyFile -Path $PasswordFile)
        }
    }

    foreach ($candidate in Get-DefaultGrafanaSecretCandidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }
        $checkedPaths.Add($candidate)
        if (Test-Path -LiteralPath $candidate) {
            return @{
                Mode = "basic"
                Source = $candidate
                Secret = (Read-NonEmptyFile -Path $candidate)
            }
        }
    }

    if ($AllowAnonymous) {
        return @{
            Mode = "anonymous"
            Source = "health endpoint allows anonymous read"
            Secret = $null
        }
    }

    $hint = @(
        "No Grafana credentials resolved.",
        "Provide -Token/-ApiKey, set GRAFANA_API_KEY or GRAFANA_TOKEN, pass -Password/-PasswordFile, or ensure GRAFANA_PASSWORD is available in one of these paths:"
    ) + ($checkedPaths | ForEach-Object { " - $_" })

    throw ($hint -join [Environment]::NewLine)
}

function New-GrafanaHeaders {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Auth
    )

    $headers = @{
        Accept = "application/json"
    }

    switch ($Auth.Mode) {
        "bearer" {
            $headers["Authorization"] = "Bearer $($Auth.Secret)"
        }
        "basic" {
            $raw = "{0}:{1}" -f $Username, $Auth.Secret
            $encoded = [Convert]::ToBase64String(
                [System.Text.Encoding]::UTF8.GetBytes($raw)
            )
            $headers["Authorization"] = "Basic $encoded"
        }
        "anonymous" {
        }
        default {
            throw "Unsupported auth mode: $($Auth.Mode)"
        }
    }

    return $headers
}

function New-RequestUri {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $false)]
        [hashtable]$QueryParameters
    )

    $uri = "{0}{1}" -f $script:ResolvedBaseUrl, $Path

    if (-not $QueryParameters -or $QueryParameters.Count -eq 0) {
        return $uri
    }

    $pairs = foreach ($entry in $QueryParameters.GetEnumerator()) {
        if ($null -eq $entry.Value -or [string]::IsNullOrWhiteSpace([string]$entry.Value)) {
            continue
        }
        "{0}={1}" -f `
            [System.Uri]::EscapeDataString([string]$entry.Key), `
            [System.Uri]::EscapeDataString([string]$entry.Value)
    }

    if (-not $pairs) {
        return $uri
    }

    return "{0}?{1}" -f $uri, ($pairs -join "&")
}

function Invoke-GrafanaGet {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $false)]
        [hashtable]$QueryParameters,

        [Parameter(Mandatory = $false)]
        [switch]$AllowAnonymous
    )

    $auth = Resolve-GrafanaAuth -AllowAnonymous:$AllowAnonymous
    $headers = New-GrafanaHeaders -Auth $auth
    $uri = New-RequestUri -Path $Path -QueryParameters $QueryParameters

    Write-Verbose ("GET {0} (auth: {1})" -f $uri, $auth.Source)

    try {
        return Invoke-RestMethod -Method Get -Uri $uri -Headers $headers
    } catch {
        $statusCode = $null
        if ($_.Exception.Response) {
            try {
                $statusCode = [int]$_.Exception.Response.StatusCode
            } catch {
                $statusCode = $null
            }
        }

        $detail = $null
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            $detail = $_.ErrorDetails.Message.Trim()
        }
        if ([string]::IsNullOrWhiteSpace($detail)) {
            $detail = $_.Exception.Message
        }

        if ($statusCode) {
            throw "Grafana API GET $uri failed with HTTP $statusCode. $detail"
        }

        throw "Grafana API GET $uri failed. $detail"
    }
}

function Export-GrafanaDashboard {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DashboardUid
    )

    $escapedUid = [System.Uri]::EscapeDataString($DashboardUid)
    $response = Invoke-GrafanaGet -Path "/api/dashboards/uid/$escapedUid"

    if (-not $response.dashboard) {
        throw "Grafana response for uid '$DashboardUid' did not include a dashboard payload."
    }

    $dashboard = $response.dashboard
    if ($dashboard.PSObject.Properties.Name -contains "id") {
        $dashboard.id = $null
    }

    if ($OutFile) {
        $targetDir = Split-Path -Parent $OutFile
        if ($targetDir) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }

        $json = $dashboard | ConvertTo-Json -Depth 100
        Set-Content -LiteralPath $OutFile -Value $json -Encoding utf8

        return [pscustomobject]@{
            uid = $dashboard.uid
            title = $dashboard.title
            folder = $response.meta.folderTitle
            outFile = (Resolve-Path -LiteralPath $OutFile).Path
        }
    }

    return $dashboard
}

$script:ResolvedBaseUrl = Resolve-GrafanaBaseUrl

switch ($Action) {
    "health" {
        $health = Invoke-GrafanaGet -Path "/api/health" -AllowAnonymous
        [pscustomobject]@{
            baseUrl = $script:ResolvedBaseUrl
            database = $health.database
            version = $health.version
            commit = $health.commit
        }
    }

    "list" {
        $results = Invoke-GrafanaGet -Path "/api/search" -QueryParameters @{
            type = "dash-db"
            query = $Query
            limit = $Limit
        }

        $results |
            Sort-Object -Property folderTitle, title |
            Select-Object -Property title, uid, folderTitle, url, uri, type, tags
    }

    "export" {
        if ([string]::IsNullOrWhiteSpace($Uid)) {
            throw "-Uid is required for -Action export."
        }

        Export-GrafanaDashboard -DashboardUid $Uid
    }
}
