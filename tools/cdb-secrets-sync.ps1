#Requires -Version 5.1

<#
.SYNOPSIS
    CDB Secrets Sync - Synchronisiert Tresor-Zone mit lokalen Secrets

.DESCRIPTION
    Synchronisiert .cdb_local/.secrets/ → .secrets/ und updated .env automatisch.
    Verhindert Redis/PostgreSQL Auth-Errors durch Passwort-Mismatches.

.PARAMETER DryRun
    Zeigt nur, was passieren würde (kein Write)

.EXAMPLE
    .\cdb-secrets-sync.ps1
    .\cdb-secrets-sync.ps1 -DryRun
#>

param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# === KONFIGURATION ===
$SOURCE_DIR = ".cdb_local\.secrets"
$TARGET_DIR = ".secrets"
$ENV_FILE = ".env"
$REQUIRED_SECRETS = @("redis_password", "postgres_password", "grafana_password")

# === FARBEN FÜR OUTPUT ===
function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }

# === HEADER ===
Write-Host "🔐 CDB Secrets Sync" -ForegroundColor Blue
if ($DryRun) {
    Write-Warning "DRY RUN MODE - Keine Änderungen werden geschrieben"
}
Write-Host ""

# === SCHRITT 1: VALIDIERUNG ===
Write-Info "Validiere Verzeichnisse..."

if (-not (Test-Path $SOURCE_DIR)) {
    Write-Error "Source-Verzeichnis nicht gefunden: $SOURCE_DIR"
    Write-Info "Lösung: Stelle sicher, dass .cdb_local/.secrets/ existiert (Tresor-Zone)"
    exit 1
}

if (-not (Test-Path $TARGET_DIR)) {
    if ($DryRun) {
        Write-Info "[DRY RUN] Würde erstellen: $TARGET_DIR"
    } else {
        New-Item -ItemType Directory -Path $TARGET_DIR | Out-Null
        Write-Success "Erstellt: $TARGET_DIR"
    }
}

if (-not (Test-Path $ENV_FILE)) {
    Write-Error ".env nicht gefunden!"
    Write-Info "Lösung: Kopiere .env.example → .env"
    exit 1
}

# === SCHRITT 2: SECRETS SYNC ===
Write-Host "`n📋 Sync-Plan:" -ForegroundColor Blue

$syncActions = @()

foreach ($secretName in $REQUIRED_SECRETS) {
    $sourcePath = Join-Path $SOURCE_DIR $secretName
    $targetPath = Join-Path $TARGET_DIR $secretName

    if (-not (Test-Path $sourcePath)) {
        Write-Warning "Source fehlt: $sourcePath (übersprungen)"
        continue
    }

    $sourceContent = (Get-Content $sourcePath -Raw).Trim()

    if (Test-Path $targetPath) {
        $targetContent = (Get-Content $targetPath -Raw).Trim()
        if ($sourceContent -eq $targetContent) {
            Write-Success "$secretName`: Identisch (kein Update nötig)"
            $syncActions += @{
                Name = $secretName
                Action = "SKIP"
                Content = $sourceContent
            }
        } else {
            Write-Warning "$secretName`: Unterschied gefunden → Update"
            $syncActions += @{
                Name = $secretName
                Action = "UPDATE"
                Content = $sourceContent
            }
        }
    } else {
        Write-Info "$secretName`: Neu → Kopieren"
        $syncActions += @{
            Name = $secretName
            Action = "CREATE"
            Content = $sourceContent
        }
    }
}

# === SCHRITT 3: SECRETS SCHREIBEN ===
if (-not $DryRun) {
    Write-Host "`n🔄 Schreibe Secrets..." -ForegroundColor Blue

    foreach ($action in $syncActions) {
        if ($action.Action -ne "SKIP") {
            $targetPath = Join-Path $TARGET_DIR $action.Name
            $action.Content | Out-File -FilePath $targetPath -Encoding ASCII -NoNewline
            Write-Success "Geschrieben: $($action.Name)"
        }
    }
}

# === SCHRITT 4: .ENV UPDATE ===
Write-Host "`n📝 .env Updates:" -ForegroundColor Blue

$envContent = Get-Content $ENV_FILE -Raw
$envUpdated = $false

# Redis Password
$redisSecret = $syncActions | Where-Object { $_.Name -eq "redis_password" }
if ($redisSecret) {
    $redisPassword = $redisSecret.Content
    if ($envContent -match "REDIS_PASSWORD=(.*)") {
        $currentValue = $matches[1].Trim()
        if ($currentValue -ne $redisPassword) {
            Write-Warning "REDIS_PASSWORD: Update erforderlich"
            $envContent = $envContent -replace "REDIS_PASSWORD=.*", "REDIS_PASSWORD=$redisPassword"
            $envUpdated = $true
        } else {
            Write-Success "REDIS_PASSWORD: Keine Änderung"
        }
    } else {
        Write-Warning "REDIS_PASSWORD nicht in .env → Hinzufügen"
        $envContent += "`nREDIS_PASSWORD=$redisPassword"
        $envUpdated = $true
    }
}

# PostgreSQL Password
$postgresSecret = $syncActions | Where-Object { $_.Name -eq "postgres_password" }
if ($postgresSecret) {
    $postgresPassword = $postgresSecret.Content
    if ($envContent -match "POSTGRES_PASSWORD=(.*)") {
        $currentValue = $matches[1].Trim()
        if ($currentValue -ne $postgresPassword) {
            Write-Warning "POSTGRES_PASSWORD: Update erforderlich"
            $envContent = $envContent -replace "POSTGRES_PASSWORD=.*", "POSTGRES_PASSWORD=$postgresPassword"
            $envUpdated = $true
        } else {
            Write-Success "POSTGRES_PASSWORD: Keine Änderung"
        }
    } else {
        Write-Warning "POSTGRES_PASSWORD nicht in .env → Hinzufügen"
        $envContent += "`nPOSTGRES_PASSWORD=$postgresPassword"
        $envUpdated = $true
    }
}

# === SCHRITT 5: .ENV SCHREIBEN ===
if ($envUpdated) {
    if ($DryRun) {
        Write-Info "[DRY RUN] Würde .env aktualisieren"
    } else {
        $envContent | Out-File -FilePath $ENV_FILE -Encoding UTF8 -NoNewline
        Write-Success ".env aktualisiert"
    }
} else {
    Write-Success ".env ist bereits aktuell"
}

# === ZUSAMMENFASSUNG ===
Write-Host "`n✅ Sync abgeschlossen!" -ForegroundColor Green

if ($DryRun) {
    Write-Warning "DRY RUN: Keine Dateien wurden geändert"
    Write-Info "Führe ohne -DryRun aus, um Änderungen zu schreiben"
}

Write-Host ""
exit 0
