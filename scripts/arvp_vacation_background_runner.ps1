#Requires -Version 5.1
<#
.SYNOPSIS
  Windows background wrapper for ARVP Vacation Autopilot MVP offline coordinator.
.DESCRIPTION
  Starts tools.arvp_vacation.coordinator in a hidden process with persistent logs.
  Issue #3986. LR NO-GO. No paper runtime.
#>
[CmdletBinding()]
param(
    [switch]$Start,
    [switch]$Stop,
    [switch]$Status,
    [string]$ManifestPath = "config/arvp/vacation/vacation_autopilot_mvp.yaml",
    [string]$CampaignId = "arvp_vacation_mvp_20260713",
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    param([string]$Override)
    if ($Override) { return (Resolve-Path $Override).Path }
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Get-CampaignDir {
    param([string]$Root, [string]$Id)
    Join-Path $Root "artifacts/arvp_vacation/$Id"
}

function Get-PidFile {
    param([string]$CampaignDir)
    Join-Path $CampaignDir "vacation.pid"
}

function Read-PidFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $null }
    $raw = Get-Content -Path $Path -Raw
    if ($raw -match '^\s*(\d+)\s*$') { return [int]$Matches[1] }
    return $null
}

function Test-ProcessRunning {
    param([int]$Pid)
    if ($Pid -le 0) { return $false }
    return $null -ne (Get-Process -Id $Pid -ErrorAction SilentlyContinue)
}

$root = Get-RepoRoot -Override $RepoRoot
$campaignDir = Get-CampaignDir -Root $root -Id $CampaignId
$pidFile = Get-PidFile -CampaignDir $campaignDir

if ($Start) {
    New-Item -ItemType Directory -Force -Path $campaignDir | Out-Null
    $existing = Read-PidFile -Path $pidFile
    if ($existing -and (Test-ProcessRunning -Pid $existing)) {
        Write-Error "Coordinator already running (PID $existing)"
    }
    $manifestFull = Join-Path $root ($ManifestPath -replace '/', '\')
    $stdout = Join-Path $campaignDir "stdout.log"
    $stderr = Join-Path $campaignDir "stderr.log"
    $args = @(
        "-m", "tools.arvp_vacation.coordinator",
        "--manifest", $manifestFull,
        "--run-until-complete",
        "--resume"
    )
    $proc = Start-Process -FilePath "python" -ArgumentList $args `
        -WorkingDirectory $root -WindowStyle Hidden `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
    Set-Content -Path $pidFile -Value $proc.Id -NoNewline
    Write-Output "Started vacation coordinator PID $($proc.Id)"
    Write-Output "Campaign dir: $campaignDir"
    exit 0
}

if ($Status) {
    $pid = Read-PidFile -Path $pidFile
    if (-not $pid) {
        Write-Output "No PID file. Coordinator not started or already cleaned up."
        exit 0
    }
    $alive = Test-ProcessRunning -Pid $pid
    Write-Output "PID: $pid alive=$alive"
    $statePath = Join-Path $campaignDir "queue_state.json"
    if (Test-Path $statePath) {
        Get-Content $statePath -Raw | Write-Output
    }
    exit 0
}

if ($Stop) {
    $pid = Read-PidFile -Path $pidFile
    if (-not $pid) {
        Write-Output "No PID file."
        exit 0
    }
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
    Write-Output "Stopped PID $pid (orphan RUNNING jobs classified on next resume)."
    exit 0
}

Write-Error "Specify -Start, -Stop, or -Status"
