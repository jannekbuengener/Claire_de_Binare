#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Grafana HTTP API helper functions.
.DESCRIPTION
    Uses GF_URL and GRAFANA_TOKEN (or a token file) to call the Grafana API.
#>

$ErrorActionPreference = "Stop"

function Get-GrafanaBaseUrl {
    $url = $env:GF_URL
    if ([string]::IsNullOrWhiteSpace($url)) {
        return "http://localhost:3000"
    }

    return $url.Trim()
}

function Get-GrafanaToken {
    $token = $env:GRAFANA_TOKEN
    if (-not [string]::IsNullOrWhiteSpace($token)) {
        return $token.Trim()
    }

    $secretsPath = $env:SECRETS_PATH
    if ([string]::IsNullOrWhiteSpace($secretsPath)) {
        $secretsPath = "C:\\Users\\janne\\Documents\\.secrets\\.cdb"
    }

    $tokenPath = Join-Path $secretsPath "grafana_api_token"
    if (Test-Path $tokenPath) {
        $fileToken = Get-Content -Path $tokenPath -Raw
        if (-not [string]::IsNullOrWhiteSpace($fileToken)) {
            return $fileToken.Trim()
        }
    }

    Write-Error "Grafana API token not found. Set GRAFANA_TOKEN or place a token file at $tokenPath."
    return $null
}

function Get-GrafanaAuthHeaders {
    $token = Get-GrafanaToken
    if (-not $token) {
        return $null
    }

    return @{ Authorization = "Bearer $token" }
}

function Invoke-GrafanaApi {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter()]
        [ValidateSet("GET", "POST", "PUT", "DELETE")]
        [string]$Method = "GET",

        [Parameter()]
        [object]$Body
    )

    $baseUrl = Get-GrafanaBaseUrl
    $headers = Get-GrafanaAuthHeaders
    if (-not $headers) {
        return $null
    }

    $uri = $baseUrl.TrimEnd("/") + $Path

    try {
        if ($null -ne $Body) {
            $json = $Body | ConvertTo-Json -Depth 10
            return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -ContentType "application/json" -Body $json
        }

        return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers
    } catch {
        Write-Error "Grafana API request failed ($Method $Path): $($_.Exception.Message)"
        return $null
    }
}

function Get-GrafanaHealth {
    return Invoke-GrafanaApi -Path "/api/health"
}

function Get-GrafanaDatasources {
    return Invoke-GrafanaApi -Path "/api/datasources"
}

function Get-GrafanaFolders {
    return Invoke-GrafanaApi -Path "/api/folders"
}

function Search-GrafanaDashboards {
    [CmdletBinding()]
    param(
        [Parameter()]
        [string]$Query = "",

        [Parameter()]
        [string]$Type = "dash-db"
    )

    $queryParts = @()
    if (-not [string]::IsNullOrWhiteSpace($Query)) {
        $queryParts += "query=$([System.Uri]::EscapeDataString($Query))"
    }
    if (-not [string]::IsNullOrWhiteSpace($Type)) {
        $queryParts += "type=$Type"
    }

    $path = "/api/search"
    if ($queryParts.Count -gt 0) {
        $path = $path + "?" + ($queryParts -join "&")
    }

    return Invoke-GrafanaApi -Path $path
}

function Export-GrafanaDashboardByUid {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Uid
    )

    return Invoke-GrafanaApi -Path ("/api/dashboards/uid/{0}" -f $Uid)
}
