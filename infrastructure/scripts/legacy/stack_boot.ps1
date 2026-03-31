#Requires -Version 5.1

# LEGACY — superseded by .\tools\cdb.ps1 runtime up (calls infrastructure/scripts/setup_blue_red.ps1).
# This script uses the correct BLUE/RED compose topology but still checks .secrets/ in the repo root,
# which is not the canonical secrets path (SECRETS_PATH / ~/Documents/.secrets/.cdb).
# Retained for reference only; do not use as an active entrypoint.

<#
.SYNOPSIS
    Golden Stack Boot für Claire de Binare v2.0

.DESCRIPTION
    Reproduzierbarer Start des kompletten Docker-Stacks.
    Prüft Docker-Status, pulled Images, startet Services, validiert Health.

.PARAMETER SkipPull
    Überspringt 'docker compose pull' (schnellerer Start bei lokalen Images)

.PARAMETER Verbose
    Zeigt detaillierte Logs während des Boots

.EXAMPLE
    .\stack_boot.ps1
    .\stack_boot.ps1 -SkipPull
    .\stack_boot.ps1 -Verbose
#>

param(
    [switch]$SkipPull,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# === KONFIGURATION ===
$COMPOSE_BLUE = "infrastructure/compose/compose.blue.yml"
$COMPOSE_RED  = "infrastructure/compose/compose.red.yml"
$BLUE_SERVICES = @(
    "cdb_redis", "cdb_postgres", "cdb_market", "cdb_candles",
    "cdb_regime", "cdb_allocation", "cdb_risk", "cdb_execution",
    "cdb_db_writer", "cdb_paper_runner"
)
$RED_SERVICES = @(
    "cdb_ws", "cdb_signal", "cdb_prometheus", "cdb_grafana"
)
$HEALTH_CHECK_TIMEOUT_SEC = 60
$HEALTH_CHECK_INTERVAL_SEC = 5

# === FARBEN FÜR OUTPUT ===
function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }
function Write-Step { param($Message) Write-Host "`n🔹 $Message" -ForegroundColor Blue }

# === SCHRITT 1: DOCKER LÄUFT? ===
Write-Step "Schritt 1/5: Docker Desktop Status prüfen"

try {
    $dockerInfo = docker info 2>&1 | Out-String
    if ($dockerInfo -match "Server Version") {
        $version = ($dockerInfo | Select-String "Server Version:\s*(.+)").Matches.Groups[1].Value.Trim()
        Write-Success "Docker läuft (Version: $version)"
    } else {
        throw "Docker nicht verfügbar"
    }
} catch {
    Write-Error "Docker Desktop läuft nicht oder ist nicht erreichbar!"
    Write-Info "Lösung:"
    Write-Info "  1. Starte Docker Desktop"
    Write-Info "  2. Warte bis 'Docker Desktop is running' im Tray"
    Write-Info "  3. Führe das Skript erneut aus"
    exit 1
}

# === SCHRITT 2: COMPOSE-FILES VORHANDEN? ===
Write-Step "Schritt 2/5: Compose-Dateien validieren"

$composeMissing = @()
if (-not (Test-Path $COMPOSE_BLUE)) { $composeMissing += $COMPOSE_BLUE }
if (-not (Test-Path $COMPOSE_RED))  { $composeMissing += $COMPOSE_RED }
if ($composeMissing.Count -gt 0) {
    Write-Error "Compose-Dateien nicht gefunden:"
    $composeMissing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Info "Führe das Skript im Repository-Root aus"
    exit 1
}
Write-Success "BLUE: $COMPOSE_BLUE"
Write-Success "RED:  $COMPOSE_RED"

# === SCHRITT 3: SECRETS & ENV PRÜFEN ===
Write-Step "Schritt 3/5: Secrets & ENV-Variablen prüfen"

$missingFiles = @()
if (-not (Test-Path ".secrets/redis_password")) { $missingFiles += ".secrets/redis_password" }
if (-not (Test-Path ".secrets/postgres_password")) { $missingFiles += ".secrets/postgres_password" }
if (-not (Test-Path ".secrets/grafana_password")) { $missingFiles += ".secrets/grafana_password" }
if (-not (Test-Path ".env")) { $missingFiles += ".env" }

if ($missingFiles.Count -gt 0) {
    Write-Error "Folgende Dateien fehlen:"
    $missingFiles | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Info "Lösung:"
    Write-Info "  1. Erstelle .secrets/ Verzeichnis: mkdir .secrets"
    Write-Info "  2. Kopiere Secrets: cp .cdb_local/.secrets/* .secrets/"
    Write-Info "  3. Erstelle .env aus .env.example: cp .env.example .env"
    Write-Info "  4. Passe REDIS_PASSWORD und POSTGRES_PASSWORD in .env an"
    exit 1
}
Write-Success "Alle Secrets & ENV-Variablen vorhanden"

# === SCHRITT 4: IMAGES PULLEN (optional) ===
if (-not $SkipPull) {
    Write-Step "Schritt 4/5: Docker Images aktualisieren"
    foreach ($cf in @($COMPOSE_BLUE, $COMPOSE_RED)) {
        try {
            docker compose -f $cf pull 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "Pull fehlgeschlagen fuer $cf" }
        } catch {
            Write-Warning "Image Pull fehlgeschlagen fuer $cf (fortfahren mit lokalen Images)"
        }
    }
    Write-Success "Images erfolgreich gepulled"
} else {
    Write-Step "Schritt 4/5: Image Pull übersprungen (--SkipPull)"
}

# === SCHRITT 5: STACK STARTEN ===
Write-Step "Schritt 5/5: Stack hochfahren"

Write-Info "BLUE-Stack starten..."
$blueOutput = docker compose -f $COMPOSE_BLUE up -d --remove-orphans 2>&1
if ($Verbose) { Write-Host $blueOutput }
if ($LASTEXITCODE -ne 0) {
    Write-Error "BLUE-Stack-Start fehlgeschlagen!"
    Write-Info "Debug: docker compose -f $COMPOSE_BLUE ps -a"
    exit 1
}
Write-Success "BLUE-Stack gestartet"

Write-Info "RED-Stack starten..."
$redOutput = docker compose -f $COMPOSE_RED up -d --remove-orphans 2>&1
if ($Verbose) { Write-Host $redOutput }
if ($LASTEXITCODE -ne 0) {
    Write-Warning "RED-Stack-Start fehlgeschlagen (BLUE laeuft weiter)"
}
Write-Success "RED-Stack gestartet"

# === HEALTH-CHECK WARTEN ===
$allExpected = @($BLUE_SERVICES) + @($RED_SERVICES)
$expectedCount = $allExpected.Count
Write-Info "Warte auf Health-Checks ($HEALTH_CHECK_TIMEOUT_SEC Sekunden Timeout)..."

$elapsed = 0
$healthyServices = @()

function Get-HealthyNames($composeFile) {
    try {
        $status = docker compose -f $composeFile ps --format json 2>&1 | ConvertFrom-Json
        if ($status -is [array]) {
            return @($status | Where-Object { $_.Health -eq "healthy" } | Select-Object -ExpandProperty Service)
        } elseif ($status.Health -eq "healthy") {
            return @($status.Service)
        }
    } catch {}
    return @()
}

while ($elapsed -lt $HEALTH_CHECK_TIMEOUT_SEC) {
    Start-Sleep -Seconds $HEALTH_CHECK_INTERVAL_SEC
    $elapsed += $HEALTH_CHECK_INTERVAL_SEC

    $healthyServices = @(Get-HealthyNames $COMPOSE_BLUE) + @(Get-HealthyNames $COMPOSE_RED)
    $healthyCount = $healthyServices.Count

    Write-Host ("`rHealth-Check: $healthyCount/$expectedCount healthy (${elapsed}s)") -NoNewline

    if ($healthyCount -ge $expectedCount) {
        Write-Host ""
        break
    }
}

Write-Host ""

# === FINALER STATUS ===
Write-Step "BLUE-Stack-Status"
docker compose -f $COMPOSE_BLUE ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>&1 | ForEach-Object { Write-Host $_ }

Write-Step "RED-Stack-Status"
docker compose -f $COMPOSE_RED ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>&1 | ForEach-Object { Write-Host $_ }

# === ZUSAMMENFASSUNG ===
$blueHealthy = @($healthyServices | Where-Object { $_ -in $BLUE_SERVICES })
$redHealthy  = @($healthyServices | Where-Object { $_ -in $RED_SERVICES })
$blueAllOk   = ($blueHealthy.Count -eq $BLUE_SERVICES.Count)
$redAllOk    = ($redHealthy.Count -eq $RED_SERVICES.Count)

if ($blueAllOk -and $redAllOk) {
    Write-Host ""
    Write-Success "STACK VOLLSTAENDIG HEALTHY ($expectedCount/$expectedCount)"
    Write-Host ""
    Write-Success "Zugriff auf Services:"
    Write-Host "  Signal Engine:    http://localhost:8005/health"
    Write-Host "  Risk Manager:     http://localhost:8002/health"
    Write-Host "  Execution:        http://localhost:8003/health"
    Write-Host "  WebSocket:        http://localhost:8000/health"
    Write-Host "  Grafana:          http://localhost:3000 (admin / <grafana_password>)"
    Write-Host "  Prometheus:       http://localhost:19090"
    Write-Host ""
    exit 0
} elseif ($blueAllOk) {
    Write-Host ""
    Write-Warning "BLUE HEALTHY, RED TEILWEISE ($($redHealthy.Count)/$($RED_SERVICES.Count))"
    $redMissing = $RED_SERVICES | Where-Object { $_ -notin $redHealthy }
    $redMissing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
    Write-Host ""
    Write-Info "BLUE-Kern laeuft. RED-Issues beeintraechtigen kein Trading."
    exit 0
} else {
    $blueMissing = $BLUE_SERVICES | Where-Object { $_ -notin $blueHealthy }
    Write-Host ""
    Write-Error "BLUE-KERN HAT ISSUES ($($blueHealthy.Count)/$($BLUE_SERVICES.Count))"
    Write-Warning "Unhealthy BLUE Services:"
    $blueMissing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host ""
    Write-Info "Debug-Kommandos:"
    $blueMissing | ForEach-Object {
        Write-Host "  docker compose -f $COMPOSE_BLUE logs $_ --tail=30"
    }
    Write-Host ""
    exit 1
}
