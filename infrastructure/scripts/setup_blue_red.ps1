#!/usr/bin/env pwsh
<#
.SYNOPSIS
    CDB Blue/Red Stack Setup - One-Time Network Creation + Initial Start

.DESCRIPTION
    Creates shared Docker network and starts BLUE (core) and optionally RED (monitoring) stacks.

    BLUE Stack (Always-On):
    - Data: postgres, redis
    - Control: candles, regime, allocation
    - Core: risk, execution, db_writer, paper_runner

    RED Stack (Optional):
    - Signal: ws, signal
    - Monitoring: prometheus, grafana, exporters, reports

.PARAMETER SkipRed
    Only start BLUE stack (core trading), skip RED (monitoring/signals)

.PARAMETER SkipSmokeTest
    Skip smoke test after BLUE startup

.EXAMPLE
    .\setup_blue_red.ps1
    # Start BLUE + RED with smoke test

.EXAMPLE
    .\tools\cdb.ps1 runtime up
    # Canonical PowerShell v1 front door

.EXAMPLE
    .\setup_blue_red.ps1 -SkipRed
    # Start BLUE only (for manual signal injection testing)
#>

param(
    [switch]$SkipRed,
    [switch]$SkipSmokeTest
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "CDB Blue/Red Stack Setup" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

# ==================== NETWORK ====================

Write-Host "[1/4] Checking Docker network..." -ForegroundColor Yellow

$networkExists = docker network ls --filter "name=cdb_network" --format "{{.Name}}" | Select-String -Pattern "^cdb_network$" -Quiet

if ($networkExists) {
    Write-Host "  [OK] Network 'cdb_network' exists" -ForegroundColor Green
} else {
    Write-Host "  [CREATE] Creating network 'cdb_network'..." -ForegroundColor Yellow
    docker network create cdb_network
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create network"
    }
    Write-Host "  [OK] Network created" -ForegroundColor Green
}

# ==================== SECRETS_PATH ====================

if (-not $env:SECRETS_PATH) {
    $env:SECRETS_PATH = Join-Path $env:USERPROFILE "Documents\.secrets\.cdb"
}
if (-not (Test-Path $env:SECRETS_PATH)) {
    Write-Error "Secrets directory not found: $env:SECRETS_PATH. Set SECRETS_PATH env var or create the directory."
}
Write-Host "SECRETS_PATH: $env:SECRETS_PATH" -ForegroundColor Gray

# ==================== BLUE STACK ====================

Write-Host "`n[2/4] Starting BLUE stack (core trading)..." -ForegroundColor Yellow

$composeDir = Join-Path $PSScriptRoot "..\compose"
Push-Location $composeDir

try {
    docker compose -f compose.blue.yml up -d --build

    if ($LASTEXITCODE -ne 0) {
        Write-Error "BLUE stack startup failed"
    }

    Write-Host "  [OK] BLUE stack started" -ForegroundColor Green

    # Wait for services to be healthy
    Write-Host "  [WAIT] Waiting 10s for services to stabilize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10

} finally {
    Pop-Location
}

# ==================== SMOKE TEST ====================

if (-not $SkipSmokeTest) {
    Write-Host "`n[3/4] Running core flow smoke test..." -ForegroundColor Yellow

    $smokeScript = Join-Path $PSScriptRoot "..\..\scripts\smoke_core_flow.py"

    if (Test-Path $smokeScript) {
        $env:REDIS_PASSWORD = (Get-Content (Join-Path $env:SECRETS_PATH "REDIS_PASSWORD") -Raw).Trim()
        $env:POSTGRES_PASSWORD = (Get-Content (Join-Path $env:SECRETS_PATH "POSTGRES_PASSWORD") -Raw).Trim()

        python $smokeScript

        if ($LASTEXITCODE -ne 0) {
            Write-Host "  [WARNING] Smoke test FAILED - check reports/CORE_FLOW_E2E_SMOKE.md" -ForegroundColor Red
            Write-Host "  BLUE stack is running but core flow is not verified" -ForegroundColor Yellow
        } else {
            Write-Host "  [OK] Smoke test PASSED" -ForegroundColor Green
        }
    } else {
        Write-Host "  [SKIP] Smoke test script not found: $smokeScript" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n[3/4] Skipping smoke test (--SkipSmokeTest)" -ForegroundColor Yellow
}

# ==================== RED STACK ====================

if (-not $SkipRed) {
    Write-Host "`n[4/4] Starting RED stack (signals + monitoring)..." -ForegroundColor Yellow

    Push-Location $composeDir

    try {
        docker compose -f compose.red.yml up -d --build

        if ($LASTEXITCODE -ne 0) {
            Write-Host "  [WARNING] RED stack startup failed" -ForegroundColor Red
            Write-Host "  BLUE stack is still operational" -ForegroundColor Yellow
        } else {
            Write-Host "  [OK] RED stack started" -ForegroundColor Green
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "`n[4/4] Skipping RED stack (--SkipRed)" -ForegroundColor Yellow
}

# ==================== SUMMARY ====================

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "Setup Complete" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

Write-Host "BLUE Stack (Core):" -ForegroundColor White
Write-Host "  - Status: " -NoNewline
docker compose -f "$composeDir\compose.blue.yml" ps --format "table {{.Service}}\t{{.Status}}" | Select-String -Pattern "Up" -Quiet
if ($?) {
    Write-Host "Running" -ForegroundColor Green
} else {
    Write-Host "Issues detected" -ForegroundColor Red
}

if (-not $SkipRed) {
    Write-Host "`nRED Stack (Optional):" -ForegroundColor White
    Write-Host "  - Status: " -NoNewline
    docker compose -f "$composeDir\compose.red.yml" ps --format "table {{.Service}}\t{{.Status}}" | Select-String -Pattern "Up" -Quiet
    if ($?) {
        Write-Host "Running" -ForegroundColor Green
    } else {
        Write-Host "Issues detected (non-blocking)" -ForegroundColor Yellow
    }
}

Write-Host "`nNext Steps:" -ForegroundColor White
Write-Host "  1. Check service status: docker compose -f infrastructure/compose/compose.blue.yml ps" -ForegroundColor Gray
Write-Host "  2. View logs: docker compose -f infrastructure/compose/compose.blue.yml logs -f" -ForegroundColor Gray
Write-Host "  3. Grafana: http://localhost:3000 (admin/password from secrets)" -ForegroundColor Gray
Write-Host "  4. Re-run smoke test: .\tools\cdb.ps1 runtime smoke -Verbose`n" -ForegroundColor Gray
