# ============================================================================
# LEGACY SCRIPT — DO NOT USE
# ============================================================================
# This script predates the Blue/Red compose canon and Docker-secrets model.
# It assumes .env-file-based configuration and an unqualified docker-compose.yml,
# neither of which reflect the current runtime architecture.
#
# Canonical entry points:
#   .\tools\cdb.ps1 runtime up      (PowerShell v1 front door — full BLUE+RED restart)
#   .\tools\cdb.ps1 secrets init    (secret setup)
#
# Live-Readiness governance: docs/live-readiness/
# ============================================================================

Write-Host "ERROR: This script is legacy and must not be used." -ForegroundColor Red
Write-Host ""
Write-Host "The current runtime uses the Blue/Red compose canon with Docker secrets." -ForegroundColor Yellow
Write-Host "Canonical entry points:" -ForegroundColor Yellow
Write-Host "  .\tools\cdb.ps1 runtime up      (full BLUE+RED stack restart)" -ForegroundColor White
Write-Host "  .\tools\cdb.ps1 secrets init    (secret setup)" -ForegroundColor White
exit 1
