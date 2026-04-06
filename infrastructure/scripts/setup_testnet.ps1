#!/usr/bin/env pwsh
# ============================================================================
# LEGACY SCRIPT — .env-based testnet setup (pre-Blue/Red canon)
# ============================================================================
# This script reads MEXC credentials from a flat .env file.
# The current runtime uses Docker secrets from ~/Documents/.secrets/.cdb/
# and the Blue/Red compose canon.
#
# Canonical runtime entry points:
#   .\tools\cdb.ps1 secrets init                           (secret setup)
#   .\tools\cdb.ps1 runtime up                             (start stack)
#   docker compose -f infrastructure/compose/compose.blue.yml up -d
#   docker compose -f infrastructure/compose/compose.red.yml  up -d
# ============================================================================
<#
.SYNOPSIS
    LEGACY: MEXC Testnet Setup & Validation Script (.env-based)
.DESCRIPTION
    Helps configure MEXC testnet credentials and validates the connection.
    NOTE: This script uses the legacy .env model. The current runtime uses
    Docker secrets — see .\tools\cdb.ps1 secrets init.
.EXAMPLE
    .\setup_testnet.ps1
#>

param(
    [switch]$SkipValidation,
    [switch]$Help
)

if ($Help) {
    Get-Help $MyInvocation.MyCommand.Path -Detailed
    exit 0
}

Write-Host "ERROR: This script is legacy and must not be used." -ForegroundColor Red
Write-Host ""
Write-Host "The current runtime uses Docker secrets and the Blue/Red compose canon." -ForegroundColor Yellow
Write-Host "Canonical entry points:" -ForegroundColor Yellow
Write-Host "  .\tools\cdb.ps1 secrets init    (secret setup)" -ForegroundColor White
Write-Host "  .\tools\cdb.ps1 runtime up       (full BLUE+RED stack restart)" -ForegroundColor White
exit 1

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

Write-Host "`n🧪 MEXC Testnet Setup" -ForegroundColor Cyan
Write-Host "=" * 50

# Check if .env exists
$envPath = Join-Path $PSScriptRoot ".." ".env"
if (-not (Test-Path $envPath)) {
    Write-Host "❌ .env file not found at: $envPath" -ForegroundColor Red
    exit 1
}

Write-Host "`n📋 Current Configuration:" -ForegroundColor Yellow
Write-Host "-" * 50

# Read current config
$envContent = Get-Content $envPath -Raw
$mexcApiKey = if ($envContent -match 'MEXC_API_KEY=([^\r\n]*)') { $matches[1].Trim() } else { "" }
$mexcApiSecret = if ($envContent -match 'MEXC_API_SECRET=([^\r\n]*)') { $matches[1].Trim() } else { "" }
$mexcTestnet = if ($envContent -match 'MEXC_TESTNET=(true|false)') { $matches[1] } else { "true" }
$mockTrading = if ($envContent -match 'MOCK_TRADING=(true|false)') { $matches[1] } else { "false" }
$dryRun = if ($envContent -match 'DRY_RUN=(true|false)') { $matches[1] } else { "true" }

Write-Host "  MEXC_TESTNET:    $mexcTestnet" -ForegroundColor $(if ($mexcTestnet -eq "true") { "Green" } else { "Red" })
Write-Host "  MOCK_TRADING:    $mockTrading" -ForegroundColor $(if ($mockTrading -eq "false") { "Green" } else { "Yellow" })
Write-Host "  DRY_RUN:         $dryRun" -ForegroundColor $(if ($dryRun -eq "true") { "Green" } else { "Yellow" })
Write-Host "  MEXC_API_KEY:    $(if ($mexcApiKey) { '[SET]' } else { '[NOT SET]' })" -ForegroundColor $(if ($mexcApiKey) { "Green" } else { "Red" })
Write-Host "  MEXC_API_SECRET: $(if ($mexcApiSecret) { '[SET]' } else { '[NOT SET]' })" -ForegroundColor $(if ($mexcApiSecret) { "Green" } else { "Red" })

# Check if credentials are set
if (-not $mexcApiKey -or -not $mexcApiSecret) {
    Write-Host "`n⚠️  MEXC API credentials not configured!" -ForegroundColor Yellow
    Write-Host "`n📝 How to get MEXC Testnet credentials:" -ForegroundColor Cyan
    Write-Host "   1. Go to: https://testnet.mexc.com/" -ForegroundColor White
    Write-Host "   2. Create account or login" -ForegroundColor White
    Write-Host "   3. Go to API Management" -ForegroundColor White
    Write-Host "   4. Create new API Key" -ForegroundColor White
    Write-Host "   5. Copy API Key and Secret" -ForegroundColor White
    Write-Host "   6. Edit .env and set MEXC_API_KEY and MEXC_API_SECRET" -ForegroundColor White
    Write-Host "`n   Note: Testnet uses FAKE money - safe for testing!" -ForegroundColor Green
    exit 0
}

Write-Host "`n✅ MEXC API credentials configured" -ForegroundColor Green

# Validate configuration
Write-Host "`n🔍 Validating Configuration..." -ForegroundColor Cyan
Write-Host "-" * 50

$issues = @()

if ($mexcTestnet -ne "true") {
    $issues += "⚠️  MEXC_TESTNET should be 'true' for safe testing"
}

if ($mockTrading -eq "true") {
    Write-Host "  ⚠️  MOCK_TRADING=true (using mock executor, not MEXC API)" -ForegroundColor Yellow
}

if ($dryRun -ne "true") {
    $issues += "⚠️  DRY_RUN should be 'true' for initial testing (prevents real order execution)"
}

if ($issues.Count -gt 0) {
    Write-Host "`n⚠️  Configuration Issues Found:" -ForegroundColor Yellow
    foreach ($issue in $issues) {
        Write-Host "  $issue" -ForegroundColor Yellow
    }
    Write-Host "`n  Edit .env to fix these issues before testing." -ForegroundColor Yellow
} else {
    Write-Host "`n✅ Configuration looks good!" -ForegroundColor Green
}

# Test MEXC API connection
if (-not $SkipValidation) {
    Write-Host "`n🔌 Testing MEXC Testnet Connection..." -ForegroundColor Cyan
    Write-Host "-" * 50

    try {
        # Run Python test script
        $testScript = @"
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'execution'))

from mexc_client import MexcClient

try:
    # Initialize client in testnet mode
    client = MexcClient(testnet=True)

    # Test balance query (read-only operation)
    balance = client.get_balance('USDT')
    print(f'✅ Connection successful!')
    print(f'   Testnet USDT Balance: {balance:.2f}')

    # Test ticker price (public endpoint)
    btc_price = client.get_ticker_price('BTCUSDT')
    print(f'   BTC/USDT Price: {btc_price:.2f}')

except Exception as e:
    print(f'❌ Connection failed: {e}')
    sys.exit(1)
"@

        $testScript | python -

        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n✅ Testnet connection validated!" -ForegroundColor Green
        } else {
            Write-Host "`n❌ Testnet connection failed" -ForegroundColor Red
            exit 1
        }

    } catch {
        Write-Host "`n❌ Validation failed: $_" -ForegroundColor Red
        Write-Host "   Make sure Python dependencies are installed: pip install requests" -ForegroundColor Yellow
        exit 1
    }
}

# Summary
Write-Host "`n📊 Setup Summary" -ForegroundColor Cyan
Write-Host "=" * 50

Write-Host "`n✅ MEXC Testnet is ready for testing!" -ForegroundColor Green
Write-Host "`n🎯 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Start services: .\tools\cdb.ps1 runtime up" -ForegroundColor White
Write-Host "     (or: docker compose -f infrastructure/compose/compose.blue.yml up -d)" -ForegroundColor DarkGray
Write-Host "  2. Monitor logs: docker logs -f cdb_execution" -ForegroundColor White
Write-Host "  3. Test order flow: python tests/test_mexc_integration.py" -ForegroundColor White
Write-Host "`n💡 Trading Modes:" -ForegroundColor Cyan
Write-Host "  • DRY_RUN=true:       Orders logged but NOT executed (safest)" -ForegroundColor Green
Write-Host "  • DRY_RUN=false:      Orders sent to MEXC Testnet (fake money)" -ForegroundColor Yellow
Write-Host "  • MEXC_TESTNET=false: LIVE TRADING - REAL MONEY! (⚠️  NOT RECOMMENDED)" -ForegroundColor Red
Write-Host ""
