#!/usr/bin/env pwsh
<#
.SYNOPSIS
    CDB Core Flow Smoke Test Wrapper

.DESCRIPTION
    Runs the E2E smoke test to verify core trading flow: Signal → Risk → Execution → DB

    Requires:
    - BLUE stack running (docker compose -f compose.blue.yml ps)
    - Redis + Postgres credentials available

.PARAMETER Verbose
    Enable verbose output from smoke test

.EXAMPLE
    .\smoke_test.ps1
    # Run smoke test with standard output

.EXAMPLE
    .\tools\cdb.ps1 runtime smoke
    # Canonical PowerShell v1 front door

.EXAMPLE
    .\smoke_test.ps1 -Verbose
    # Run smoke test with detailed debug output
#>

param(
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "CDB Core Flow Smoke Test" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

# Check BLUE stack is running
Write-Host "[1/3] Checking BLUE stack status..." -ForegroundColor Yellow

$composeDir = Join-Path $PSScriptRoot "..\compose"
$blueRunning = docker compose -f "$composeDir\compose.blue.yml" ps --format "table {{.Service}}\t{{.State}}" | Select-String -Pattern "running" -Quiet

if (-not $blueRunning) {
    Write-Host "  [ERROR] BLUE stack is not running" -ForegroundColor Red
    Write-Host "  Please start BLUE stack first: docker compose -f infrastructure/compose/compose.blue.yml up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host "  [OK] BLUE stack is running" -ForegroundColor Green

# Load credentials
Write-Host "`n[2/3] Loading credentials..." -ForegroundColor Yellow

$secretsPath = "$env:USERPROFILE\Documents\.secrets\.cdb"

if (-not (Test-Path "$secretsPath\REDIS_PASSWORD")) {
    Write-Error "Redis password not found at: $secretsPath\REDIS_PASSWORD"
}

if (-not (Test-Path "$secretsPath\POSTGRES_PASSWORD")) {
    Write-Error "Postgres password not found at: $secretsPath\POSTGRES_PASSWORD"
}

$env:REDIS_PASSWORD = Get-Content "$secretsPath\REDIS_PASSWORD" -Raw
$env:POSTGRES_PASSWORD = Get-Content "$secretsPath\POSTGRES_PASSWORD" -Raw

Write-Host "  [OK] Credentials loaded" -ForegroundColor Green

# Run smoke test
Write-Host "`n[3/3] Running smoke test..." -ForegroundColor Yellow

$smokeScript = Join-Path $PSScriptRoot "..\..\scripts\smoke_core_flow.py"

if (-not (Test-Path $smokeScript)) {
    Write-Error "Smoke test script not found at: $smokeScript"
}

$args = @()
if ($Verbose) {
    $args += "--verbose"
}

python $smokeScript @args

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n============================================================" -ForegroundColor Cyan
    Write-Host "[PASS] SMOKE TEST PASSED" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Core flow operational: Signal -> Risk -> Execution -> DB`n" -ForegroundColor Green
    Write-Host "Report: reports/CORE_FLOW_E2E_SMOKE.md`n" -ForegroundColor Gray
} else {
    Write-Host "`n============================================================" -ForegroundColor Cyan
    Write-Host "[FAIL] SMOKE TEST FAILED" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Check report for details: reports/CORE_FLOW_E2E_SMOKE.md`n" -ForegroundColor Yellow

    Write-Host "Common Fixes:" -ForegroundColor White
    Write-Host "  1. Check service health: docker compose -f infrastructure/compose/compose.blue.yml ps" -ForegroundColor Gray
    Write-Host "  2. Check Risk allocation: curl http://localhost:8002/status" -ForegroundColor Gray
    Write-Host "  3. View service logs: docker compose -f infrastructure/compose/compose.blue.yml logs risk execution`n" -ForegroundColor Gray

    exit 1
}
