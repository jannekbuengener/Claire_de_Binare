#Requires -Version 7.0
param(
    [Parameter(Mandatory = $true)]
    [string]$RunId
)
$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot
& python ci/scripts/run.py --cleanup $RunId
exit $LASTEXITCODE
