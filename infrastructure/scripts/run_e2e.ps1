#!/usr/bin/env pwsh
<#
.SYNOPSIS
    E2E Test Runner - Deterministic Test Path (Issue #354)

.DESCRIPTION
    Automated E2E test runner:
    1. Starts Claire de Binare stack (stack_up.ps1)
    2. Waits for services to be healthy
    3. Runs E2E smoke tests
    4. Tears down stack (optional)

.PARAMETER SkipStackStart
    Skip stack_up.ps1 (assume stack already running)

.PARAMETER SkipTeardown
    Keep stack running after tests (for debugging)

.PARAMETER TestPath
    Path to specific E2E test (default: all E2E tests)

.EXAMPLE
    .\infrastructure\scripts\run_e2e.ps1

.EXAMPLE
    .\infrastructure\scripts\run_e2e.ps1 -SkipStackStart -SkipTeardown

.NOTES
    Issue: #354
    Author: Team B (Engineering)
#>

[CmdletBinding()]
param(
    [switch]$SkipStackStart,
    [switch]$SkipTeardown,
    [string]$TestPath = "tests/e2e/test_smoke_pipeline.py"
)

$ErrorActionPreference = "Stop"

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "E2E Test Runner - Issue #354" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Start Stack (unless skipped)
if (-not $SkipStackStart) {
    Write-Host "📦 Starting Claire de Binare stack..." -ForegroundColor Yellow
    & ".\infrastructure\scripts\stack_up.ps1" -Logging

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
        docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml -f infrastructure/compose/logging.yml down
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
    docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml -f infrastructure/compose/logging.yml down

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
