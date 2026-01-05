#Requires -Version 5.1

<#
.SYNOPSIS
    Shows filtered and highlighted Docker service logs.
.DESCRIPTION
    Wraps docker logs with color coding, follow mode, optional regex filtering, and timestamp toggles.
.PARAMETER ServiceName
    Required service name.
.PARAMETER Lines
    Number of lines to retrieve when not following.
.PARAMETER Follow
    Streams logs continuously.
.PARAMETER Filter
    Regex filter applied to static output; live follow is unfiltered after the intro.
.PARAMETER ShowTimestamps
    Enables timestamps on each log entry.
.EXAMPLE
    ./tools/cdb-service-logs.ps1 -ServiceName cdb_execution
    ./tools/cdb-service-logs.ps1 -ServiceName cdb_risk -Filter 'ERROR|WARN'
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ServiceName,

    [int]$Lines = 50,

    [switch]$Follow,

    [string]$Filter,

    [switch]$ShowTimestamps
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

$validServices = @('cdb_redis','cdb_postgres','cdb_prometheus','cdb_grafana','cdb_ws','cdb_core','cdb_risk','cdb_execution','cdb_db_writer')

if ($ServiceName -notin $validServices) {
    Write-Failure ('Invalid service: {0}' -f $ServiceName)
    Write-Host 'Valid services:' -ForegroundColor Yellow
    foreach ($svc in $validServices) {
        Write-Host ('  - {0}' -f $svc)
    }
    exit 1
}

function Write-LogLine($line) {
    if ([string]::IsNullOrWhiteSpace($line)) {
        return
    }
    if ($line -match 'ERROR|Exception|Traceback|Failed') {
        Write-Host $line -ForegroundColor Red
    } elseif ($line -match 'WARNING|WARN') {
        Write-Host $line -ForegroundColor Yellow
    } elseif ($line -match 'INFO') {
        Write-Host $line -ForegroundColor Green
    } else {
        Write-Host $line -ForegroundColor Gray
    }
}

function Show-Logs([string[]]$DockerArgs, $label) {
    Write-Section ('{0} logs' -f $label)
    docker @DockerArgs | ForEach-Object { Write-LogLine $_ }
}

function Get-LogArgs($tailValue) {
    $args = @('logs')
    if ($ShowTimestamps) {
        $args += '-t'
    }
    $args += '--tail'
    $args += $tailValue
    $args += $ServiceName
    return $args
}

Write-Section ('Service logs for {0}' -f $ServiceName)
$filterLabel = if ($Filter) { $Filter } else { 'none' }
Write-Info ('Lines: {0}; Follow: {1}; Filter: {2}' -f $Lines, $Follow.IsPresent, $filterLabel)

try {
    $state = docker inspect --format '{{.State.Status}}' $ServiceName 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw $state
    }
    $state = $state.Trim()
    Write-Info ('Container state: {0}' -f $state)
} catch {
    Write-Failure ('Cannot inspect {0}: {1}' -f $ServiceName, $_)
    exit 1
}

if ($Filter) {
    Write-Section 'Filtered preview'
    try {
        docker logs --tail $Lines $ServiceName 2>&1 | ForEach-Object {
            if ($_ -match $Filter) {
                Write-LogLine $_
            }
        }
    } catch {
        Write-Warning ('Unable to read filtered logs: {0}' -f $_)
    }
    if ($Follow) {
        Write-Info 'Starting live follow (unfiltered) after filtered preview.'
        $followArgs = @('logs','--tail','0','--follow',$ServiceName)
        Show-Logs $followArgs 'live follow'
    }
    exit 0
}

if ($Follow) {
    $liveArgs = Get-LogArgs $Lines
    $liveArgs += '--follow'
    Show-Logs $liveArgs 'live follow'
} else {
    $staticArgs = Get-LogArgs $Lines
    Show-Logs $staticArgs 'static output'
}
