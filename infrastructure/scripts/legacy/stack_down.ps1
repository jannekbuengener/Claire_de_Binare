# LEGACY — superseded by BLUE/RED compose split (compose.blue.yml + compose.red.yml).
# Still references .cdb_local/.secrets/.env.compose and the old base.yml/dev.yml topology.
# Canonical stack-down: docker compose -f infrastructure/compose/compose.blue.yml down
# Retained for reference only; do not use as an active entrypoint.

Set-StrictMode -Version Latest

$scriptDir = $PSScriptRoot
if (-not $scriptDir) {
    $definition = $MyInvocation.MyCommand.Definition
    $scriptDir = if ($definition) { Split-Path -Parent $definition } else { Get-Location }
}
$repoRoot = Split-Path -Parent $scriptDir

Push-Location -LiteralPath $repoRoot
try {
    $envFile = '.\.cdb_local\.secrets\.env.compose'
    if (-not (Test-Path $envFile)) {
        Write-Error "Missing compose env file at $envFile"
        exit 1
    }

    $composeArgs = @(
        '--env-file', '.\.cdb_local\.secrets\.env.compose',
        '-f', 'docker-compose.base.yml',
        '-f', 'infrastructure\compose\base.yml',
        '-f', 'infrastructure\compose\dev.yml'
    )

    function Invoke-StackCompose {
        param([string[]]$Args)
        $cmd = @('compose') + $composeArgs + $Args
        & 'docker' @cmd
    }

    Write-Host 'Stopping Claire_de_Binare stack (cdb_ws excluded; volumes are preserved).'

    Invoke-StackCompose -Args @('down')
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose down failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}
