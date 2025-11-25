# Repository Backup Script - Claire de Binare
# Version: 1.0.0
# Speicherort: F:\Claire_Backups\Repository\
# Retention: 14 Tage
# Sichert: Git Repo + .env (verschlüsselt) + Docker Volumes

param(
    [string]$BackupRoot = "F:\Claire_Backups\Repository",
    [int]$RetentionDays = 14,
    [switch]$IncludeEnv,
    [switch]$IncludeDockerVolumes,
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

Write-Log "=== Repository Backup Started ===" "INFO"

# 1. Backup-Verzeichnis erstellen
try {
    if (-not (Test-Path $BackupRoot)) {
        New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
        Write-Log "Backup-Verzeichnis erstellt: $BackupRoot" "SUCCESS"
    }
} catch {
    Write-Log "Fehler beim Erstellen des Backup-Verzeichnisses: $_" "ERROR"
    exit 1
}

# 2. Repository-Pfad ermitteln
$repoPath = git rev-parse --show-toplevel 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Log "Nicht in einem Git-Repository!" "ERROR"
    exit 1
}

# Konvertiere Unix-Pfad zu Windows-Pfad falls nötig
if ($repoPath -match "^/([a-z])/") {
    $drive = $matches[1].ToUpper()
    $repoPath = $repoPath -replace "^/[a-z]/", "$drive`:\"
    $repoPath = $repoPath -replace "/", "\"
}

Write-Log "Repository: $repoPath" "INFO"

# 3. Git-Status prüfen
Write-Log "Prüfe Git-Status..." "INFO"

$gitStatus = git status --porcelain 2>&1

if ($gitStatus) {
    Write-Log "WARNUNG: Uncommitted changes gefunden!" "WARN"
    Write-Log "  Anzahl geänderter Dateien: $(($gitStatus -split "`n").Count)" "WARN"

    if (-not $Force) {
        Write-Log "  Backup könnte inkonsistent sein. Fortfahren? (Ctrl+C zum Abbrechen)" "WARN"
        Start-Sleep -Seconds 3
    }
}

$currentBranch = git branch --show-current
$latestCommit = git rev-parse --short HEAD

Write-Log "Branch: $currentBranch | Commit: $latestCommit" "INFO"

# 4. Backup-Dateiname mit Timestamp + Commit
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$backupName = "claire_repo_${timestamp}_${latestCommit}"
$backupDir = Join-Path $BackupRoot $backupName
$backupArchive = "$backupDir.zip"

# 5. Temporäres Backup-Verzeichnis erstellen
Write-Log "Erstelle Backup-Struktur..." "INFO"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

# 6. Git Repository archivieren (nur tracked files)
Write-Log "Archiviere Git Repository..." "INFO"

try {
    # Git Archive (nur versionierte Dateien)
    $gitArchive = Join-Path $backupDir "repository.zip"
    git archive --format=zip --output="$gitArchive" HEAD 2>&1 | Out-Null

    if ($LASTEXITCODE -ne 0) {
        throw "Git archive failed"
    }

    $archiveSize = (Get-Item $gitArchive).Length / 1MB
    Write-Log "Repository archiviert: $([math]::Round($archiveSize, 2)) MB" "SUCCESS"

} catch {
    Write-Log "Git-Archivierung fehlgeschlagen: $_" "ERROR"
    Remove-Item $backupDir -Recurse -Force -ErrorAction SilentlyContinue
    exit 1
}

# 7. Git-Metadaten sichern
Write-Log "Sichere Git-Metadaten..." "INFO"

$metadataFile = Join-Path $backupDir "git_metadata.txt"

@"
Repository Backup Metadata
Created: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Branch: $currentBranch
Commit: $(git rev-parse HEAD)
Commit Short: $latestCommit
Commit Message: $(git log -1 --pretty=%B)
Commit Author: $(git log -1 --pretty=%an)
Commit Date: $(git log -1 --pretty=%ci)
Total Commits: $(git rev-list --count HEAD)
Remotes: $(git remote -v)
Uncommitted Changes: $(if ($gitStatus) { "Yes ($(@($gitStatus -split "`n").Count) files)" } else { "No" })
"@ | Out-File -FilePath $metadataFile -Encoding UTF8

Write-Log "Metadaten gesichert" "SUCCESS"

# 8. .env Datei sichern (wenn aktiviert)
if ($IncludeEnv) {
    Write-Log "Sichere .env Datei..." "INFO"

    $envFile = Join-Path $repoPath ".env"

    if (Test-Path $envFile) {
        # .env in Backup-Verzeichnis kopieren
        $envBackup = Join-Path $backupDir ".env.backup"
        Copy-Item $envFile $envBackup

        Write-Log ".env gesichert (ACHTUNG: Enthält Secrets!)" "WARN"

        # Warnung in Metadata schreiben
        Add-Content $metadataFile "`n.env File: INCLUDED (CONTAINS SECRETS - KEEP SECURE!)"
    } else {
        Write-Log ".env Datei nicht gefunden, übersprungen" "WARN"
    }
}

# 9. Docker Volumes sichern (wenn aktiviert)
if ($IncludeDockerVolumes) {
    Write-Log "Sichere Docker Volumes..." "INFO"

    $volumesDir = Join-Path $backupDir "docker_volumes"
    New-Item -ItemType Directory -Path $volumesDir -Force | Out-Null

    # PostgreSQL Volume
    $pgVolume = "cdb_postgres_data"
    Write-Log "  Exportiere Volume: $pgVolume" "INFO"

    try {
        # Volume als TAR exportieren
        $volumeBackup = Join-Path $volumesDir "$pgVolume.tar"
        docker run --rm -v ${pgVolume}:/data -v ${volumesDir}:/backup ubuntu tar czf /backup/$pgVolume.tar.gz /data 2>&1 | Out-Null

        if (Test-Path "$volumesDir/$pgVolume.tar.gz") {
            $volumeSize = (Get-Item "$volumesDir/$pgVolume.tar.gz").Length / 1MB
            Write-Log "  Volume ${pgVolume}: $([math]::Round($volumeSize, 2)) MB" "SUCCESS"
        }
    } catch {
        Write-Log "  Volume-Export fehlgeschlagen: $_" "WARN"
    }
}

# 10. Komprimieren zu ZIP
Write-Log "Komprimiere Backup..." "INFO"

try {
    Compress-Archive -Path "$backupDir\*" -DestinationPath $backupArchive -Force

    $finalSize = (Get-Item $backupArchive).Length / 1MB
    Write-Log "Backup komprimiert: $([math]::Round($finalSize, 2)) MB" "SUCCESS"

    # Temporäres Verzeichnis löschen
    Remove-Item $backupDir -Recurse -Force

} catch {
    Write-Log "Komprimierung fehlgeschlagen: $_" "ERROR"
    exit 1
}

# 11. Alte Backups löschen (Retention)
Write-Log "Bereinige alte Backups (älter als $RetentionDays Tage)..." "INFO"

$cutoffDate = (Get-Date).AddDays(-$RetentionDays)
$oldBackups = Get-ChildItem -Path $BackupRoot -Filter "claire_repo_*.zip" |
    Where-Object { $_.LastWriteTime -lt $cutoffDate }

if ($oldBackups.Count -gt 0) {
    foreach ($oldBackup in $oldBackups) {
        Remove-Item $oldBackup.FullName -Force
        Write-Log "Gelöscht: $($oldBackup.Name)" "INFO"
    }
    Write-Log "Gelöscht: $($oldBackups.Count) alte Backups" "SUCCESS"
} else {
    Write-Log "Keine alten Backups zum Löschen gefunden" "INFO"
}

# 12. Backup-Log schreiben
$logFile = Join-Path $BackupRoot "backup_log.txt"
$logEntry = @"
[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Repository Backup erfolgreich
  Datei: $backupArchive
  Größe: $([math]::Round($finalSize, 2)) MB
  Branch: $currentBranch
  Commit: $latestCommit
  .env included: $(if ($IncludeEnv) { "Yes" } else { "No" })
  Volumes included: $(if ($IncludeDockerVolumes) { "Yes" } else { "No" })
  Retention: Gelöscht $($oldBackups.Count) alte Backups

"@

Add-Content -Path $logFile -Value $logEntry

# 13. Zusammenfassung
Write-Log "" "INFO"
Write-Log "=== Backup Complete ===" "SUCCESS"
Write-Log "Datei: $backupArchive" "INFO"
Write-Log "Größe: $([math]::Round($finalSize, 2)) MB" "INFO"
Write-Log "Commit: $latestCommit ($currentBranch)" "INFO"
Write-Log "Aktive Backups: $($(Get-ChildItem -Path $BackupRoot -Filter 'claire_repo_*.zip').Count)" "INFO"

if ($IncludeEnv) {
    Write-Log "" "WARN"
    Write-Log "⚠️  WICHTIG: Backup enthält .env mit Secrets!" "WARN"
    Write-Log "   Sichere Speicherung erforderlich (F:\\ ist OK wenn verschlüsselt)" "WARN"
}

Write-Log "" "INFO"

# Optional: Neueste Backups anzeigen
if ($Verbose) {
    Write-Log "Letzte 5 Backups:" "INFO"
    Get-ChildItem -Path $BackupRoot -Filter "claire_repo_*.zip" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 5 |
        ForEach-Object {
            $size = [math]::Round($_.Length / 1MB, 2)
            $commitHash = if ($_.Name -match "_([a-f0-9]{7})\.zip$") { $matches[1] } else { "unknown" }
            Write-Log "  $($_.Name) - $size MB - Commit: $commitHash" "INFO"
        }
}

exit 0
