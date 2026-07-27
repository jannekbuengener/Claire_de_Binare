#Requires -Version 7.0
<#
.SYNOPSIS
  Windows front door for the trusted local CI status publisher.
.DESCRIPTION
  Delegates to python -m ci.publisher. Token is read from the environment
  (GITHUB_TOKEN / GH_TOKEN) or gh auth — never echoed.
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("validate", "publish", "inspect", "dry-run")]
    [string]$Command,

    [string]$EvidenceDir = "",
    [string]$CommitSha = "",
    [int]$PrNumber = 0,
    [string]$StatusContext = "cdb-local-ci",
    [double]$FreshnessHours = 24,
    [string]$Repository = "jannekbuengener/Claire_de_Binare",
    [string]$TargetUrl = "",
    [string]$Ledger = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
}
else {
    $PythonExe = "python"
}

$pyArgs = @("-m", "ci.publisher", $Command)
if ($EvidenceDir) { $pyArgs += @("--evidence-dir", $EvidenceDir) }
elseif ($Command -ne "inspect") {
    Write-Error "EvidenceDir is required for command '$Command'"
    exit 2
}
else {
    $pyArgs += @("--evidence-dir", ".")
}
if ($CommitSha) { $pyArgs += @("--commit-sha", $CommitSha) }
if ($PrNumber -gt 0) { $pyArgs += @("--pr-number", "$PrNumber") }
if ($StatusContext) { $pyArgs += @("--status-context", $StatusContext) }
$pyArgs += @("--freshness-hours", "$FreshnessHours")
if ($Repository) { $pyArgs += @("--repository", $Repository) }
if ($TargetUrl) { $pyArgs += @("--target-url", $TargetUrl) }
if ($Ledger) { $pyArgs += @("--ledger", $Ledger) }

Write-Host "CDB local CI status publisher → $PythonExe -m ci.publisher $Command"
& $PythonExe @pyArgs
exit $LASTEXITCODE
