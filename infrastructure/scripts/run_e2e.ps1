#!/usr/bin/env pwsh
<#
.SYNOPSIS
    E2E Test Runner - Canonical local E2E entry point (Issue #354, #149)

.DESCRIPTION
    Automated E2E test runner:
    1. Resolves repo root and loads secrets (CI/Test-Compose-Pfad)
    2. Starts Claire de Binare stack via docker compose (base + dev + logging)
    3. Waits for services to be healthy
    4. Runs E2E smoke tests
    5. Tears down stack (optional)

    Secrets are loaded from the single source of truth (~\Documents\.secrets\.cdb\).
    Optional .env.runtime auto-load from tools\secrets\.env.runtime (disable via CDB_IGNORE_RUNTIME_ENV=1).
    Runtime-/Operator-Pfad (BLUE+RED) is NOT used here.

.PARAMETER SkipStackStart
    Skip stack start (assume stack already running)

.PARAMETER SkipTeardown
    Keep stack running after tests (for debugging)

.PARAMETER TestPath
    Path to specific E2E test (default: tests/e2e/test_smoke_pipeline.py)

.EXAMPLE
    .\infrastructure\scripts\run_e2e.ps1

.EXAMPLE
    .\infrastructure\scripts\run_e2e.ps1 -SkipStackStart -SkipTeardown

.NOTES
    Issue: #354, #149
    Author: Team B (Engineering)
#>

[CmdletBinding()]
param(
    [switch]$SkipStackStart,
    [switch]$SkipTeardown,
    [string]$TestPath = "tests/e2e/test_smoke_pipeline.py"
)

$ErrorActionPreference = "Stop"

# --- Repo Root ---
$scriptDir = $PSScriptRoot
if (-not $scriptDir) {
    $definition = $MyInvocation.MyCommand.Definition
    $scriptDir = if ($definition) { Split-Path -Parent $definition } else { Get-Location }
}
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)

Push-Location -LiteralPath $repoRoot
try {

# --- STEP 1: SECRETS_PATH setzen (Single Source of Truth) ---
$SECRETS_PATH = Join-Path $env:USERPROFILE 'Documents\.secrets\.cdb'
[Environment]::SetEnvironmentVariable('SECRETS_PATH', $SECRETS_PATH, 'Process')

if (-not (Test-Path $SECRETS_PATH)) {
    Write-Error @"

FATAL: Secrets directory not found!
Expected: $SECRETS_PATH

Run infrastructure\scripts\init-secrets.ps1 or create manually:
  mkdir -p ~/.secrets/.cdb
  openssl rand -base64 24 > ~/.secrets/.cdb/REDIS_PASSWORD
  openssl rand -base64 24 > ~/.secrets/.cdb/POSTGRES_PASSWORD
  openssl rand -base64 24 > ~/.secrets/.cdb/GRAFANA_PASSWORD

"@
    exit 1
}

# --- STEP 2: Optional .env.runtime auto-load (same order as stack_up.ps1) ---
if ($env:CDB_IGNORE_RUNTIME_ENV -ne '1') {
    $runtimeEnvPath = Join-Path $repoRoot 'tools\secrets\.env.runtime'
    if (Test-Path $runtimeEnvPath) {
        Write-Host "Loading .env.runtime from $runtimeEnvPath" -ForegroundColor Cyan
        $loaded = 0
        Get-Content $runtimeEnvPath | ForEach-Object {
            $line = $_.Trim()
            if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith('#')) { return }
            if ($line -match '^([^=]+)=(.*)$') {
                $key = $matches[1].Trim()
                $val = $matches[2]
                [Environment]::SetEnvironmentVariable($key, $val, 'Process')
                $loaded++
            }
        }
        if ($loaded -gt 0) {
            Write-Host "  Loaded $loaded runtime env vars" -ForegroundColor Green
        }
    }
}

# --- STEP 3: Required secrets pruefen und laden ---
$requiredSecrets = @('REDIS_PASSWORD', 'POSTGRES_PASSWORD', 'GRAFANA_PASSWORD')
$missing = @()

foreach ($secret in $requiredSecrets) {
    $secretFile = Join-Path $SECRETS_PATH $secret
    if (-not (Test-Path $secretFile)) {
        $missing += $secret
    } else {
        $value = (Get-Content $secretFile -Raw).Trim()
        if ([string]::IsNullOrEmpty($value)) {
            $missing += "$secret (empty)"
        } else {
            [Environment]::SetEnvironmentVariable($secret, $value, 'Process')
        }
    }
}

if ($missing.Count -gt 0) {
    Write-Error "FATAL: Missing required secrets: $($missing -join ', ')"
    exit 1
}

# --- STEP 4: Non-secret defaults (same as stack_up.ps1) ---
[Environment]::SetEnvironmentVariable('POSTGRES_USER', 'claire_user', 'Process')
[Environment]::SetEnvironmentVariable('STACK_NAME', 'cdb', 'Process')

# --- CI/Test-Compose-Pfad (base + dev + logging) ---
$ComposeFiles = @(
    "infrastructure/compose/base.yml",
    "infrastructure/compose/dev.yml",
    "infrastructure/compose/logging.yml"
)
$ComposeArgs = ($ComposeFiles | ForEach-Object { "-f"; $_ })

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "E2E Test Runner - Issue #354, #149" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "  Secrets: $SECRETS_PATH" -ForegroundColor Gray
Write-Host "  Compose: CI/Test (base + dev + logging)" -ForegroundColor Gray
Write-Host ""

# Step 1: Start Stack (unless skipped)
if (-not $SkipStackStart) {
    Write-Host "📦 Starting Claire de Binare stack (CI/Test-Compose)..." -ForegroundColor Yellow
    docker compose @ComposeArgs up -d

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Stack start failed. Aborting E2E tests."
        exit 1
    }

    Write-Host "✅ Stack started successfully" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "⏭️  Skipping stack start (assume stack already running)" -ForegroundColor Yellow
    Write-Host ""
}

# Step 2: Wait for services to be healthy
Write-Host "⏳ Waiting for services to be healthy..." -ForegroundColor Yellow

$services = @("cdb_redis", "cdb_prometheus", "cdb_signal")
$maxWait = 60  # seconds
$elapsed = 0

while ($elapsed -lt $maxWait) {
    $allHealthy = $true

    foreach ($service in $services) {
        $health = docker inspect --format='{{.State.Health.Status}}' $service 2>$null

        if ($health -ne "healthy") {
            $allHealthy = $false
            Write-Host "  ⏳ $service not healthy yet (status: $health)" -ForegroundColor Gray
            break
        }
    }

    if ($allHealthy) {
        Write-Host "✅ All services healthy" -ForegroundColor Green
        break
    }

    Start-Sleep -Seconds 2
    $elapsed += 2
}

if ($elapsed -ge $maxWait) {
    Write-Error "Timeout waiting for services to be healthy. Check: docker ps"
    if (-not $SkipTeardown) {
        Write-Host "🧹 Tearing down stack..." -ForegroundColor Yellow
        docker compose @ComposeArgs down
    }
    exit 1
}

Write-Host ""

# Step 3: Run E2E Tests
Write-Host "🧪 Running E2E tests..." -ForegroundColor Yellow
Write-Host "  Test Path: $TestPath" -ForegroundColor Gray
Write-Host ""

# Activate venv and run pytest
& ".\.venv\Scripts\python.exe" -m pytest $TestPath -v --tb=short --no-cov

$testExitCode = $LASTEXITCODE

if ($testExitCode -eq 0) {
    Write-Host ""
    Write-Host "✅ E2E tests passed" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ E2E tests failed (exit code: $testExitCode)" -ForegroundColor Red
}

Write-Host ""

# Step 4: Teardown (unless skipped)
if (-not $SkipTeardown) {
    Write-Host "🧹 Tearing down stack..." -ForegroundColor Yellow
    docker compose @ComposeArgs down

    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Stack teardown failed (non-fatal)"
    } else {
        Write-Host "✅ Stack teardown complete" -ForegroundColor Green
    }
} else {
    Write-Host "⏭️  Skipping teardown (stack left running for debugging)" -ForegroundColor Yellow
    Write-Host "  To stop manually: docker compose down" -ForegroundColor Gray
}

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "E2E Test Runner - Complete" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

exit $testExitCode

} finally {
    Pop-Location
}
