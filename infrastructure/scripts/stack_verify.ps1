# stack_verify.ps1 - Automatische Stack-Vollständigkeitsprüfung
# Governance: Muss bei jedem Stack-Start ausgeführt werden
# Referenz: knowledge/governance/SERVICE_CATALOG.md

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CDB Stack Verification" -ForegroundColor Cyan
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Erwartete AKTIV-Services (aus knowledge/governance/SERVICE_CATALOG.md)
$expectedServices = @{
    # Applikation
    "cdb_signal"       = @{ Type = "App"; Required = $true }
    "cdb_risk"         = @{ Type = "App"; Required = $true }
    "cdb_execution"    = @{ Type = "App"; Required = $true }
    "cdb_db_writer"    = @{ Type = "App"; Required = $true }
    "cdb_ws"           = @{ Type = "App"; Required = $true }
    "cdb_paper_runner" = @{ Type = "App"; Required = $true }
    # Infrastruktur
    "cdb_redis"        = @{ Type = "Infra"; Required = $true }
    "cdb_postgres"     = @{ Type = "Infra"; Required = $true }
    "cdb_prometheus"   = @{ Type = "Infra"; Required = $true }
    "cdb_grafana"      = @{ Type = "Infra"; Required = $true }
}

# Optional (Logging Stack)
$optionalServices = @{
    "cdb_loki"     = @{ Type = "Logging"; Layer = "logging.yml" }
    "cdb_promtail" = @{ Type = "Logging"; Layer = "logging.yml" }
}

# BEREIT aber nicht deployed (bewusst deaktiviert)
$disabledServices = @{
    "cdb_allocation" = "Fehlende Env-Vars (ALLOCATION_*)"
    "cdb_regime"     = "Fehlende Env-Vars (REGIME_*)"
    "cdb_market"     = "Nicht implementiert (laut stack_up.ps1)"
}

# GAP-Services (Code existiert, kein Compose)
# Aktuell keine GAPs - cdb_signal wurde aktiviert (2025-12-28)
$gapServices = @{}

# Prüfung
Write-Host "[1/4] Laufende Container..." -ForegroundColor Yellow
$runningContainers = docker ps --format "{{.Names}}" 2>$null
if (-not $runningContainers) {
    Write-Host "FEHLER: Keine Container laufen oder Docker nicht erreichbar" -ForegroundColor Red
    exit 1
}

$running = @{}
$runningContainers | ForEach-Object { $running[$_] = $true }

Write-Host ""
Write-Host "[2/4] Pflicht-Services (AKTIV)..." -ForegroundColor Yellow
$errors = 0
$warnings = 0

foreach ($svc in $expectedServices.Keys | Sort-Object) {
    $info = $expectedServices[$svc]
    $status = docker inspect --format '{{.State.Health.Status}}' $svc 2>$null

    if ($running.ContainsKey($svc)) {
        if ($status -eq "healthy") {
            Write-Host "  [OK] $svc ($($info.Type)) - healthy" -ForegroundColor Green
        } elseif ($status -eq "starting") {
            Write-Host "  [WAIT] $svc ($($info.Type)) - starting" -ForegroundColor Yellow
            $warnings++
        } else {
            Write-Host "  [WARN] $svc ($($info.Type)) - $status" -ForegroundColor Yellow
            $warnings++
        }
    } else {
        Write-Host "  [FEHLT] $svc ($($info.Type)) - NICHT GESTARTET" -ForegroundColor Red
        $errors++
    }
}

Write-Host ""
Write-Host "[3/4] Optionale Services..." -ForegroundColor Yellow
foreach ($svc in $optionalServices.Keys | Sort-Object) {
    $info = $optionalServices[$svc]
    if ($running.ContainsKey($svc) -or $running.ContainsKey("claire_de_binare-${svc}-1")) {
        Write-Host "  [OK] $svc ($($info.Type)) - aktiv" -ForegroundColor Green
    } else {
        Write-Host "  [--] $svc - nicht gestartet (Layer: $($info.Layer))" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "[4/4] GAP-Analyse..." -ForegroundColor Yellow
foreach ($svc in $gapServices.Keys | Sort-Object) {
    Write-Host "  [GAP] $svc - $($gapServices[$svc])" -ForegroundColor Magenta
}

Write-Host ""
Write-Host "Bewusst deaktivierte Services:" -ForegroundColor Gray
foreach ($svc in $disabledServices.Keys | Sort-Object) {
    Write-Host "  [--] $svc - $($disabledServices[$svc])" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($errors -gt 0) {
    Write-Host "  ERGEBNIS: FEHLGESCHLAGEN ($errors Fehler, $warnings Warnungen)" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Cyan
    exit 1
} elseif ($warnings -gt 0) {
    Write-Host "  ERGEBNIS: OK mit Warnungen ($warnings)" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "  ERGEBNIS: VOLLSTANDIG" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    exit 0
}
