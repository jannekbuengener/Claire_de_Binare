# ============================================================================
# HISTORICAL TEMPLATE - Documents 2025-11-16 migration
# ============================================================================
# Repository : Claire_de_Binare_Cleanroom
# Context    : Migration from backup repo into Cleanroom baseline
# Status     : Historical reference only (do not re-run on current baseline)
#
# Original Header:
# Claire de Binare - Pre-Migration Validation
# ZWECK: Validierung aller Pre-Migration-Tasks vor Cleanroom-Migration
# AUTOR: Pipeline 4 - Multi-Agenten-System
# DATUM: 2025-11-16
# ============================================================================

param(
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$IssuesFound = 0

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "Claire de Binare - Pre-Migration Validation" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

function Test-Check {
    param(
        [string]$Name,
        [scriptblock]$Test,
        [string]$SuccessMessage,
        [string]$FailureMessage,
        [string]$Severity = "ERROR"  # ERROR, WARNING, INFO
    )

    Write-Host "[$Name] " -NoNewline -ForegroundColor Yellow

    try {
        $result = & $Test
        if ($result) {
            Write-Host "✅ $SuccessMessage" -ForegroundColor Green
            if ($Verbose) {
                Write-Host "   Details: $result" -ForegroundColor Gray
            }
            return $true
        } else {
            if ($Severity -eq "ERROR") {
                Write-Host "❌ $FailureMessage" -ForegroundColor Red
                $script:IssuesFound++
            } elseif ($Severity -eq "WARNING") {
                Write-Host "⚠️  $FailureMessage" -ForegroundColor Yellow
            } else {
                Write-Host "ℹ️  $FailureMessage" -ForegroundColor Cyan
            }
            return $false
        }
    } catch {
        Write-Host "❌ Fehler: $_" -ForegroundColor Red
        $script:IssuesFound++
        return $false
    }
}

# ============================================================================
# KATEGORIE 1: Secrets & Security (CRITICAL)
# ============================================================================

Write-Host ""
Write-Host "[KATEGORIE 1] Secrets & Security" -ForegroundColor Cyan
Write-Host "─────────────────────────────────────────────────────────────────" -ForegroundColor Gray

Test-Check -Name "SR-001.1" -Test {
    # .env.template existiert
    Test-Path "$RepoRoot\.env.template"
} -SuccessMessage ".env.template existiert" -FailureMessage ".env.template fehlt!" -Severity "ERROR"

Test-Check -Name "SR-001.2" -Test {
    # Alte ' - Kopie.env' existiert NICHT mehr
    -not (Test-Path "$RepoRoot\ - Kopie.env")
} -SuccessMessage "' - Kopie.env' wurde korrekt entfernt/umbenannt" -FailureMessage "' - Kopie.env' existiert noch - Secrets-Leak-Risiko!" -Severity "ERROR"

Test-Check -Name "SR-001.3" -Test {
    # Keine echten Secrets in .env.template
    if (Test-Path "$RepoRoot\.env.template") {
        $content = Get-Content "$RepoRoot\.env.template" -Raw
        $forbiddenPatterns = @(
            'Jannek',
            'password=(?!<SET_IN_ENV>)\w+',
            'PASSWORD=(?!<SET_IN_ENV>)\w+',
            'secret=(?!<SET_IN_ENV>)\w+',
            'SECRET=(?!<SET_IN_ENV>)\w+'
        )
        foreach ($pattern in $forbiddenPatterns) {
            if ($content -match $pattern) {
                return $false
            }
        }
        return $true
    }
    return $false
} -SuccessMessage "Keine echten Secrets in .env.template" -FailureMessage "CRITICAL: Echte Secrets gefunden in .env.template!" -Severity "ERROR"

Test-Check -Name "SR-001.4" -Test {
    # .env in .gitignore
    if (Test-Path "$RepoRoot\.gitignore") {
        $content = Get-Content "$RepoRoot\.gitignore" -Raw
        return ($content -match '^\s*\.env\s*$' -or $content -match '\*\.env')
    }
    return $false
} -SuccessMessage ".env ist in .gitignore" -FailureMessage ".env fehlt in .gitignore - Git-Commit-Risiko!" -Severity "ERROR"

Test-Check -Name "SR-001.5" -Test {
    # Git-History-Check (ob Secrets jemals committed wurden)
    try {
        $gitLog = & git log --all -S "Jannek8" --oneline 2>&1
        return ([string]::IsNullOrWhiteSpace($gitLog))
    } catch {
        return $null  # Git nicht verfügbar
    }
} -SuccessMessage "Keine Secrets in Git-History gefunden" -FailureMessage "WARNUNG: Secrets könnten in Git-History vorhanden sein!" -Severity "WARNING"

# ============================================================================
# KATEGORIE 2: ENV-Naming-Konvention (CRITICAL)
# ============================================================================

Write-Host ""
Write-Host "[KATEGORIE 2] ENV-Naming-Konvention (Dezimal)" -ForegroundColor Cyan
Write-Host "─────────────────────────────────────────────────────────────────" -ForegroundColor Gray

Test-Check -Name "SR-002.1" -Test {
    # MAX_DAILY_DRAWDOWN_PCT vorhanden (neue Konvention)
    if (Test-Path "$RepoRoot\.env.template") {
        $content = Get-Content "$RepoRoot\.env.template" -Raw
        return ($content -match 'MAX_DAILY_DRAWDOWN_PCT')
    }
    return $false
} -SuccessMessage "MAX_DAILY_DRAWDOWN_PCT vorhanden (neue Konvention)" -FailureMessage "MAX_DAILY_DRAWDOWN_PCT fehlt!" -Severity "ERROR"

Test-Check -Name "SR-002.2" -Test {
    # MAX_POSITION_PCT vorhanden
    if (Test-Path "$RepoRoot\.env.template") {
        $content = Get-Content "$RepoRoot\.env.template" -Raw
        return ($content -match 'MAX_POSITION_PCT')
    }
    return $false
} -SuccessMessage "MAX_POSITION_PCT vorhanden" -FailureMessage "MAX_POSITION_PCT fehlt!" -Severity "ERROR"

Test-Check -Name "SR-002.3" -Test {
    # MAX_EXPOSURE_PCT vorhanden
    if (Test-Path "$RepoRoot\.env.template") {
        $content = Get-Content "$RepoRoot\.env.template" -Raw
        return ($content -match 'MAX_EXPOSURE_PCT')
    }
    return $false
} -SuccessMessage "MAX_EXPOSURE_PCT vorhanden" -FailureMessage "MAX_EXPOSURE_PCT fehlt!" -Severity "ERROR"

Test-Check -Name "SR-002.4" -Test {
    # Alte Konvention NICHT mehr vorhanden
    if (Test-Path "$RepoRoot\.env.template") {
        $content = Get-Content "$RepoRoot\.env.template" -Raw
        return ($content -notmatch 'MAX_DAILY_DRAWDOWN=\d+\.0')
    }
    return $false
} -SuccessMessage "Alte ENV-Namen (MAX_DAILY_DRAWDOWN=5.0) entfernt" -FailureMessage "Alte ENV-Konvention noch vorhanden - Konflikt!" -Severity "ERROR"

Test-Check -Name "SR-002.5" -Test {
    # Alle 7 Risk-Parameter vorhanden
    if (Test-Path "$RepoRoot\.env.template") {
        $content = Get-Content "$RepoRoot\.env.template" -Raw
        $requiredParams = @(
            'MAX_DAILY_DRAWDOWN_PCT',
            'MAX_POSITION_PCT',
            'MAX_EXPOSURE_PCT',
            'STOP_LOSS_PCT',
            'MAX_SLIPPAGE_PCT',
            'MAX_SPREAD_MULTIPLIER',
            'DATA_STALE_TIMEOUT_SEC'
        )
        foreach ($param in $requiredParams) {
            if ($content -notmatch $param) {
                return $false
            }
        }
        return $true
    }
    return $false
} -SuccessMessage "Alle 7 Risk-Parameter vorhanden" -FailureMessage "Fehlende Risk-Parameter!" -Severity "ERROR"

# ============================================================================
# KATEGORIE 3: MEXC-API-Credentials (CRITICAL)
# ============================================================================

Write-Host ""
Write-Host "[KATEGORIE 3] MEXC-API-Credentials" -ForegroundColor Cyan
Write-Host "─────────────────────────────────────────────────────────────────" -ForegroundColor Gray

Test-Check -Name "SR-003.1" -Test {
    # MEXC_API_KEY vorhanden
    if (Test-Path "$RepoRoot\.env.template") {
        $content = Get-Content "$RepoRoot\.env.template" -Raw
        return ($content -match 'MEXC_API_KEY')
    }
    return $false
} -SuccessMessage "MEXC_API_KEY vorhanden" -FailureMessage "MEXC_API_KEY fehlt - System nicht funktionsfähig!" -Severity "ERROR"

Test-Check -Name "SR-003.2" -Test {
    # MEXC_API_SECRET vorhanden
    if (Test-Path "$RepoRoot\.env.template") {
        $content = Get-Content "$RepoRoot\.env.template" -Raw
        return ($content -match 'MEXC_API_SECRET')
    }
    return $false
} -SuccessMessage "MEXC_API_SECRET vorhanden" -FailureMessage "MEXC_API_SECRET fehlt - System nicht funktionsfähig!" -Severity "ERROR"

# ============================================================================
# KATEGORIE 4: docker-compose.yml (Legacy-Service)
# ============================================================================

Write-Host ""
Write-Host "[KATEGORIE 4] docker-compose.yml Cleanup" -ForegroundColor Cyan
Write-Host "─────────────────────────────────────────────────────────────────" -ForegroundColor Gray

Test-Check -Name "Task-4.1" -Test {
    # cdb_signal_gen auskommentiert oder entfernt
    if (Test-Path "$RepoRoot\docker-compose.yml") {
        $content = Get-Content "$RepoRoot\docker-compose.yml" -Raw
        # Prüfe ob Service auskommentiert ist ODER nicht existiert
        return ($content -match '^\s*#.*cdb_signal_gen:' -or $content -notmatch '^\s*cdb_signal_gen:')
    }
    return $false
} -SuccessMessage "cdb_signal_gen entfernt/auskommentiert" -FailureMessage "cdb_signal_gen noch aktiv in compose!" -Severity "ERROR"

Test-Check -Name "Task-4.2" -Test {
    # docker-compose.yml Syntax valide
    try {
        $composeCheck = & docker compose -f "$RepoRoot\docker-compose.yml" config --quiet 2>&1
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $null  # Docker nicht verfügbar
    }
} -SuccessMessage "docker-compose.yml Syntax valide" -FailureMessage "docker-compose.yml hat Syntax-Fehler!" -Severity "ERROR"

# ============================================================================
# KATEGORIE 5: Completeness & Konsistenz
# ============================================================================

Write-Host ""
Write-Host "[KATEGORIE 5] Completeness & Konsistenz" -ForegroundColor Cyan
Write-Host "─────────────────────────────────────────────────────────────────" -ForegroundColor Gray

Test-Check -Name "Vollständigkeit" -Test {
    # Alle kritischen ENV-Keys in .env.template
    if (Test-Path "$RepoRoot\.env.template") {
        $content = Get-Content "$RepoRoot\.env.template" -Raw
        $criticalKeys = @(
            'POSTGRES_PASSWORD',
            'REDIS_PASSWORD',
            'GRAFANA_PASSWORD',
            'MEXC_API_KEY',
            'MEXC_API_SECRET'
        )
        foreach ($key in $criticalKeys) {
            if ($content -notmatch $key) {
                return $false
            }
        }
        return $true
    }
    return $false
} -SuccessMessage "Alle kritischen ENV-Keys vorhanden" -FailureMessage "Fehlende kritische ENV-Keys!" -Severity "ERROR"

Test-Check -Name "Platzhalter" -Test {
    # Alle Secrets haben <SET_IN_ENV> Platzhalter
    if (Test-Path "$RepoRoot\.env.template") {
        $content = Get-Content "$RepoRoot\.env.template" -Raw
        $lines = $content -split "`n"
        $secretLines = $lines | Where-Object { $_ -match '(PASSWORD|SECRET|KEY)=' -and $_ -notmatch '^#' }
        foreach ($line in $secretLines) {
            if ($line -notmatch '<SET_IN_ENV>') {
                return $false
            }
        }
        return $true
    }
    return $false
} -SuccessMessage "Alle Secrets nutzen <SET_IN_ENV> Platzhalter" -FailureMessage "Einige Secrets ohne Platzhalter!" -Severity "WARNING"

# ============================================================================
# ZUSAMMENFASSUNG
# ============================================================================

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "Validation Summary" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

if ($IssuesFound -eq 0) {
    Write-Host "✅ ALLE CHECKS BESTANDEN" -ForegroundColor Green
    Write-Host ""
    Write-Host "Status: " -NoNewline
    Write-Host "✅ GO für Cleanroom-Migration" -ForegroundColor Green
    Write-Host ""
    Write-Host "Nächste Schritte:" -ForegroundColor Cyan
    Write-Host "1. Echte .env erstellen: cp .env.template .env" -ForegroundColor White
    Write-Host "2. Alle <SET_IN_ENV> durch echte Werte ersetzen" -ForegroundColor White
    Write-Host "3. docker compose up -d" -ForegroundColor White
    Write-Host "4. Health-Checks prüfen (alle Services healthy?)" -ForegroundColor White
    Write-Host "5. Smoke-Test: market_data → signals → orders → order_results" -ForegroundColor White
} else {
    Write-Host "❌ $IssuesFound ISSUE(S) GEFUNDEN" -ForegroundColor Red
    Write-Host ""
    Write-Host "Status: " -NoNewline
    Write-Host "⚠️ NO-GO für Migration" -ForegroundColor Red
    Write-Host ""
    Write-Host "Behebe die oben genannten Fehler und führe dann erneut aus:" -ForegroundColor Yellow
    Write-Host "  .\pre_migration_validation.ps1" -ForegroundColor White
}

Write-Host ""

exit $IssuesFound
