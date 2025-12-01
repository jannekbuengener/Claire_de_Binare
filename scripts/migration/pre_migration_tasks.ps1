# ============================================================================
# HISTORICAL TEMPLATE - Documents 2025-11-16 migration
# ============================================================================
# Repository : Claire_de_Binare
# Context    : Migration from backup repo into Claire de Binare baseline
# Status     : Historical reference only (do not re-run on current baseline)
#
# Original Header:
# Claire de Binare - Pre-Migration Tasks
# ZWECK: Automatisierte Ausführung der 4 CRITICAL Pre-Migration-Tasks
# AUTOR: Pipeline 4 - Multi-Agenten-System
# DATUM: 2025-11-16
# ============================================================================

param(
    [switch]$DryRun = $false,
    [switch]$SkipBackup = $false
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "Claire de Binare - Pre-Migration Execution" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN] Keine Dateien werden geändert. Nur Vorschau." -ForegroundColor Yellow
    Write-Host ""
}

# ============================================================================
# TASK 0: Backup erstellen
# ============================================================================

if (-not $SkipBackup -and -not $DryRun) {
    Write-Host "[TASK 0] Backup erstellen..." -ForegroundColor Yellow

    $BackupDir = Join-Path $PSScriptRoot "backups"
    $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

    if (-not (Test-Path $BackupDir)) {
        New-Item -ItemType Directory -Path $BackupDir | Out-Null
    }

    # Backup kritischer Dateien
    Copy-Item "$RepoRoot\ - Kopie.env" "$BackupDir\.env.backup_$Timestamp" -ErrorAction SilentlyContinue
    Copy-Item "$RepoRoot\docker-compose.yml" "$BackupDir\docker-compose.yml.backup_$Timestamp"

    Write-Host "✅ Backup erstellt in: $BackupDir" -ForegroundColor Green
    Write-Host ""
}

# ============================================================================
# TASK 1: SR-001 - Secrets bereinigen
# ============================================================================

Write-Host "[TASK 1] SR-001 - Secrets aus ' - Kopie.env' bereinigen..." -ForegroundColor Yellow

$EnvFile = Join-Path $RepoRoot " - Kopie.env"
$EnvTemplate = Join-Path $RepoRoot ".env.template"

if (Test-Path $EnvFile) {
    if ($DryRun) {
        Write-Host "  [DRY RUN] Würde Secrets ersetzen in: $EnvFile" -ForegroundColor Gray
        Write-Host "  [DRY RUN] Würde Datei umbenennen zu: $EnvTemplate" -ForegroundColor Gray
    } else {
        # Secrets durch Platzhalter ersetzen
        $content = Get-Content $EnvFile -Raw

        # Postgres Password
        $content = $content -replace 'POSTGRES_PASSWORD=.*', 'POSTGRES_PASSWORD=<SET_IN_ENV>'
        $content = $content -replace 'POSTGRES_USER=.*', 'POSTGRES_USER=<SET_IN_ENV>'
        $content = $content -replace 'DATABASE_URL=postgresql://.*', 'DATABASE_URL=postgresql://<USER>:<PASSWORD>@cdb_postgres:5432/claire_de_binare'

        # Grafana Password
        $content = $content -replace 'GRAFANA_PASSWORD=.*', 'GRAFANA_PASSWORD=<SET_IN_ENV>'

        # Redis Password (falls noch nicht Platzhalter)
        $content = $content -replace 'REDIS_PASSWORD=(?!<SET_IN_ENV>).*', 'REDIS_PASSWORD=<SET_IN_ENV>'

        Set-Content -Path $EnvFile -Value $content -NoNewline

        # Datei umbenennen
        Move-Item -Path $EnvFile -Destination $EnvTemplate -Force

        Write-Host "✅ Secrets bereinigt und Datei umbenannt zu .env.template" -ForegroundColor Green
    }
} else {
    Write-Host "⚠️  Datei ' - Kopie.env' nicht gefunden. Überspringe." -ForegroundColor Yellow
}
Write-Host ""

# ============================================================================
# TASK 2: SR-002 - ENV-Naming normalisieren
# ============================================================================

Write-Host "[TASK 2] SR-002 - ENV-Naming auf Dezimal-Konvention normalisieren..." -ForegroundColor Yellow

$TemplateFile = Join-Path $RepoRoot ".env.template"

if (Test-Path $TemplateFile) {
    if ($DryRun) {
        Write-Host "  [DRY RUN] Würde ENV-Namen aktualisieren in: $TemplateFile" -ForegroundColor Gray
    } else {
        $content = Get-Content $TemplateFile -Raw

        # ALT → NEU (Dezimal-Konvention)
        $replacements = @{
            'MAX_DAILY_DRAWDOWN=5\.0' = 'MAX_DAILY_DRAWDOWN_PCT=0.05'
            'MAX_POSITION_SIZE=10\.0' = 'MAX_POSITION_PCT=0.10'
            'MAX_TOTAL_EXPOSURE=50\.0' = 'MAX_EXPOSURE_PCT=0.50'
        }

        foreach ($pattern in $replacements.Keys) {
            $replacement = $replacements[$pattern]
            if ($content -match $pattern) {
                $content = $content -replace $pattern, $replacement
                Write-Host "  ✓ Ersetzt: $pattern → $replacement" -ForegroundColor Gray
            }
        }

        # Fehlende Risk-Parameter ergänzen (falls nicht vorhanden)
        if ($content -notmatch 'STOP_LOSS_PCT') {
            $riskSection = $content -match '(?s)(# RISK MANAGEMENT.*?)(# ====)'
            if ($matches) {
                $insert = @"

# Per-Trade Stop Loss (Min: 0.005, Max: 0.10, Default: 0.02)
STOP_LOSS_PCT=0.02

# Market Anomaly: Max Slippage (Min: 0.001, Max: 0.05, Default: 0.01)
MAX_SLIPPAGE_PCT=0.01

# Market Anomaly: Max Spread Multiplier (Min: 2.0, Max: 10.0, Default: 5.0)
MAX_SPREAD_MULTIPLIER=5.0

# Data Staleness Timeout in Seconds (Min: 10, Max: 120, Default: 30)
DATA_STALE_TIMEOUT_SEC=30

"@
                $content = $content -replace '(INITIAL_CAPITAL=.*?)(\r?\n# ====)', "`$1$insert`$2"
                Write-Host "  ✓ Fehlende Risk-Parameter ergänzt" -ForegroundColor Gray
            }
        }

        Set-Content -Path $TemplateFile -Value $content -NoNewline
        Write-Host "✅ ENV-Naming normalisiert (Dezimal-Konvention)" -ForegroundColor Green
    }
} else {
    Write-Host "⚠️  .env.template nicht gefunden. Kopiere aus sandbox/..." -ForegroundColor Yellow

    if (-not $DryRun) {
        Copy-Item "$PSScriptRoot\.env.template" $TemplateFile
        Write-Host "✅ .env.template aus sandbox/ kopiert" -ForegroundColor Green
    }
}
Write-Host ""

# ============================================================================
# TASK 3: SR-003 - MEXC-API-ENV sicherstellen
# ============================================================================

Write-Host "[TASK 3] SR-003 - MEXC-API-Credentials in ENV-Template prüfen..." -ForegroundColor Yellow

if (Test-Path $TemplateFile) {
    $content = Get-Content $TemplateFile -Raw

    if ($content -match 'MEXC_API_KEY' -and $content -match 'MEXC_API_SECRET') {
        Write-Host "✅ MEXC-API-Keys bereits vorhanden in .env.template" -ForegroundColor Green
    } else {
        if ($DryRun) {
            Write-Host "  [DRY RUN] Würde MEXC-API-Keys ergänzen" -ForegroundColor Gray
        } else {
            # MEXC-Sektion ergänzen (falls nicht vorhanden)
            if ($content -notmatch 'MEXC API') {
                $mexcSection = @"

# ============================================================================
# MEXC API (CRITICAL - System nicht funktionsfähig ohne!)
# ============================================================================
MEXC_API_KEY=<SET_IN_ENV>
MEXC_API_SECRET=<SET_IN_ENV>
"@
                $content = $content -replace '(# MONITORING.*?\r?\n)', "$mexcSection`r`n`r`n`$1"
                Set-Content -Path $TemplateFile -Value $content -NoNewline
                Write-Host "✅ MEXC-API-Keys ergänzt" -ForegroundColor Green
            }
        }
    }
} else {
    Write-Host "⚠️  .env.template nicht gefunden" -ForegroundColor Yellow
}
Write-Host ""

# ============================================================================
# TASK 4: cdb_signal_gen aus docker-compose.yml entfernen
# ============================================================================

Write-Host "[TASK 4] cdb_signal_gen aus docker-compose.yml entfernen..." -ForegroundColor Yellow

$ComposeFile = Join-Path $RepoRoot "docker-compose.yml"

if (Test-Path $ComposeFile) {
    if ($DryRun) {
        Write-Host "  [DRY RUN] Würde Service 'cdb_signal_gen' auskommentieren" -ForegroundColor Gray
    } else {
        $content = Get-Content $ComposeFile -Raw

        # Service-Block auskommentieren (Zeilen 263-277)
        $pattern = '(?m)(^  cdb_signal_gen:.*?^    networks:.*?^      - cdb_network\r?\n)'
        if ($content -match $pattern) {
            $serviceBlock = $matches[1]
            $commentedBlock = ($serviceBlock -split "`n") | ForEach-Object { "  # $_" }
            $commentedBlock = $commentedBlock -join "`n"

            $content = $content -replace [regex]::Escape($serviceBlock), "  # ============================================================`n  # LEGACY SERVICE (entfernt - Dockerfile.signal_gen fehlt)`n  # ============================================================`n$commentedBlock"

            Set-Content -Path $ComposeFile -Value $content -NoNewline
            Write-Host "✅ Service cdb_signal_gen auskommentiert (Legacy)" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Service cdb_signal_gen nicht gefunden oder bereits entfernt" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "❌ docker-compose.yml nicht gefunden!" -ForegroundColor Red
}
Write-Host ""

# ============================================================================
# VALIDIERUNG
# ============================================================================

if (-not $DryRun) {
    Write-Host "[VALIDIERUNG] Änderungen prüfen..." -ForegroundColor Yellow

    # Check 1: .env.template existiert
    if (Test-Path $TemplateFile) {
        Write-Host "✅ .env.template existiert" -ForegroundColor Green
    } else {
        Write-Host "❌ .env.template fehlt!" -ForegroundColor Red
    }

    # Check 2: Keine Secrets in .env.template
    $templateContent = Get-Content $TemplateFile -Raw
    $secretPatterns = @('Jannek', 'password=(?!<SET_IN_ENV>)', 'secret=(?!<SET_IN_ENV>)')
    $foundSecrets = $false

    foreach ($pattern in $secretPatterns) {
        if ($templateContent -match $pattern) {
            Write-Host "❌ WARNUNG: Potentieller Secret-Wert gefunden: $pattern" -ForegroundColor Red
            $foundSecrets = $true
        }
    }

    if (-not $foundSecrets) {
        Write-Host "✅ Keine Secrets in .env.template gefunden" -ForegroundColor Green
    }

    # Check 3: docker-compose.yml valide
    try {
        $composeCheck = & docker compose -f $ComposeFile config --quiet 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ docker-compose.yml ist valide" -ForegroundColor Green
        } else {
            Write-Host "❌ docker-compose.yml hat Fehler: $composeCheck" -ForegroundColor Red
        }
    } catch {
        Write-Host "⚠️  docker compose nicht verfügbar - Validierung übersprungen" -ForegroundColor Yellow
    }

    Write-Host ""
}

# ============================================================================
# ZUSAMMENFASSUNG
# ============================================================================

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "Pre-Migration Tasks - Zusammenfassung" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN MODUS] - Keine Änderungen durchgeführt" -ForegroundColor Yellow
} else {
    Write-Host "✅ Task 1: Secrets bereinigt" -ForegroundColor Green
    Write-Host "✅ Task 2: ENV-Naming normalisiert (Dezimal-Konvention)" -ForegroundColor Green
    Write-Host "✅ Task 3: MEXC-API-ENV sichergestellt" -ForegroundColor Green
    Write-Host "✅ Task 4: cdb_signal_gen entfernt" -ForegroundColor Green
}

Write-Host ""
Write-Host "Nächste Schritte:" -ForegroundColor Cyan
Write-Host "1. Echte .env erstellen: cp .env.template .env" -ForegroundColor White
Write-Host "2. Alle <SET_IN_ENV> Platzhalter durch echte Werte ersetzen" -ForegroundColor White
Write-Host "3. Sicherstellen: .env ist in .gitignore (bereits erledigt)" -ForegroundColor White
Write-Host "4. docker compose config --quiet (Syntax prüfen)" -ForegroundColor White
Write-Host "5. docker compose up -d (Services starten)" -ForegroundColor White
Write-Host ""
Write-Host "Für ausführliche Validierung: .\pre_migration_validation.ps1" -ForegroundColor Cyan
Write-Host ""
