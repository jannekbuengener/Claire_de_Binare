param(
    [switch]$Rebuild,
    [ValidateSet('dev', 'prod')]
    [string]$Profile = 'dev',
    [switch]$Logging,
    [switch]$StrictHealth,
    [switch]$NetworkIsolation,
    [switch]$TLS
)

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

    # Build compose file list based on profile and switches
    # NOTE: Removed legacy docker-compose.base.yml reference (2025-12-24)
    # Using canonical infrastructure/compose/base.yml only
    $composeArgs = @(
        '--env-file', '.\.cdb_local\.secrets\.env.compose',
        '-f', 'infrastructure\compose\base.yml'
    )

    # Add profile-specific overlay
    if ($Profile -eq 'dev') {
        $composeArgs += '-f', 'infrastructure\compose\dev.yml'
    }
    elseif ($Profile -eq 'prod') {
        # Prod overlay (currently none, but ready for future)
        # Future: Add network-prod.yml here
    }

    # Add optional overlays
    if ($Logging) {
        $composeArgs += '-f', 'infrastructure\compose\logging.yml'
        Write-Host "Logging overlay enabled (Loki + Promtail)" -ForegroundColor Cyan
    }

    if ($StrictHealth) {
        $composeArgs += '-f', 'infrastructure\compose\healthchecks-strict.yml'
        $composeArgs += '-f', 'infrastructure\compose\healthchecks-mounts.yml'
        Write-Host "Strict healthchecks enabled" -ForegroundColor Cyan
    }

    if ($NetworkIsolation) {
        $composeArgs += '-f', 'infrastructure\compose\network-prod.yml'
        Write-Host "Network isolation enabled (internal: true)" -ForegroundColor Cyan
    }

    if ($TLS) {
        # Verify TLS certificates exist
        # Path: Documents/.cdb_local/tls (4 levels up from repo root)
        $documentsDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $repoRoot))
        $tlsDir = Join-Path $documentsDir '.cdb_local\tls'
        if (-not (Test-Path $tlsDir)) {
            Write-Error "TLS certificates not found at $tlsDir"
            Write-Error "Run: bash infrastructure/tls/generate_certs.sh $tlsDir"
            exit 1
        }
        $requiredCerts = @('ca.crt', 'redis.crt', 'redis.key', 'postgres.crt', 'postgres.key', 'client.crt', 'client.key')
        $missingCerts = $requiredCerts | Where-Object { -not (Test-Path (Join-Path $tlsDir $_)) }
        if ($missingCerts) {
            Write-Error "Missing TLS certificates: $($missingCerts -join ', ')"
            Write-Error "Run: bash infrastructure/tls/generate_certs.sh $tlsDir"
            exit 1
        }
        $composeArgs += '-f', 'infrastructure\compose\tls.yml'
        Write-Host "TLS enabled (Redis + PostgreSQL encrypted)" -ForegroundColor Green
    }

    # SERVICE_CATALOG.md: Alle AKTIV-Services (Stand 2025-12-28)
    $targetServices = @(
        # Infrastruktur
        'cdb_redis',
        'cdb_postgres',
        'cdb_prometheus',
        'cdb_grafana',
        # Applikation
        'cdb_core',
        'cdb_risk',
        'cdb_execution',
        'cdb_db_writer',
        'cdb_ws',
        'cdb_paper_runner'
        # BEREIT aber deaktiviert (siehe SERVICE_CATALOG.md):
        # 'cdb_allocation',    # Fehlende Env-Vars (ALLOCATION_*)
        # 'cdb_regime',        # Fehlende Env-Vars (REGIME_*)
        # 'cdb_market',        # service.py existiert, aber in dev.yml auskommentiert
        # GAP: cdb_signal - Code existiert, kein Compose-Eintrag!
    )

    function Invoke-StackCompose {
        param([string[]]$CommandArgs)
        $cmd = @('compose') + $composeArgs + $CommandArgs
        & 'docker' @cmd
    }

    Write-Host "=== Starting Claire de Binare Stack ===" -ForegroundColor Cyan
    Write-Host "Profile: $Profile" -ForegroundColor Yellow
    if ($Logging -or $StrictHealth -or $NetworkIsolation -or $TLS) {
        Write-Host "Overlays: $(if($Logging){'Logging '})$(if($StrictHealth){'StrictHealth '})$(if($NetworkIsolation){'NetworkIsolation '})$(if($TLS){'TLS'})" -ForegroundColor Yellow
    }
    Write-Host "Referenz: governance/SERVICE_CATALOG.md`n" -ForegroundColor Gray

    $upArgs = @('up', '-d')
    if ($Rebuild.IsPresent) {
        $upArgs += '--build'
    }
    $upArgs += $targetServices

    Invoke-StackCompose -CommandArgs $upArgs
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose up failed with exit code $LASTEXITCODE"
    }

    $timeoutSeconds = 120
    $deadline = (Get-Date).AddSeconds($timeoutSeconds)
    $pending = @()
    $warnedAboutUsage = $false
    while ((Get-Date) -lt $deadline) {
        $psOutput = Invoke-StackCompose -CommandArgs @('ps', '--format', '{{json .}}')
        $statusList = @()
        $parsed = $false
        if ($psOutput) {
            $firstLine = $psOutput[0].Trim()
            if ($firstLine.StartsWith('Usage:')) {
                if (-not $warnedAboutUsage) {
                    Write-Host 'docker compose ps returned the usage banner; retrying...' -ForegroundColor Yellow
                    $warnedAboutUsage = $true
                }
            } else {
                try {
                    $statusList = $psOutput | ConvertFrom-Json
                    $parsed = $true
                } catch {
                    Write-Host 'Unable to parse docker compose ps output; retrying...' -ForegroundColor Yellow
                }
            }
        }

        if ($parsed) {
            $pending = $statusList | Where-Object { $targetServices -contains $_.Service } | Where-Object {
                $_.State -ne 'running' -or ($null -ne $_.Health -and $_.Health -ne 'healthy')
            }
            if (-not $pending) {
                Write-Host 'All targeted services are running and healthy.'
                break
            }
        } else {
            $pending = $targetServices
        }

        $waiting = $pending | Sort-Object -Unique
        $waitingMessage = if ($waiting) { $waiting -join ', ' } else { 'unknown services' }
        Write-Host ("Waiting for: {0}" -f $waitingMessage) -ForegroundColor Yellow
        Start-Sleep -Seconds 5
    }

    if ($pending -and $pending.Count -gt 0) {
        $names = $pending | Sort-Object -Unique
        Write-Warning ("Timeout waiting for healthy services: {0}" -f ($names -join ', '))
    }

    Invoke-StackCompose -CommandArgs @('ps')

    # Stack-Vollständigkeitsprüfung (Governance)
    Write-Host "`n=== Stack Verification ===" -ForegroundColor Cyan
    $verifyScript = Join-Path $scriptDir 'stack_verify.ps1'
    if (Test-Path $verifyScript) {
        & $verifyScript
    } else {
        Write-Warning "stack_verify.ps1 nicht gefunden - manuelle Prüfung erforderlich"
    }
} finally {
    Pop-Location
}
