#Requires -Version 5.1
<#
.SYNOPSIS
  ARVP 14-day vacation MEXC candle data capture (no trading).
.DESCRIPTION
  Wraps tools.arvp_vacation.data_capture for preflight, start, status, stop, resume.
  Issue #3990. LR NO-GO. No paper, signal, execution, or live trading.
  Start/Resume require the exact DATA-CAPTURE-GO phrase.
#>
[CmdletBinding()]
param(
    [switch]$Preflight,
    [switch]$Start,
    [switch]$Status,
    [switch]$Stop,
    [switch]$Resume,
    [string]$ManifestPath = "manifests/vacation/vacation_data_capture_14d.yaml",
    [string]$GoPhrase = "",
    [string]$RepoRoot = "",
    [switch]$Json
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    param([string]$Override)
    if ($Override) { return (Resolve-Path $Override).Path }
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$root = Get-RepoRoot -Override $RepoRoot
$manifestFull = Join-Path $root ($ManifestPath -replace '/', '\')
$pyArgs = @("-m", "tools.arvp_vacation.data_capture", "--manifest", $manifestFull)
if ($Json) { $pyArgs += "--json" }

if ($Preflight) {
    $pyArgs += "--preflight-only"
    Push-Location $root
    try {
        & python @pyArgs
        exit $LASTEXITCODE
    } finally {
        Pop-Location
    }
}

if ($Status) {
    $pyArgs += "--status"
    Push-Location $root
    try {
        & python @pyArgs
        exit $LASTEXITCODE
    } finally {
        Pop-Location
    }
}

if ($Start) {
    if (-not $GoPhrase) {
        Write-Error "Start requires -GoPhrase with exact DATA-CAPTURE-GO phrase"
    }
    $pyArgs += @("--start", "--go-phrase", $GoPhrase)
    Push-Location $root
    try {
        & python @pyArgs
        exit $LASTEXITCODE
    } finally {
        Pop-Location
    }
}

if ($Stop) {
    $pyArgs += "--stop"
    Push-Location $root
    try {
        & python @pyArgs
        exit $LASTEXITCODE
    } finally {
        Pop-Location
    }
}

if ($Resume) {
    if (-not $GoPhrase) {
        Write-Error "Resume requires -GoPhrase with exact DATA-CAPTURE-GO phrase"
    }
    $pyArgs += @("--resume", "--go-phrase", $GoPhrase)
    Push-Location $root
    try {
        & python @pyArgs
        exit $LASTEXITCODE
    } finally {
        Pop-Location
    }
}

Write-Error "Specify -Preflight, -Start, -Status, -Stop, or -Resume"
