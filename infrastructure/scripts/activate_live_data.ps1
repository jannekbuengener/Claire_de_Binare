# ============================================================================
# LEGACY SCRIPT — DO NOT USE FOR PRODUCTION ACTIVATION
# ============================================================================
# This script predates the Blue/Red compose canon and Docker-secrets model.
# It assumes .env-file-based configuration and an unqualified docker-compose.yml,
# neither of which reflect the current runtime architecture.
#
# Canonical runtime entry points:
#   .\tools\cdb.ps1 runtime up                             (PowerShell front door)
#   docker compose -f infrastructure/compose/compose.blue.yml up -d   (BLUE stack)
#   docker compose -f infrastructure/compose/compose.red.yml  up -d   (RED stack)
#
# Live-Readiness governance: docs/live-readiness/
# ============================================================================

Write-Host "ERROR: This script is legacy and must not be used." -ForegroundColor Red
Write-Host ""
Write-Host "The current runtime uses the Blue/Red compose canon with Docker secrets." -ForegroundColor Yellow
Write-Host "See:  .\tools\cdb.ps1 runtime up" -ForegroundColor Yellow
Write-Host "      infrastructure/compose/compose.blue.yml" -ForegroundColor Yellow
Write-Host "      infrastructure/compose/compose.red.yml" -ForegroundColor Yellow
Write-Host "      docs/live-readiness/" -ForegroundColor Yellow
exit 1
