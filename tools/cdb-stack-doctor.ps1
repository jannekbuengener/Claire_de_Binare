#Requires -Version 5.1

<#
.SYNOPSIS
    CDB Stack Doctor - Diagnose & Health-Check für den Docker-Stack

.DESCRIPTION
    Prüft Docker-Stack-Health, zeigt Unhealthy-Services mit Logs,
    validiert Konfigurationsdateien und gibt konkrete Fix-Empfehlungen.

.PARAMETER ServiceName
    Optional: Prüft nur einen spezifischen Service

.PARAMETER ShowLogs
    Anzahl der Log-Zeilen für unhealthy Services (default: 30)

.EXAMPLE
    .\cdb-stack-doctor.ps1
    .\cdb-stack-doctor.ps1 -ServiceName cdb_execution
    .\cdb-stack-doctor.ps1 -ShowLogs 50
#>

param(
    [string]$ServiceName,
    [int]$ShowLogs = 30
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# === KONFIGURATION ===
$COMPOSE_FILE = "docker-compose.yml"
$ENV_FILE = ".env"
$SECRETS_DIR = ".secrets"
$REQUIRED_SECRETS = @("redis_password", "postgres_password", "grafana_password")
$EXPECTED_SERVICES = @(
    "cdb_redis", "cdb_postgres", "cdb_prometheus", "cdb_grafana",
    "cdb_ws", "cdb_core", "cdb_risk", "cdb_execution", "cdb_db_writer"
)

# === FARBEN FÜR OUTPUT ===
function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }
function Write-Header { param($Message) Write-Host "`n🔍 $Message" -ForegroundColor Blue }

# === HEADER ===
Write-Host "🩺 CDB Stack Doctor v1.0" -ForegroundColor Blue
Write-Host "Diagnose gestartet: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

# === CHECK 1: DOCKER LÄUFT? ===
Write-Header "Check 1/5: Docker Desktop Status"

try {
    $dockerInfo = docker info 2>&1 | Out-String
    if ($dockerInfo -match "Server Version") {
        $version = ($dockerInfo | Select-String "Server Version:\s*(.+)").Matches.Groups[1].Value.Trim()
        Write-Success "Docker läuft (Version: $version)"
    } else {
        throw "Docker nicht verfügbar"
    }
} catch {
    Write-Error "Docker Desktop läuft nicht!"
    Write-Info "Lösung: Starte Docker Desktop und warte bis 'Docker Desktop is running' im Tray"
    exit 1
}

# === CHECK 2: KONFIGURATIONSDATEIEN ===
Write-Header "Check 2/5: Konfigurationsdateien"

$configIssues = @()

if (-not (Test-Path $COMPOSE_FILE)) {
    $configIssues += "$COMPOSE_FILE fehlt"
}

if (-not (Test-Path $ENV_FILE)) {
    $configIssues += "$ENV_FILE fehlt"
}

if (-not (Test-Path $SECRETS_DIR)) {
    $configIssues += "$SECRETS_DIR/ Verzeichnis fehlt"
} else {
    foreach ($secret in $REQUIRED_SECRETS) {
        $secretPath = Join-Path $SECRETS_DIR $secret
        if (-not (Test-Path $secretPath)) {
            $configIssues += "$secretPath fehlt"
        }
    }
}

if ($configIssues.Count -gt 0) {
    Write-Error "Konfigurationsprobleme gefunden:"
    $configIssues | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Info "Lösung: Führe .\tools\cdb-secrets-sync.ps1 aus"
    exit 1
} else {
    Write-Success "Alle Konfigurationsdateien vorhanden"
}

# === CHECK 3: CONTAINER STATUS ===
Write-Header "Check 3/5: Container Status"

try {
    $containers = docker compose ps --format json 2>&1

    if (-not $containers) {
        Write-Warning "Keine Container gefunden (Stack läuft nicht)"
        Write-Info "Lösung: Führe .\stack_boot.ps1 aus"
        exit 1
    }

    $status = $containers | ConvertFrom-Json

    # Handle both single object and array
    if ($status -isnot [array]) {
        $status = @($status)
    }

    # Filter by ServiceName if provided
    if ($ServiceName) {
        $status = $status | Where-Object { $_.Service -eq $ServiceName }
        if ($status.Count -eq 0) {
            Write-Error "Service '$ServiceName' nicht gefunden"
            exit 1
        }
    }

    $runningCount = ($status | Where-Object { $_.State -eq "running" }).Count
    $healthyCount = ($status | Where-Object { $_.Health -eq "healthy" }).Count
    $totalCount = $status.Count

    Write-Host "Running: $runningCount/$totalCount | Healthy: $healthyCount/$totalCount"

} catch {
    Write-Error "Fehler beim Lesen des Container-Status: $_"
    exit 1
}

# === CHECK 4: UNHEALTHY SERVICES DIAGNOSE ===
Write-Header "Check 4/5: Unhealthy Services Diagnose"

$unhealthyServices = $status | Where-Object {
    $_.State -eq "running" -and $_.Health -ne "healthy"
}

if ($unhealthyServices.Count -eq 0) {
    Write-Success "Alle Services sind healthy!"
} else {
    Write-Warning "Unhealthy Services gefunden: $($unhealthyServices.Count)"
    Write-Host ""

    foreach ($service in $unhealthyServices) {
        Write-Host "═══════════════════════════════════════════" -ForegroundColor Yellow
        Write-Host "Service: $($service.Name)" -ForegroundColor Yellow
        Write-Host "Status:  $($service.State) (Health: $($service.Health))" -ForegroundColor Yellow
        Write-Host "═══════════════════════════════════════════" -ForegroundColor Yellow

        Write-Info "Letzte $ShowLogs Log-Zeilen:"
        Write-Host ""

        try {
            $logs = docker logs $service.Name --tail $ShowLogs 2>&1
            Write-Host $logs -ForegroundColor Gray
        } catch {
            Write-Error "Konnte Logs nicht lesen: $_"
        }

        Write-Host ""
    }
}

# === CHECK 5: STOPPED/EXITED SERVICES ===
Write-Header "Check 5/5: Gestoppte/Exited Services"

$stoppedServices = $status | Where-Object { $_.State -ne "running" }

if ($stoppedServices.Count -eq 0) {
    Write-Success "Alle Services laufen"
} else {
    Write-Error "Gestoppte Services gefunden: $($stoppedServices.Count)"
    Write-Host ""

    foreach ($service in $stoppedServices) {
        Write-Host "Service: $($service.Name)" -ForegroundColor Red
        Write-Host "Status:  $($service.State)" -ForegroundColor Red

        Write-Info "Letzte $ShowLogs Log-Zeilen:"
        Write-Host ""

        try {
            $logs = docker logs $service.Name --tail $ShowLogs 2>&1
            Write-Host $logs -ForegroundColor Gray
        } catch {
            Write-Error "Konnte Logs nicht lesen: $_"
        }

        Write-Host ""
    }

    Write-Info "Lösung: docker compose up -d --force-recreate"
}

# === ZUSAMMENFASSUNG ===
Write-Host "`n═══════════════════════════════════════════" -ForegroundColor Blue
Write-Host "DIAGNOSE ZUSAMMENFASSUNG" -ForegroundColor Blue
Write-Host "═══════════════════════════════════════════" -ForegroundColor Blue

$allHealthy = ($healthyCount -eq $totalCount) -and ($stoppedServices.Count -eq 0)

if ($allHealthy) {
    Write-Host "🎉 " -NoNewline -ForegroundColor Green
    Write-Host "STACK VOLLSTÄNDIG HEALTHY ($healthyCount/$totalCount)" -ForegroundColor Green
    exit 0
} else {
    Write-Host "⚠️  " -NoNewline -ForegroundColor Yellow
    Write-Host "STACK HAT PROBLEME" -ForegroundColor Yellow
    Write-Host ""

    if ($unhealthyServices.Count -gt 0) {
        Write-Host "Unhealthy Services:" -ForegroundColor Yellow
        $unhealthyServices | ForEach-Object { Write-Host "  - $($_.Name)" -ForegroundColor Yellow }
    }

    if ($stoppedServices.Count -gt 0) {
        Write-Host "Gestoppte Services:" -ForegroundColor Red
        $stoppedServices | ForEach-Object { Write-Host "  - $($_.Name)" -ForegroundColor Red }
    }

    Write-Host ""
    Write-Info "Empfohlene Fix-Schritte:"
    Write-Host "  1. Prüfe Logs oben auf Error-Meldungen"
    Write-Host "  2. Führe aus: docker compose up -d --force-recreate"
    Write-Host "  3. Prüfe .secrets/ und .env Konfiguration"
    Write-Host "  4. Bei Redis/PostgreSQL Errors: .\tools\cdb-secrets-sync.ps1"
    Write-Host ""

    exit 1
}
