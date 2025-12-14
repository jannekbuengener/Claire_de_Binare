#Requires -Version 5.1

<#
.SYNOPSIS
    CDB Service Logs - Intelligenter Log-Viewer mit Filterung

.DESCRIPTION
    Zeigt Docker-Container-Logs mit farblicher Hervorhebung und Filterung.
    Unterstützt Live-Tail-Modus und Regex-basierte Log-Filterung.

.PARAMETER ServiceName
    Name des Services (z.B. cdb_execution, cdb_risk)
    REQUIRED

.PARAMETER Lines
    Anzahl der letzten Log-Zeilen (default: 50)

.PARAMETER Follow
    Live-Tail-Modus (folgt neuen Log-Einträgen)

.PARAMETER Filter
    Regex-Filter für Log-Zeilen

.PARAMETER ShowTimestamps
    Zeigt Timestamps in Logs (docker logs -t)

.EXAMPLE
    .\cdb-service-logs.ps1 -ServiceName cdb_execution
    .\cdb-service-logs.ps1 -ServiceName cdb_risk -Lines 100
    .\cdb-service-logs.ps1 -ServiceName cdb_core -Follow
    .\cdb-service-logs.ps1 -ServiceName cdb_ws -Filter "ERROR|WARNING"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ServiceName,

    [int]$Lines = 50,

    [switch]$Follow,

    [string]$Filter,

    [switch]$ShowTimestamps
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# === KONFIGURATION ===
$VALID_SERVICES = @(
    "cdb_redis", "cdb_postgres", "cdb_prometheus", "cdb_grafana",
    "cdb_ws", "cdb_core", "cdb_risk", "cdb_execution", "cdb_db_writer"
)

# === FARBEN FÜR LOG-LEVELS ===
function Write-LogLine {
    param($Line)

    # Color-coding based on log level
    if ($Line -match "ERROR|Exception|Traceback|Failed") {
        Write-Host $Line -ForegroundColor Red
    } elseif ($Line -match "WARNING|WARN") {
        Write-Host $Line -ForegroundColor Yellow
    } elseif ($Line -match "INFO") {
        Write-Host $Line -ForegroundColor Green
    } elseif ($Line -match "DEBUG") {
        Write-Host $Line -ForegroundColor Gray
    } else {
        Write-Host $Line
    }
}

# === HEADER ===
Write-Host "📋 CDB Service Logs Viewer v1.0" -ForegroundColor Blue
Write-Host "Service: $ServiceName" -ForegroundColor Cyan

if ($Follow) {
    Write-Host "Mode: LIVE TAIL (Ctrl+C zum Beenden)" -ForegroundColor Yellow
} else {
    Write-Host "Mode: Last $Lines lines" -ForegroundColor Cyan
}

if ($Filter) {
    Write-Host "Filter: $Filter" -ForegroundColor Magenta
}

Write-Host "═══════════════════════════════════════════`n" -ForegroundColor Blue

# === VALIDIERUNG ===
if ($ServiceName -notin $VALID_SERVICES) {
    Write-Host "❌ Ungültiger Service: $ServiceName" -ForegroundColor Red
    Write-Host "`nGültige Services:" -ForegroundColor Yellow
    $VALID_SERVICES | ForEach-Object { Write-Host "  - $_" }
    exit 1
}

# === PRÜFE OB CONTAINER LÄUFT ===
try {
    $containerStatus = docker inspect $ServiceName 2>&1 | ConvertFrom-Json

    if (-not $containerStatus) {
        Write-Host "❌ Container '$ServiceName' nicht gefunden" -ForegroundColor Red
        Write-Host "Lösung: Führe .\stack_boot.ps1 aus" -ForegroundColor Yellow
        exit 1
    }

    $state = $containerStatus.State.Status

    if ($state -ne "running") {
        Write-Host "⚠️  Container '$ServiceName' läuft nicht (Status: $state)" -ForegroundColor Yellow
        Write-Host "Zeige letzte Logs vor dem Stop:`n" -ForegroundColor Cyan
    }
} catch {
    Write-Host "❌ Fehler beim Prüfen des Container-Status: $_" -ForegroundColor Red
    exit 1
}

# === BUILD DOCKER LOGS COMMAND ===
$dockerArgs = @("logs")

if ($Follow -and $state -eq "running") {
    $dockerArgs += "--follow"
}

$dockerArgs += "--tail"
$dockerArgs += $Lines.ToString()

if ($ShowTimestamps) {
    $dockerArgs += "-t"
}

$dockerArgs += $ServiceName

# === LOGS ANZEIGEN (MIT FILTERUNG) ===
try {
    if ($Filter) {
        # Mit Filterung: Lese Zeilen und filtere
        if ($Follow -and $state -eq "running") {
            # Live-Tail mit Filter
            Write-Host "⚠️  Live-Tail mit Filter ist limitiert (nur initiale Zeilen)" -ForegroundColor Yellow
            Write-Host "Für vollständige Live-Filterung: Nutze -Follow ohne -Filter`n" -ForegroundColor Yellow

            $initialLogs = docker logs --tail $Lines $ServiceName 2>&1

            foreach ($line in $initialLogs -split "`n") {
                if ($line -match $Filter) {
                    Write-LogLine $line
                }
            }

            Write-Host "`nInitiale gefilterte Logs angezeigt. Starte Live-Tail (UNGEFILTERT)...`n" -ForegroundColor Cyan
            Start-Sleep -Seconds 1

            # Starte ungefilterten Live-Tail
            docker logs --follow --tail 0 $ServiceName 2>&1 | ForEach-Object {
                Write-LogLine $_
            }

        } else {
            # Statische Logs mit Filter
            $logs = docker logs --tail $Lines $ServiceName 2>&1

            $matchCount = 0
            foreach ($line in $logs -split "`n") {
                if ($line -match $Filter) {
                    Write-LogLine $line
                    $matchCount++
                }
            }

            Write-Host "`n═══════════════════════════════════════════" -ForegroundColor Blue
            Write-Host "Gefilterte Zeilen: $matchCount / $Lines" -ForegroundColor Cyan
        }
    } else {
        # Ohne Filterung: Direktes Streaming mit Farbcodierung
        if ($Follow -and $state -eq "running") {
            # Live-Tail
            docker logs --follow --tail $Lines $ServiceName 2>&1 | ForEach-Object {
                Write-LogLine $_
            }
        } else {
            # Statische Logs
            $logs = docker logs --tail $Lines $ServiceName 2>&1

            foreach ($line in $logs -split "`n") {
                Write-LogLine $line
            }

            Write-Host "`n═══════════════════════════════════════════" -ForegroundColor Blue
            Write-Host "Log-Zeilen angezeigt: $Lines" -ForegroundColor Cyan
        }
    }
} catch {
    Write-Host "`n❌ Fehler beim Lesen der Logs: $_" -ForegroundColor Red
    exit 1
}
