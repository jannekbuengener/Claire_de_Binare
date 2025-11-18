# ============================================================================
# HISTORICAL TEMPLATE - Documents 2025-11-16 migration
# ============================================================================
# Repository : Claire_de_Binare_Cleanroom
# Context    : Migration from backup repo into Cleanroom baseline
# Status     : Historical reference only (do not re-run on current baseline)
#
# Original Header:
# Claire de Binare - Cleanroom Migration Script
# ZWECK: Automatisierte Migration vom Backup-Repo ins Cleanroom-Repo
# AUTOR: Pipeline 4 - Multi-Agenten-System
# DATUM: 2025-11-16
# ============================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$SourceRepo = (Split-Path -Parent $PSScriptRoot),

    [Parameter(Mandatory=$true)]
    [string]$TargetRepo,

    [switch]$DryRun = $false,
    [switch]$SkipServices = $false,
    [switch]$ShowDetails = $false
)

$ErrorActionPreference = "Stop"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "Claire de Binaire - Cleanroom Migration" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Source Repo: $SourceRepo" -ForegroundColor Gray
Write-Host "Target Repo: $TargetRepo" -ForegroundColor Gray
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN] Keine Dateien werden kopiert. Nur Vorschau." -ForegroundColor Yellow
    Write-Host ""
}

# ============================================================================
# Hilfsfunktionen
# ============================================================================

function Copy-File-Safe {
    param(
        [string]$Source,
        [string]$Target,
        [string]$Description = ""
    )

    $SourceFull = Join-Path $SourceRepo $Source
    $TargetFull = Join-Path $TargetRepo $Target

    if (-not (Test-Path $SourceFull)) {
        Write-Host "  ⚠️  SKIP: $Description (Source nicht gefunden)" -ForegroundColor Yellow
        if ($ShowDetails) {
            Write-Host "       Source: $SourceFull" -ForegroundColor Gray
        }
        return $false
    }

    if ($DryRun) {
        Write-Host "  [DRY RUN] Würde kopieren: $Description" -ForegroundColor Gray
        if ($ShowDetails) {
            Write-Host "       $Source → $Target" -ForegroundColor DarkGray
        }
        return $true
    }

    # Zielverzeichnis erstellen falls nötig
    $TargetDir = Split-Path -Parent $TargetFull
    if (-not (Test-Path $TargetDir)) {
        New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    }

    Copy-Item -Path $SourceFull -Destination $TargetFull -Force
    Write-Host "  ✅ $Description" -ForegroundColor Green
    if ($ShowDetails) {
        Write-Host "       $Source → $Target" -ForegroundColor Gray
    }
    return $true
}

function Copy-Directory-Safe {
    param(
        [string]$Source,
        [string]$Target,
        [string]$Description = ""
    )

    $SourceFull = Join-Path $SourceRepo $Source
    $TargetFull = Join-Path $TargetRepo $Target

    if (-not (Test-Path $SourceFull)) {
        Write-Host "  ⚠️  SKIP: $Description (Source nicht gefunden)" -ForegroundColor Yellow
        return $false
    }

    if ($DryRun) {
        Write-Host "  [DRY RUN] Würde kopieren: $Description (Ordner)" -ForegroundColor Gray
        return $true
    }

    # Zielverzeichnis erstellen falls nötig
    if (-not (Test-Path $TargetFull)) {
        New-Item -ItemType Directory -Path $TargetFull -Force | Out-Null
    }

    Copy-Item -Path "$SourceFull\*" -Destination $TargetFull -Recurse -Force
    Write-Host "  ✅ $Description (Ordner)" -ForegroundColor Green
    return $true
}

# ============================================================================
# Validierung
# ============================================================================

Write-Host "[VALIDIERUNG] Repos prüfen..." -ForegroundColor Yellow

if (-not (Test-Path $SourceRepo)) {
    Write-Host "❌ Source-Repo nicht gefunden: $SourceRepo" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $TargetRepo)) {
    Write-Host "⚠️  Target-Repo existiert nicht. Erstelle..." -ForegroundColor Yellow
    if (-not $DryRun) {
        New-Item -ItemType Directory -Path $TargetRepo -Force | Out-Null
        Write-Host "✅ Target-Repo erstellt" -ForegroundColor Green
    }
}

# Prüfe ob sandbox/ existiert
$SandboxPath = Join-Path $SourceRepo "sandbox"
if (-not (Test-Path $SandboxPath)) {
    Write-Host "❌ sandbox/ nicht gefunden in Source-Repo!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Validierung erfolgreich" -ForegroundColor Green
Write-Host ""

# ============================================================================
# KATEGORIE 1: Kanonische Dokumentation (sandbox/ → backoffice/docs/)
# ============================================================================

Write-Host "[KATEGORIE 1] Kanonische Dokumentation..." -ForegroundColor Yellow

$filesCopied = 0

$filesCopied += Copy-File-Safe -Source "sandbox\canonical_schema.yaml" -Target "backoffice\docs\canonical_schema.yaml" -Description "canonical_schema.yaml"
$filesCopied += Copy-File-Safe -Source "sandbox\canonical_model_overview.md" -Target "backoffice\docs\canonical_model_overview.md" -Description "canonical_model_overview.md"
$filesCopied += Copy-File-Safe -Source "sandbox\canonical_readiness_report.md" -Target "backoffice\docs\canonical_readiness_report.md" -Description "canonical_readiness_report.md"
$filesCopied += Copy-File-Safe -Source "sandbox\output.md" -Target "backoffice\docs\SYSTEM_REFERENCE.md" -Description "SYSTEM_REFERENCE.md (umbenannt)"
$filesCopied += Copy-File-Safe -Source "sandbox\infra_knowledge.md" -Target "backoffice\docs\infra_knowledge.md" -Description "infra_knowledge.md"
$filesCopied += Copy-File-Safe -Source "sandbox\file_index.md" -Target "backoffice\docs\file_index.md" -Description "file_index.md"
$filesCopied += Copy-File-Safe -Source "sandbox\env_index.md" -Target "backoffice\docs\env_index.md" -Description "env_index.md"

Write-Host "  → $filesCopied/7 Dateien kopiert" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# KATEGORIE 2: Infra-Templates (sandbox/ → backoffice/templates/)
# ============================================================================

Write-Host "[KATEGORIE 2] Infra-Templates..." -ForegroundColor Yellow

$filesCopied = 0

$filesCopied += Copy-File-Safe -Source "sandbox\infra_templates.md" -Target "backoffice\templates\infra_templates.md" -Description "infra_templates.md"
$filesCopied += Copy-File-Safe -Source "sandbox\project_template.md" -Target "backoffice\templates\project_template.md" -Description "project_template.md"
$filesCopied += Copy-File-Safe -Source "sandbox\.env.template" -Target "backoffice\templates\.env.template" -Description ".env.template (Backup)"

Write-Host "  → $filesCopied/3 Dateien kopiert" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# KATEGORIE 3: Konfiguration (Root → Root)
# ============================================================================

Write-Host "[KATEGORIE 3] Konfiguration (Root)..." -ForegroundColor Yellow

$filesCopied = 0

$filesCopied += Copy-File-Safe -Source ".env.template" -Target ".env.template" -Description ".env.template (Haupt-Template)"
$filesCopied += Copy-File-Safe -Source "docker-compose.yml" -Target "docker-compose.yml" -Description "docker-compose.yml"
$filesCopied += Copy-File-Safe -Source "prometheus.yml" -Target "prometheus.yml" -Description "prometheus.yml"
$filesCopied += Copy-File-Safe -Source ".gitignore" -Target ".gitignore" -Description ".gitignore"

Write-Host "  → $filesCopied/4 Dateien kopiert" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# KATEGORIE 4: Service-Code (backoffice/services/)
# ============================================================================

if (-not $SkipServices) {
    Write-Host "[KATEGORIE 4] Service-Code..." -ForegroundColor Yellow

    $servicesCopied = 0

    $servicesCopied += Copy-Directory-Safe -Source "backoffice\services\signal_engine" -Target "backoffice\services\signal_engine" -Description "Signal Engine"
    $servicesCopied += Copy-Directory-Safe -Source "backoffice\services\risk_manager" -Target "backoffice\services\risk_manager" -Description "Risk Manager"
    $servicesCopied += Copy-Directory-Safe -Source "backoffice\services\execution_service" -Target "backoffice\services\execution_service" -Description "Execution Service"

    Write-Host "  → $servicesCopied/3 MVP-Services kopiert" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host "[KATEGORIE 4] Service-Code... ÜBERSPRUNGEN (--SkipServices)" -ForegroundColor Gray
    Write-Host ""
}

# ============================================================================
# KATEGORIE 5: Screeners (Root → Root)
# ============================================================================

Write-Host "[KATEGORIE 5] Screeners..." -ForegroundColor Yellow

$filesCopied = 0

$filesCopied += Copy-File-Safe -Source "mexc_top5_ws.py" -Target "mexc_top5_ws.py" -Description "mexc_top5_ws.py"
$filesCopied += Copy-File-Safe -Source "mexc_top_movers.py" -Target "mexc_top_movers.py" -Description "mexc_top_movers.py"
$filesCopied += Copy-File-Safe -Source "Dockerfile" -Target "Dockerfile" -Description "Dockerfile"

Write-Host "  → $filesCopied/3 Dateien kopiert" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# KATEGORIE 6: Tests (tests/ → tests/)
# ============================================================================

Write-Host "[KATEGORIE 6] Tests..." -ForegroundColor Yellow

$filesCopied = 0

$filesCopied += Copy-File-Safe -Source "tests\conftest.py" -Target "tests\conftest.py" -Description "conftest.py"
$filesCopied += Copy-Directory-Safe -Source "tests\unit" -Target "tests\unit" -Description "Unit-Tests"
$filesCopied += Copy-Directory-Safe -Source "tests\integration" -Target "tests\integration" -Description "Integration-Tests"

Write-Host "  → Tests kopiert" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# KATEGORIE 7: Migration-Historie (Optional)
# ============================================================================

Write-Host "[KATEGORIE 7] Migration-Historie (optional)..." -ForegroundColor Yellow

$filesCopied = 0

$filesCopied += Copy-File-Safe -Source "sandbox\PIPELINE_COMPLETE_SUMMARY.md" -Target "backoffice\docs\PIPELINE_COMPLETE_SUMMARY.md" -Description "PIPELINE_COMPLETE_SUMMARY.md"
$filesCopied += Copy-File-Safe -Source "sandbox\PRE_MIGRATION_EXECUTION_REPORT.md" -Target "backoffice\docs\PRE_MIGRATION_EXECUTION_REPORT.md" -Description "PRE_MIGRATION_EXECUTION_REPORT.md"
$filesCopied += Copy-File-Safe -Source "sandbox\CLEANROOM_MIGRATION_MANIFEST.md" -Target "backoffice\docs\CLEANROOM_MIGRATION_MANIFEST.md" -Description "CLEANROOM_MIGRATION_MANIFEST.md"
$filesCopied += Copy-File-Safe -Source "sandbox\ADRs_FOR_DECISION_LOG.md" -Target "backoffice\docs\ADRs_FOR_DECISION_LOG.md" -Description "ADRs_FOR_DECISION_LOG.md"

Write-Host "  → $filesCopied/4 Dateien kopiert" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# POST-MIGRATION CHECKS
# ============================================================================

if (-not $DryRun) {
    Write-Host "[POST-MIGRATION] Validierungen..." -ForegroundColor Yellow

    # Check 1: .env.template existiert
    $envTemplate = Join-Path $TargetRepo ".env.template"
    if (Test-Path $envTemplate) {
        Write-Host "  ✅ .env.template existiert im Target-Repo" -ForegroundColor Green
    } else {
        Write-Host "  ❌ .env.template fehlt im Target-Repo!" -ForegroundColor Red
    }

    # Check 2: Keine .env im Target
    $env = Join-Path $TargetRepo ".env"
    if (Test-Path $env) {
        Write-Host "  ⚠️  WARNUNG: .env existiert im Target-Repo (sollte nicht sein!)" -ForegroundColor Yellow
    } else {
        Write-Host "  ✅ Keine .env im Target-Repo (korrekt)" -ForegroundColor Green
    }

    # Check 3: canonical_schema.yaml existiert
    $canonicalSchema = Join-Path $TargetRepo "backoffice\docs\canonical_schema.yaml"
    if (Test-Path $canonicalSchema) {
        Write-Host "  ✅ canonical_schema.yaml vorhanden" -ForegroundColor Green
    } else {
        Write-Host "  ❌ canonical_schema.yaml fehlt!" -ForegroundColor Red
    }

    # Check 4: docker-compose.yml validieren
    try {
        $composeFile = Join-Path $TargetRepo "docker-compose.yml"
        if (Test-Path $composeFile) {
            Push-Location $TargetRepo
            $composeCheck = & docker compose -f "docker-compose.yml" config --quiet 2>&1
            Pop-Location

            if ($LASTEXITCODE -eq 0) {
                Write-Host "  ✅ docker-compose.yml Syntax valide" -ForegroundColor Green
            } else {
                Write-Host "  ❌ docker-compose.yml hat Fehler: $composeCheck" -ForegroundColor Red
            }
        }
    } catch {
        Write-Host "  ⚠️  docker compose nicht verfügbar - Validierung übersprungen" -ForegroundColor Yellow
    }

    Write-Host ""
}

# ============================================================================
# ZUSAMMENFASSUNG
# ============================================================================

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "Migration - Zusammenfassung" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN MODUS] - Keine Dateien wurden kopiert" -ForegroundColor Yellow
} else {
    Write-Host "✅ Migration abgeschlossen" -ForegroundColor Green
}

Write-Host ""
Write-Host "Kategorien:" -ForegroundColor Cyan
Write-Host "  1. Kanonische Dokumentation: 7 Dateien" -ForegroundColor White
Write-Host "  2. Infra-Templates: 3 Dateien" -ForegroundColor White
Write-Host "  3. Konfiguration: 4 Dateien" -ForegroundColor White
if (-not $SkipServices) {
    Write-Host "  4. Service-Code: 3 Services" -ForegroundColor White
} else {
    Write-Host "  4. Service-Code: ÜBERSPRUNGEN" -ForegroundColor Gray
}
Write-Host "  5. Screeners: 3 Dateien" -ForegroundColor White
Write-Host "  6. Tests: 3+ Dateien" -ForegroundColor White
Write-Host "  7. Migration-Historie: 4 Dateien" -ForegroundColor White
Write-Host ""

Write-Host "Nächste Schritte:" -ForegroundColor Cyan
Write-Host "1. cd $TargetRepo" -ForegroundColor White
Write-Host "2. DECISION_LOG.md mit 3 ADRs ergänzen (siehe sandbox\ADRs_FOR_DECISION_LOG.md)" -ForegroundColor White
Write-Host "3. .env erstellen: cp .env.template .env" -ForegroundColor White
Write-Host "4. Platzhalter in .env ersetzen" -ForegroundColor White
Write-Host "5. docker compose config --quiet" -ForegroundColor White
Write-Host "6. docker compose up -d" -ForegroundColor White
Write-Host "7. Health-Checks prüfen: docker compose ps" -ForegroundColor White
Write-Host "8. Tests ausführen: pytest -v" -ForegroundColor White
Write-Host "9. Git initial commit" -ForegroundColor White
Write-Host ""
Write-Host "Für Details siehe: backoffice\docs\CLEANROOM_MIGRATION_MANIFEST.md" -ForegroundColor Cyan
Write-Host ""
