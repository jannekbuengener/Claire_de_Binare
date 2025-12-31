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
$ErrorActionPreference = 'Stop'

# ============================================================================
# SECRETS MANAGEMENT - SINGLE SOURCE OF TRUTH
# ============================================================================
# Secrets are ONLY loaded from: ~/.secrets/.cdb/
# NO .env files, NO env_file: directives, NO hardcoded values
# ============================================================================

$SECRETS_PATH = Join-Path $env:USERPROFILE 'Documents\.secrets\.cdb'

function Set-SecretsPath {
    <#
    .SYNOPSIS
    Sets SECRETS_PATH environment variable for Docker Compose.

    .DESCRIPTION
    Docker Compose secrets: directive uses ${SECRETS_PATH} variable.
    This sets it to the Single Source of Truth location.
    #>

    [Environment]::SetEnvironmentVariable('SECRETS_PATH', $SECRETS_PATH, 'Process')
    Write-Host "  [OK] SECRETS_PATH=$SECRETS_PATH" -ForegroundColor Green
}

function Load-Secrets {
    <#
    .SYNOPSIS
    Loads secrets from the single source of truth.

    .DESCRIPTION
    Reads secrets from ~/.secrets/.cdb/ and sets them as environment variables.
    Fails HARD if any required secret is missing.
    #>

    Write-Host "`n=== Loading Secrets ===" -ForegroundColor Cyan
    Write-Host "Source: $SECRETS_PATH" -ForegroundColor Gray

    if (-not (Test-Path $SECRETS_PATH)) {
        Write-Error @"

FATAL: Secrets directory not found!
Expected: $SECRETS_PATH

Create it with:
  mkdir -p ~/.secrets/.cdb
  openssl rand -base64 24 > ~/.secrets/.cdb/REDIS_PASSWORD
  openssl rand -base64 24 > ~/.secrets/.cdb/POSTGRES_PASSWORD
  openssl rand -base64 24 > ~/.secrets/.cdb/GRAFANA_PASSWORD

"@
        exit 1
    }

    $requiredSecrets = @(
        'REDIS_PASSWORD',
        'POSTGRES_PASSWORD',
        'GRAFANA_PASSWORD'
    )

    $missing = @()

    foreach ($secret in $requiredSecrets) {
        $secretPath = Join-Path $SECRETS_PATH $secret
        if (-not (Test-Path $secretPath)) {
            $missing += $secret
        } else {
            $value = (Get-Content $secretPath -Raw).Trim()
            if ([string]::IsNullOrEmpty($value)) {
                $missing += "$secret (empty)"
            } else {
                # Set environment variable for this process
                [Environment]::SetEnvironmentVariable($secret, $value, 'Process')
                Write-Host "  [OK] $secret" -ForegroundColor Green
            }
        }
    }

    if ($missing.Count -gt 0) {
        Write-Error @"

FATAL: Missing required secrets!
$($missing -join "`n")

Generate missing secrets:
  openssl rand -base64 24 > $SECRETS_PATH\<SECRET_NAME>

"@
        exit 1
    }

    # Set non-secret defaults
    [Environment]::SetEnvironmentVariable('POSTGRES_USER', 'claire_user', 'Process')
    [Environment]::SetEnvironmentVariable('STACK_NAME', 'cdb', 'Process')

    Write-Host "  [OK] All secrets loaded" -ForegroundColor Green
}

# ============================================================================
# MAIN SCRIPT
# ============================================================================

$scriptDir = $PSScriptRoot
if (-not $scriptDir) {
    $definition = $MyInvocation.MyCommand.Definition
    $scriptDir = if ($definition) { Split-Path -Parent $definition } else { Get-Location }
}
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)

Push-Location -LiteralPath $repoRoot
try {
    # STEP 1: Set SECRETS_PATH for Docker Compose
    Set-SecretsPath

    # STEP 2: Load and validate secrets from single source
    Load-Secrets

    # STEP 2: Build compose file list (NO --env-file!)
    $composeArgs = @(
        '-f', 'infrastructure\compose\base.yml'
    )

    if ($Profile -eq 'dev') {
        $composeArgs += '-f', 'infrastructure\compose\dev.yml'
    }

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
        Write-Host "Network isolation enabled" -ForegroundColor Cyan
    }

    if ($TLS) {
        $documentsDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $repoRoot))
        $tlsDir = Join-Path $documentsDir '.cdb_local\tls'
        if (-not (Test-Path $tlsDir)) {
            Write-Error "TLS certificates not found at $tlsDir"
            exit 1
        }
        $requiredCerts = @('ca.crt', 'redis.crt', 'redis.key', 'postgres.crt', 'postgres.key', 'client.crt', 'client.key')
        $missingCerts = $requiredCerts | Where-Object { -not (Test-Path (Join-Path $tlsDir $_)) }
        if ($missingCerts) {
            Write-Error "Missing TLS certificates: $($missingCerts -join ', ')"
            exit 1
        }
        $composeArgs += '-f', 'infrastructure\compose\tls.yml'
        Write-Host "TLS enabled (Redis + PostgreSQL encrypted)" -ForegroundColor Green
    }

    # Target services
    $targetServices = @(
        'cdb_redis', 'cdb_postgres', 'cdb_prometheus', 'cdb_grafana',
        'cdb_signal', 'cdb_risk', 'cdb_execution', 'cdb_db_writer',
        'cdb_ws', 'cdb_paper_runner'
    )

    function Invoke-StackCompose {
        param([string[]]$CommandArgs)
        $cmd = @('compose') + $composeArgs + $CommandArgs
        & 'docker' @cmd
    }

    Write-Host "`n=== Starting Claire de Binare Stack ===" -ForegroundColor Cyan
    Write-Host "Profile: $Profile" -ForegroundColor Yellow
    Write-Host "Secrets: Loaded from $SECRETS_PATH" -ForegroundColor Yellow

    $upArgs = @('up', '-d')
    if ($Rebuild.IsPresent) {
        $upArgs += '--build'
    }
    $upArgs += $targetServices

    Invoke-StackCompose -CommandArgs $upArgs
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose up failed with exit code $LASTEXITCODE"
    }

    # Wait for healthy
    $timeoutSeconds = 120
    $deadline = (Get-Date).AddSeconds($timeoutSeconds)
    $pending = @()
    while ((Get-Date) -lt $deadline) {
        $psOutput = Invoke-StackCompose -CommandArgs @('ps', '--format', '{{json .}}')
        $statusList = @()
        $parsed = $false
        if ($psOutput) {
            $firstLine = $psOutput[0].Trim()
            if (-not $firstLine.StartsWith('Usage:')) {
                try {
                    $statusList = $psOutput | ConvertFrom-Json
                    $parsed = $true
                } catch { }
            }
        }

        if ($parsed) {
            $pending = $statusList | Where-Object { $targetServices -contains $_.Service } | Where-Object {
                $_.State -ne 'running' -or ($null -ne $_.Health -and $_.Health -ne 'healthy')
            }
            if (-not $pending) {
                Write-Host "`nAll services are running and healthy." -ForegroundColor Green
                break
            }
        } else {
            $pending = $targetServices
        }

        $waiting = $pending | Sort-Object -Unique
        Write-Host "Waiting for: $($waiting -join ', ')" -ForegroundColor Yellow
        Start-Sleep -Seconds 5
    }

    if ($pending) {
        $pendingCount = @($pending).Count
        if ($pendingCount -gt 0) {
            Write-Warning "Timeout waiting for: $($pending -join ', ')"
        }
    }

    Invoke-StackCompose -CommandArgs @('ps')

    # Verification
    Write-Host "`n=== Stack Verification ===" -ForegroundColor Cyan
    $verifyScript = Join-Path $scriptDir 'stack_verify.ps1'
    if (Test-Path $verifyScript) {
        & $verifyScript
    }
} finally {
    Pop-Location
}
