<#
.SYNOPSIS
    One-Click Local Bootstrap for Claire de Binare (Windows/PowerShell)

.DESCRIPTION
    This script initializes secrets, creates .env, validates the environment,
    starts the Docker stack, and runs basic health checks.

.EXAMPLE
    .\infrastructure\scripts\bootstrap_local.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host "=== Claire de Binare - Local Bootstrap ===" -ForegroundColor Cyan

# 1. Initialize Secrets
Write-Host "`n1. Initializing secrets..." -ForegroundColor Yellow
& "$PSScriptRoot\init-secrets.ps1"

# 2. Setup Environment File
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot

if (-not (Test-Path ".env")) {
    Write-Host "`n2. Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "  [OK] .env created" -ForegroundColor Green
} else {
    Write-Host "`n2. .env already exists, skipping..." -ForegroundColor Yellow
}

# 3. Validate Environment
Write-Host "`n3. Validating environment..." -ForegroundColor Yellow
& "$PSScriptRoot\check_env.ps1"  # Or stack_doctor if preferred

# 4. Start Docker Stack
Write-Host "`n4. Starting Docker Compose stack..." -ForegroundColor Yellow
& "$PSScriptRoot\stack_up.ps1"

# 5. Health Check Loop
Write-Host "`n5. Waiting for services to be healthy..." -ForegroundColor Yellow
$maxRetries = 30
$count = 0
$targetServices = @('cdb_redis', 'cdb_postgres', 'cdb_prometheus', 'cdb_grafana', 'cdb_ws', 'cdb_signal')

while ($count -lt $maxRetries) {
    $allHealthy = $true
    foreach ($svc in $targetServices) {
        $health = docker inspect --format='{{.State.Health.Status}}' $svc 2>$null
        if ($health -ne "healthy") {
            $allHealthy = $false
            Write-Host "   Waiting for $svc (status: $health)..." -ForegroundColor Gray
            break
        }
    }

    if ($allHealthy) {
        Write-Host "  [OK] All core services are healthy!" -ForegroundColor Green
        break
    }

    Start-Sleep -Seconds 5
    $count++
}

if ($count -eq $maxRetries) {
    Write-Warning "Timeout waiting for services to be healthy. Some services might still be initializing."
}

# 6. Basic Smoke Test
Write-Host "`n6. Running basic smoke test..." -ForegroundColor Yellow
try {
    $wsHealth = Invoke-RestMethod -Uri "http://localhost:8000/health" -ErrorAction SilentlyContinue
    if ($wsHealth.status -eq "healthy") {
        Write-Host "  [PASS] WS Service healthy" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] WS Service health status: $($wsHealth.status)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [WARN] WS Service health check failed (port not reachable)" -ForegroundColor Yellow
}

# 7. Database Check
Write-Host "`n7. Checking database status..." -ForegroundColor Yellow
try {
    $dbCheck = docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "\dt" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] Database connection and tables verified" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Could not verify database tables (is it still initializing?)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [WARN] Database check failed" -ForegroundColor Yellow
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Bootstrap complete!" -ForegroundColor Green
Write-Host "Access Grafana at http://localhost:3000 (admin / see secrets)"
Write-Host "Run tests with: make test"
Write-Host "==========================================" -ForegroundColor Cyan

Pop-Location
