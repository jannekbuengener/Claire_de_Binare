#Requires -Version 5.1

<#
.SYNOPSIS
    Diagnoses the Docker stack and surfaces unhealthy services.
.DESCRIPTION
    Verifies Docker, configuration files, secrets, and container health using docker compose.
.PARAMETER ServiceName
    Optional service to focus on.
.PARAMETER ShowLogs
    Number of log lines to show when services are unhealthy.
.EXAMPLE
    ./tools/cdb-stack-doctor.ps1
    ./tools/cdb-stack-doctor.ps1 -ServiceName cdb_execution -ShowLogs 50
#>

param(
    [string]$ServiceName,
    [int]$ShowLogs = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Section($text) {
    Write-Host ''
    Write-Host ('== {0} ==' -f $text) -ForegroundColor Blue
}

function Write-Success($text) { Write-Host ('[OK]    {0}' -f $text) -ForegroundColor Green }
function Write-Info($text)    { Write-Host ('[INFO]  {0}' -f $text) -ForegroundColor Cyan }
function Write-Warning($text) { Write-Host ('[WARN]  {0}' -f $text) -ForegroundColor Yellow }
function Write-Failure($text) { Write-Host ('[FAIL]  {0}' -f $text) -ForegroundColor Red }

$composeFile = 'docker-compose.yml'
$envFile = '.env'
$secretsFolder = '.secrets'
$requiredSecrets = @('redis_password','postgres_password','grafana_password')
$expectedServices = @('cdb_redis','cdb_postgres','cdb_prometheus','cdb_grafana','cdb_ws','cdb_core','cdb_risk','cdb_execution','cdb_db_writer')

Write-Section 'Docker engine'
try {
    $dockerVersion = docker version --format '{{.Server.Version}}' 2>&1
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($dockerVersion)) {
        throw 'Docker command failed'
    }
    Write-Success ('Docker is running (server {0})' -f $dockerVersion.Trim())
} catch {
    Write-Failure 'Docker Desktop is not accessible.'
    Write-Info 'Start Docker Desktop and wait until it reports running.'
    exit 1
}

Write-Section 'Configuration files'
$configIssues = @()
if (-not (Test-Path $composeFile)) { $configIssues += $composeFile }
if (-not (Test-Path $envFile)) { $configIssues += $envFile }
if (-not (Test-Path $secretsFolder)) { $configIssues += $secretsFolder }
foreach ($secret in $requiredSecrets) {
    $secretPath = Join-Path $secretsFolder $secret
    if (-not (Test-Path $secretPath)) {
        $configIssues += ('Missing secret file: {0}' -f $secret)
    }
}
if ($configIssues.Count -gt 0) {
    Write-Failure 'Configuration issues detected:'
    foreach ($issue in $configIssues) {
        Write-Warning $issue
    }
    exit 1
}
Write-Success 'Required configuration and secrets are present.'

Write-Section 'Container health'
try {
    $psOutput = docker compose ps --format json 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw 'docker compose ps failed'
    }
    $services = if ([string]::IsNullOrWhiteSpace($psOutput)) { @() } else { $psOutput | ConvertFrom-Json }
    if ($services -isnot [array]) {
        $services = @($services)
    }
} catch {
    Write-Failure ('Unable to read docker compose status: {0}' -f $_)
    exit 1
}

if ($services.Count -eq 0) {
    Write-Warning 'No services are running; stack does not appear to be up.'
    Write-Info 'Consider running ./stack_boot.ps1.'
    exit 1
}

if ($ServiceName) {
    $services = $services | Where-Object { $_.Service -eq $ServiceName }
    if ($services.Count -eq 0) {
        Write-Warning ('Service {0} not found in compose output.' -f $ServiceName)
        exit 1
    }
}

$running = ($services | Where-Object { $_.State -eq 'running' }).Count
$healthy = ($services | Where-Object { $_.Health -eq 'healthy' }).Count
$total = $services.Count
Write-Info ('Running: {0}/{1}; Healthy: {2}/{1}' -f $running, $total, $healthy)

$unhealthy = @($services | Where-Object { $_.State -eq 'running' -and $_.Health -ne 'healthy' })
$stopped   = @($services | Where-Object { $_.State -ne 'running' })

function Show-Logs($service, $label) {
    Write-Section ('Logs for {0} ({1})' -f $service.Service, $label)
    try {
        docker logs $service.Name --tail $ShowLogs 2>&1 | ForEach-Object { Write-Host $_ }
    } catch {
        Write-Warning ('Unable to read logs for {0}' -f $service.Service)
    }
}

if ($unhealthy.Count -gt 0) {
    Write-Warning ('Unhealthy services: {0}' -f ($unhealthy | Measure-Object).Count)
    foreach ($entry in $unhealthy) {
        Show-Logs $entry 'unhealthy'
    }
}

if ($stopped.Count -gt 0) {
    Write-Warning ('Stopped services: {0}' -f ($stopped | Measure-Object).Count)
    foreach ($entry in $stopped) {
        Show-Logs $entry 'stopped'
    }
}

Write-Section 'Summary'
if (($unhealthy.Count -eq 0) -and ($stopped.Count -eq 0)) {
    Write-Success 'All monitored services appear healthy.'
    exit 0
}

Write-Failure 'Stack has issues; check the logs above.'
Write-Info 'Run ./tools/cdb-stack-doctor.ps1 again after addressing errors.'
Write-Info 'If secrets changed, run ./tools/cdb-secrets-sync.ps1.'
exit 1
