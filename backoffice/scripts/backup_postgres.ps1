# PostgreSQL Backup Script - Claire de Binare
# Version: 1.0.0
# Speicherort: F:\Claire_Backups\PostgreSQL\
# Retention: 14 Tage

param(
    [string]$BackupRoot = "F:\Claire_Backups\PostgreSQL",
    [int]$RetentionDays = 14,
    [switch]$Verbose
)

# ANSI Colors
$RED = "`e[31m"
$GREEN = "`e[32m"
$YELLOW = "`e[33m"
$BLUE = "`e[34m"
$RESET = "`e[0m"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "ERROR" { $RED }
        "SUCCESS" { $GREEN }
        "WARN" { $YELLOW }
        default { $BLUE }
    }
    Write-Host "${color}[$timestamp][$Level]${RESET} $Message"
}

Write-Log "=== PostgreSQL Backup Started ===" "INFO"

# 1. Backup-Verzeichnis erstellen
try {
    if (-not (Test-Path $BackupRoot)) {
        New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
        Write-Log "Backup-Verzeichnis erstellt: $BackupRoot" "SUCCESS"
    } else {
        Write-Log "Backup-Verzeichnis existiert: $BackupRoot" "INFO"
    }
} catch {
    Write-Log "Fehler beim Erstellen des Backup-Verzeichnisses: $_" "ERROR"
    exit 1
}

# 2. Backup-Dateiname mit Timestamp
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$backupFile = Join-Path $BackupRoot "cdb_backup_$timestamp.sql"
$logFile = Join-Path $BackupRoot "backup_log.txt"

Write-Log "Backup-Datei: $backupFile" "INFO"

# 3. PostgreSQL Container prüfen (direkt via docker ps)
Write-Log "Prüfe PostgreSQL Container..." "INFO"

$containerCheck = docker ps --filter "name=cdb_postgres" --format "{{.Names}}:{{.Status}}" 2>&1

if ($containerCheck -match "cdb_postgres:Up") {
    Write-Log "PostgreSQL Container: Running" "SUCCESS"
} else {
    Write-Log "PostgreSQL Container nicht gefunden oder nicht running!" "ERROR"
    Write-Log "Bitte starte den Container manuell: docker compose up -d cdb_postgres" "INFO"
    exit 1
}

# 4. ENV-Variablen laden
Write-Log "Lade Datenbank-Credentials..." "INFO"

$envFile = ".env"
if (-not (Test-Path $envFile)) {
    Write-Log ".env Datei nicht gefunden!" "ERROR"
    exit 1
}

$envVars = @{}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        $envVars[$key] = $value
    }
}

$POSTGRES_USER = $envVars["POSTGRES_USER"]
$POSTGRES_PASSWORD = $envVars["POSTGRES_PASSWORD"]
$POSTGRES_DB = $envVars["POSTGRES_DB"]
$POSTGRES_HOST = $envVars["POSTGRES_HOST"]
$POSTGRES_PORT = $envVars["POSTGRES_PORT"]

if (-not $POSTGRES_USER -or -not $POSTGRES_DB) {
    Write-Log "Fehlende PostgreSQL Credentials in .env!" "ERROR"
    exit 1
}

Write-Log "Database: $POSTGRES_DB | User: $POSTGRES_USER" "INFO"

# 5. Backup durchführen (via Docker exec)
Write-Log "Starte Backup..." "INFO"

$env:PGPASSWORD = $POSTGRES_PASSWORD

try {
    # pg_dump via Docker Container ausführen
    $dumpCommand = "docker exec cdb_postgres pg_dump -U $POSTGRES_USER -d $POSTGRES_DB --clean --if-exists --no-owner --no-acl"

    if ($Verbose) {
        Write-Log "Command: $dumpCommand" "INFO"
    }

    # Backup ausführen und in Datei schreiben
    $output = Invoke-Expression "$dumpCommand 2>&1"

    # Fehlerprüfung
    if ($LASTEXITCODE -ne 0) {
        Write-Log "pg_dump fehlgeschlagen! Exit Code: $LASTEXITCODE" "ERROR"
        Write-Log "Output: $output" "ERROR"
        exit 1
    }

    # Output in Datei schreiben
    $output | Out-File -FilePath $backupFile -Encoding UTF8

    $fileSize = (Get-Item $backupFile).Length / 1KB
    Write-Log "Backup erfolgreich: $([math]::Round($fileSize, 2)) KB" "SUCCESS"

} catch {
    Write-Log "Backup fehlgeschlagen: $_" "ERROR"
    exit 1
} finally {
    # Passwort aus ENV entfernen
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}

# 6. Backup validieren
Write-Log "Validiere Backup..." "INFO"

$backupContent = Get-Content $backupFile -TotalCount 10
if ($backupContent -match "PostgreSQL database dump") {
    Write-Log "Backup-Datei ist valide (PostgreSQL Dump erkannt)" "SUCCESS"
} else {
    Write-Log "Backup-Datei könnte korrupt sein (kein PostgreSQL Header)" "WARN"
}

# Prüfe auf kritische Tabellen
$criticalTables = @("signals", "orders", "trades", "positions", "portfolio_snapshots")
$backupText = Get-Content $backupFile -Raw

$missingTables = @()
foreach ($table in $criticalTables) {
    if ($backupText -notmatch "CREATE TABLE.*$table") {
        $missingTables += $table
    }
}

if ($missingTables.Count -gt 0) {
    Write-Log "WARNUNG: Folgende Tabellen fehlen im Backup: $($missingTables -join ', ')" "WARN"
} else {
    Write-Log "Alle 5 kritischen Tabellen im Backup gefunden" "SUCCESS"
}

# 7. Alte Backups löschen (Retention)
Write-Log "Bereinige alte Backups (älter als $RetentionDays Tage)..." "INFO"

$cutoffDate = (Get-Date).AddDays(-$RetentionDays)
$oldBackups = Get-ChildItem -Path $BackupRoot -Filter "cdb_backup_*.sql" |
    Where-Object { $_.LastWriteTime -lt $cutoffDate }

if ($oldBackups.Count -gt 0) {
    foreach ($oldBackup in $oldBackups) {
        Remove-Item $oldBackup.FullName -Force
        Write-Log "Gelöscht: $($oldBackup.Name) ($(Get-Date $oldBackup.LastWriteTime -Format 'yyyy-MM-dd'))" "INFO"
    }
    Write-Log "Gelöscht: $($oldBackups.Count) alte Backups" "SUCCESS"
} else {
    Write-Log "Keine alten Backups zum Löschen gefunden" "INFO"
}

# 8. Backup-Log schreiben
$logEntry = @"
[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Backup erfolgreich
  Datei: $backupFile
  Größe: $([math]::Round($fileSize, 2)) KB
  Tabellen: $($criticalTables.Count) / $($criticalTables.Count)
  Retention: Gelöscht $($oldBackups.Count) alte Backups

"@

Add-Content -Path $logFile -Value $logEntry

# 9. Zusammenfassung
Write-Log "" "INFO"
Write-Log "=== Backup Complete ===" "SUCCESS"
Write-Log "Datei: $backupFile" "INFO"
Write-Log "Größe: $([math]::Round($fileSize, 2)) KB" "INFO"
Write-Log "Aktive Backups: $($(Get-ChildItem -Path $BackupRoot -Filter 'cdb_backup_*.sql').Count)" "INFO"
Write-Log "Log: $logFile" "INFO"
Write-Log "" "INFO"

# Optional: Neueste Backups anzeigen
if ($Verbose) {
    Write-Log "Letzte 5 Backups:" "INFO"
    Get-ChildItem -Path $BackupRoot -Filter "cdb_backup_*.sql" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 5 |
        ForEach-Object {
            $size = [math]::Round($_.Length / 1KB, 2)
            Write-Log "  $($_.Name) - $size KB - $(Get-Date $_.LastWriteTime -Format 'yyyy-MM-dd HH:mm')" "INFO"
        }
}

exit 0
