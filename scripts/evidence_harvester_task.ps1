param(
    [ValidateSet('plan', 'status', 'run-once-fixture', 'install', 'uninstall')]
    [string]$Action = 'plan',
    [string]$TaskName = 'CDB Evidence Harvester',
    [string]$Fixture,
    [string]$OutputDir,
    [string]$PythonExecutable = 'python',
    [string]$GeneratedAtUtc,
    [string]$StartTime = '04:00',
    [switch]$Explicit,
    [switch]$Pretty
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$moduleArgs = @('-m', 'tools.evidence_harvester.scheduler', $Action, '--task-name', $TaskName)

if ($OutputDir) {
    $moduleArgs += @('--output-dir', $OutputDir)
}
if ($Fixture) {
    $moduleArgs += @('--fixture', $Fixture)
}
if ($GeneratedAtUtc) {
    $moduleArgs += @('--generated-at-utc', $GeneratedAtUtc)
}
if ($Action -in @('plan', 'install') -and $StartTime) {
    $moduleArgs += @('--start-time', $StartTime)
}
if ($Pretty) {
    $moduleArgs += '--pretty'
}
if ($Action -in @('install', 'uninstall')) {
    if (-not $Explicit) {
        throw "$Action requires -Explicit. Default mode remains dry-run/plan-only."
    }
    $moduleArgs += '--explicit'
}
if ($Action -in @('plan', 'install')) {
    $moduleArgs += @('--python-executable', $PythonExecutable)
}

& $PythonExecutable @moduleArgs
exit $LASTEXITCODE
