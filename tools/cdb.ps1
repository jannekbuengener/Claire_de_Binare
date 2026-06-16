#Requires -Version 5.1

param(
    [Parameter(Position=0)]
    [string]$Area,

    [Parameter(Position=1)]
    [string]$Action,

    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$RemainingArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Show-Usage {
    @'
CDB PowerShell v1 front door

Usage:
  .\tools\cdb.ps1 secrets init [args]
  .\tools\cdb.ps1 runtime up [args]
  .\tools\cdb.ps1 runtime smoke [args]
  .\tools\cdb.ps1 stack verify [args]
  .\tools\cdb.ps1 service logs [args]
  .\tools\cdb.ps1 onboarding doctor [--format json]

Examples:
  .\tools\cdb.ps1 secrets init
  .\tools\cdb.ps1 secrets init -Force
  .\tools\cdb.ps1 runtime up
  .\tools\cdb.ps1 runtime up -SkipRed
  .\tools\cdb.ps1 stack verify -Verbose
  .\tools\cdb.ps1 service logs -ServiceName cdb_risk -Lines 100
  .\tools\cdb.ps1 runtime smoke -Verbose

Non-interactive:
  pwsh -ExecutionPolicy Bypass -File .\tools\cdb.ps1 runtime up
'@ | Write-Host
}

if ([string]::IsNullOrWhiteSpace($Area) -or $Area -in @('help', '--help', '-h', '/?')) {
    Show-Usage
    exit 0
}

if ([string]::IsNullOrWhiteSpace($Action)) {
    Show-Usage
    exit 1
}

$scriptDir = $PSScriptRoot
if (-not $scriptDir) {
    $definition = $MyInvocation.MyCommand.Definition
    $scriptDir = if ($definition) { Split-Path -Parent $definition } else { Get-Location }
}
$repoRoot = Split-Path -Parent $scriptDir

$areaText = if ([string]::IsNullOrWhiteSpace($Area)) { '' } else { $Area.Trim().ToLowerInvariant() }
$actionText = if ([string]::IsNullOrWhiteSpace($Action)) { '' } else { $Action.Trim().ToLowerInvariant() }
$commandKey = ('{0} {1}' -f $areaText, $actionText).Trim()
$targetRelativePath = switch ($commandKey) {
    'secrets init' { 'infrastructure\scripts\init-secrets.ps1' }
    'runtime up' { 'infrastructure\scripts\setup_blue_red.ps1' }
    'runtime smoke' { 'infrastructure\scripts\smoke_test.ps1' }
    'stack verify' { 'tools\verify_stack.ps1' }
    'service logs' { 'tools\cdb-service-logs.ps1' }
    'onboarding doctor' { 'tools\onboarding_doctor.py' }
    default { $null }
}

if (-not $targetRelativePath) {
    Write-Error "Unknown command: '$commandKey'. Run '.\tools\cdb.ps1 help' for usage."
    exit 1
}

$targetPath = Join-Path $repoRoot $targetRelativePath
if (-not (Test-Path -LiteralPath $targetPath)) {
    Write-Error "Missing target script: $targetPath"
    exit 1
}

if ($targetRelativePath -like '*.py') {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        Write-Error "Missing required Python interpreter (expected python in PATH)."
        exit 1
    }
    $invokeArgs = @($targetPath) + $RemainingArgs
    Push-Location -LiteralPath $repoRoot
    try {
        & $pythonCmd.Source @invokeArgs
        exit $LASTEXITCODE
    } finally {
        Pop-Location
    }
} else {
    $shellCommand = if ($PSVersionTable.PSEdition -eq 'Core') {
        Get-Command pwsh -ErrorAction SilentlyContinue
    } else {
        Get-Command powershell.exe -ErrorAction SilentlyContinue
    }
    if (-not $shellCommand) {
        $shellCommand = Get-Command pwsh -ErrorAction SilentlyContinue
    }
    if (-not $shellCommand) {
        $shellCommand = Get-Command powershell.exe -ErrorAction SilentlyContinue
    }
    if (-not $shellCommand) {
        Write-Error "Missing required PowerShell host (expected pwsh or powershell.exe)."
        exit 1
    }

    $invokeArgs = @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', $targetPath
    ) + $RemainingArgs

    Push-Location -LiteralPath $repoRoot
    try {
        & $shellCommand.Source @invokeArgs
        exit $LASTEXITCODE
    } finally {
        Pop-Location
    }
}
