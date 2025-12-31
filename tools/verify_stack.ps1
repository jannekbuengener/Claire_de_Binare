#Requires -Version 5.1
<#
.SYNOPSIS
    Verifies Docker stack health (services, volumes, networks, endpoints).
.DESCRIPTION
    Checks expected container health, named volumes, and networks. Optional
    endpoint checks are available via -Verbose.
.PARAMETER Verbose
    Enable endpoint checks and detailed output.
.PARAMETER Json
    Output results as JSON for automation.
.PARAMETER StackName
    Stack name prefix (default: STACK_NAME env var or "cdb").
.PARAMETER IncludeLogging
    Include logging services (cdb_loki, cdb_promtail) in expected list.
.PARAMETER IncludePaperRunner
    Include paper trading runner in expected list.
.PARAMETER ExpectedVolumes
    Expected number of Docker volumes with the stack prefix.
.PARAMETER ExpectedNetworks
    Expected number of Docker networks with the stack prefix.
.EXAMPLE
    pwsh -File tools/verify_stack.ps1
.EXAMPLE
    pwsh -File tools/verify_stack.ps1 -Verbose -Json
#>
param(
    [switch]$Verbose,
    [switch]$Json,
    [string]$StackName = ($env:STACK_NAME | ForEach-Object { $_ }) ?? 'cdb',
    [bool]$IncludeLogging = $true,
    [bool]$IncludePaperRunner = $true,
    [int]$ExpectedVolumes = 6,
    [int]$ExpectedNetworks = 2
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Section($text) { Write-Host "`n== $text ==" -ForegroundColor Blue }
function Write-Info($text)    { Write-Host "[INFO]  $text" -ForegroundColor Cyan }
function Write-Success($text) { Write-Host "[OK]    $text" -ForegroundColor Green }
function Write-Warning($text) { Write-Host "[WARN]  $text" -ForegroundColor Yellow }
function Write-Failure($text) { Write-Host "[FAIL]  $text" -ForegroundColor Red }

function Require-Command($name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Write-Failure "Missing required command: $name"
        exit 2
    }
}

Require-Command docker

$expectedServices = @(
    'cdb_redis',
    'cdb_postgres',
    'cdb_prometheus',
    'cdb_grafana',
    'cdb_ws',
    'cdb_signal',
    'cdb_risk',
    'cdb_execution',
    'cdb_db_writer'
)

if ($IncludeLogging) {
    $expectedServices += @('cdb_loki', 'cdb_promtail')
}
if ($IncludePaperRunner) {
    $expectedServices += 'cdb_paper_runner'
}

$results = [ordered]@{
    Services = [ordered]@{
        Expected = $expectedServices.Count
        Running = 0
        Healthy = 0
        Unhealthy = 0
        Missing = 0
    }
    Volumes = [ordered]@{
        Expected = $ExpectedVolumes
        Found = 0
        Names = @()
    }
    Networks = [ordered]@{
        Expected = $ExpectedNetworks
        Found = 0
        Names = @()
    }
    Endpoints = @{}
}

Write-Section "Service Health"
foreach ($service in $expectedServices) {
    $status = docker inspect $service --format '{{.State.Status}}' 2>$null
    if (-not $status) {
        $results.Services.Missing++
        Write-Failure "$service missing"
        continue
    }
    if ($status -ne 'running') {
        $results.Services.Unhealthy++
        Write-Failure "$service status=$status"
        continue
    }
    $results.Services.Running++
    $health = docker inspect $service --format '{{.State.Health.Status}}' 2>$null
    if (-not $health -or $health -eq '<no value>') {
        $results.Services.Unhealthy++
        Write-Warning "$service running (no healthcheck)"
        continue
    }
    if ($health -eq 'healthy') {
        $results.Services.Healthy++
        Write-Success "$service healthy"
        continue
    }
    if ($health -eq 'starting') {
        $results.Services.Unhealthy++
        Write-Warning "$service starting"
        continue
    }
    $results.Services.Unhealthy++
    Write-Failure "$service health=$health"
}

Write-Section "Volumes"
$volumeNames = docker volume ls --filter "name=${StackName}_" --format '{{.Name}}'
$results.Volumes.Names = @($volumeNames | Where-Object { $_ })
$results.Volumes.Found = $results.Volumes.Names.Count
Write-Info "Found $($results.Volumes.Found)/$($results.Volumes.Expected) volumes"
foreach ($vol in $results.Volumes.Names) {
    Write-Success $vol
}

Write-Section "Networks"
$networkNames = docker network ls --filter "name=${StackName}" --format '{{.Name}}'
$results.Networks.Names = @($networkNames | Where-Object { $_ })
$results.Networks.Found = $results.Networks.Names.Count
Write-Info "Found $($results.Networks.Found)/$($results.Networks.Expected) networks"
foreach ($net in $results.Networks.Names) {
    Write-Success $net
}

if ($Verbose) {
    Write-Section "Endpoints"
    $endpoints = [ordered]@{
        'cdb_ws' = 'http://localhost:8000/health'
        'cdb_signal' = 'http://localhost:8005/health'
        'cdb_risk' = 'http://localhost:8002/health'
        'cdb_execution' = 'http://localhost:8003/health'
        'cdb_paper_runner' = 'http://localhost:8004/health'
        'cdb_grafana' = 'http://localhost:3000/api/health'
        'cdb_prometheus' = 'http://localhost:19090/-/healthy'
        'cdb_loki' = 'http://localhost:3100/ready'
    }

    foreach ($key in $endpoints.Keys) {
        try {
            $response = Invoke-WebRequest -Uri $endpoints[$key] -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -eq 200) {
                $results.Endpoints[$key] = 'OK'
                Write-Success "$key endpoint OK"
            } else {
                $results.Endpoints[$key] = "HTTP $($response.StatusCode)"
                Write-Warning "$key endpoint HTTP $($response.StatusCode)"
            }
        } catch {
            $results.Endpoints[$key] = 'FAILED'
            Write-Failure "$key endpoint FAILED"
        }
    }
}

Write-Section "Summary"
Write-Info "Services healthy: $($results.Services.Healthy)/$($results.Services.Expected)"
Write-Info "Volumes: $($results.Volumes.Found)/$($results.Volumes.Expected)"
Write-Info "Networks: $($results.Networks.Found)/$($results.Networks.Expected)"

if ($Json) {
    $results | ConvertTo-Json -Depth 6
}

$allHealthy = (
    $results.Services.Healthy -eq $results.Services.Expected -and
    $results.Volumes.Found -ge $results.Volumes.Expected -and
    $results.Networks.Found -ge $results.Networks.Expected
)

if ($allHealthy) {
    Write-Success "Stack is healthy"
    exit 0
}

Write-Warning "Stack has issues"
exit 1
