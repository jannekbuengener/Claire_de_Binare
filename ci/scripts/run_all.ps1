#Requires -Version 7.0
<#
.SYNOPSIS
  Preferred Windows front door for CDB local Docker CI Phase 1.
.DESCRIPTION
  Delegates to the canonical Python orchestrator ci/scripts/run.py.
  Local evidence is NOT a GitHub Required Check.
#>
param(
    [ValidateSet("fast", "heavy")]
    [string]$Profile = "fast",
    [string]$Stage = "",
    [string]$RunId = "",
    [switch]$Report,
    [string]$Cleanup = ""
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

$pyArgs = @("ci/scripts/run.py")
if ($Report) {
    $pyArgs += "--report"
}
elseif ($Cleanup) {
    $pyArgs += @("--cleanup", $Cleanup)
}
else {
    $pyArgs += @("--profile", $Profile)
    if ($Stage) { $pyArgs += @("--stage", $Stage) }
    if ($RunId) { $pyArgs += @("--run-id", $RunId) }
}

Write-Host "CDB local CI → $PythonExe $($pyArgs -join ' ')"
& $PythonExe @pyArgs
exit $LASTEXITCODE
