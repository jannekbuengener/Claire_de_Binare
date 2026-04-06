# ============================================================================
# LEGACY SCRIPT — DO NOT USE
# ============================================================================
# This script reads MEXC credentials from a flat .env file.
# The current runtime uses Docker secrets from ~/Documents/.secrets/.cdb/
# and the Blue/Red compose canon.
#
# Canonical entry points:
#   .\tools\cdb.ps1 secrets init    (secret setup)
#   .\tools\cdb.ps1 runtime up      (full BLUE+RED stack restart)
#
# Live-Readiness governance: docs/live-readiness/
# ============================================================================

Write-Host "ERROR: This script is legacy and must not be used." -ForegroundColor Red
Write-Host ""
Write-Host "The current runtime uses Docker secrets — not .env files." -ForegroundColor Yellow
Write-Host "Canonical entry points:" -ForegroundColor Yellow
Write-Host "  .\tools\cdb.ps1 secrets init    (secret setup)" -ForegroundColor White
Write-Host "  .\tools\cdb.ps1 runtime up       (full BLUE+RED stack restart)" -ForegroundColor White
exit 1
