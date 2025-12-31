# IMMEDIATE LIVE DATA ACTIVATION SCRIPT
Write-Host "🚨 ACTIVATING LIVE DATA MODE - NO MORE MOCK" -ForegroundColor Red

# Copy live data config to active .env
Copy-Item ".env.live_data" ".env" -Force
Write-Host "✅ Environment configured for LIVE DATA" -ForegroundColor Green

# Restart services with LIVE DATA
Write-Host "🔄 Restarting services with LIVE DATA..." -ForegroundColor Yellow
docker-compose down
docker-compose up -d

Write-Host "🎯 LIVE DATA MODE ACTIVATED!" -ForegroundColor Green
Write-Host "   • MockExecutor → MexcExecutor (REAL API)" -ForegroundColor White
Write-Host "   • test_balance → real_balance (REAL MONEY)" -ForegroundColor White
Write-Host "   • fake validation → real_validation (REAL RESULTS)" -ForegroundColor White
Write-Host "   • All market data now LIVE" -ForegroundColor White

Write-Host ""
Write-Host "⚠️  CAUTION: SYSTEM NOW USES REAL DATA AND REAL MONEY" -ForegroundColor Red
