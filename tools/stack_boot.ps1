#Requires -Version 5.1

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
$COMPOSE_FILE = "docker-compose.yml"
$EXPECTED_SERVICES = @(
    "cdb_redis", "cdb_postgres", "cdb_prometheus", "cdb_grafana",
    "cdb_core", "cdb_risk", "cdb_execution", "cdb_db_writer"
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

# === SCHRITT 2: COMPOSE-FILE VORHANDEN? ===
Write-Step "Schritt 2/5: Golden Stack File validieren"

if (-not (Test-Path $COMPOSE_FILE)) {
    Write-Error "$COMPOSE_FILE nicht gefunden!"
    Write-Info "Führe das Skript im Repository-Root aus (Verzeichnis mit docker-compose.yml)"
    exit 1
}
Write-Success "$COMPOSE_FILE gefunden"

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
    try {
        docker compose pull 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Pull fehlgeschlagen" }
        Write-Success "Images erfolgreich gepulled"
    } catch {
        Write-Warning "Image Pull fehlgeschlagen (fortfahren mit lokalen Images)"
    }
} else {
    Write-Step "Schritt 4/5: Image Pull übersprungen (--SkipPull)"
}

# === SCHRITT 5: STACK STARTEN ===
Write-Step "Schritt 5/5: Stack hochfahren"

Write-Info "Führe aus: docker compose up -d --remove-orphans"
$upOutput = docker compose up -d --remove-orphans 2>&1
if ($Verbose) {
    Write-Host $upOutput
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "Stack-Start fehlgeschlagen!"
    Write-Info "Debug-Schritte:"
    Write-Info "  docker compose ps -a"
    Write-Info "  docker compose logs --tail=50"
    exit 1
}

Write-Success "Stack gestartet"

# === HEALTH-CHECK WARTEN ===
Write-Info "Warte auf Health-Checks ($HEALTH_CHECK_TIMEOUT_SEC Sekunden Timeout)..."

$elapsed = 0
$healthyServices = @()

while ($elapsed -lt $HEALTH_CHECK_TIMEOUT_SEC) {
    Start-Sleep -Seconds $HEALTH_CHECK_INTERVAL_SEC
    $elapsed += $HEALTH_CHECK_INTERVAL_SEC

    try {
        $status = docker compose ps --format json 2>&1 | ConvertFrom-Json
        if ($status -is [array]) {
            $healthyServices = $status | Where-Object { $_.Health -eq "healthy" } | Select-Object -ExpandProperty Name
        } elseif ($status.Health -eq "healthy") {
            $healthyServices = @($status.Name)
        } else {
            $healthyServices = @()
        }
    } catch {
        $healthyServices = @()
    }

    $healthyCount = $healthyServices.Count
    $expectedCount = $EXPECTED_SERVICES.Count

    Write-Host ("`rHealth-Check: $healthyCount/$expectedCount healthy (${elapsed}s)") -NoNewline

    if ($healthyCount -eq $expectedCount) {
        Write-Host ""
        break
    }
}

Write-Host ""

# === FINALER STATUS ===
Write-Step "Stack-Status"

$finalStatus = docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>&1
Write-Host $finalStatus

# === ZUSAMMENFASSUNG ===
$allHealthy = ($healthyServices.Count -eq $EXPECTED_SERVICES.Count)

if ($allHealthy) {
    Write-Host "`n🎉 " -NoNewline -ForegroundColor Green
    Write-Host "STACK VOLLSTÄNDIG HEALTHY ($($EXPECTED_SERVICES.Count)/$($EXPECTED_SERVICES.Count))" -ForegroundColor Green
    Write-Host ""
    Write-Success "Zugriff auf Services:"
    Write-Host "  Signal Engine:    http://localhost:8001/health"
    Write-Host "  Risk Manager:     http://localhost:8002/health"
    Write-Host "  Execution:        http://localhost:8003/health"
    Write-Host "  WebSocket:        http://localhost:8000/health"
    Write-Host "  Grafana:          http://localhost:3000 (admin / <grafana_password>)"
    Write-Host "  Prometheus:       http://localhost:19090"
    Write-Host ""
    exit 0
} else {
    $unhealthyServices = $EXPECTED_SERVICES | Where-Object { $_ -notin $healthyServices }
    Write-Host "`n⚠️  " -NoNewline -ForegroundColor Yellow
    Write-Host "STACK TEILWEISE HEALTHY ($($healthyServices.Count)/$($EXPECTED_SERVICES.Count))" -ForegroundColor Yellow
    Write-Host ""
    Write-Warning "Unhealthy Services:"
    $unhealthyServices | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
    Write-Host ""
    Write-Info "Debug-Kommandos:"
    $unhealthyServices | ForEach-Object {
        Write-Host "  docker logs $_ --tail=30"
    }
    Write-Host ""
    exit 1
}
