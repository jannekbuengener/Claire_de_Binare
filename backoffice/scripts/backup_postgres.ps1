# PostgreSQL Backup Script - Claire de Binare
# Stündliche Backups für 14-Tage Paper Trading Test
#
# Funktionalität:
# - Erstellt pg_dump Backup via Docker
# - Komprimiert mit ZIP
# - Retention: 14 Tage (336 stündliche Backups)
# - Disk-Space Check
#
# Verwendung:
#   powershell.exe -ExecutionPolicy Bypass -File backup_postgres.ps1
#
# Task Scheduler Setup:
#   schtasks /create /tn "Claire_Hourly_Backup" `
#     /tr "powershell.exe -ExecutionPolicy Bypass -File C:\...\backup_postgres.ps1" `
#     /sc hourly /st 00:00

# Configuration
$BACKUP_DIR = "F:\Claire_Backups"
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$BACKUP_FILE = "$BACKUP_DIR\claire_de_binare_$TIMESTAMP.sql"
$MIN_FREE_GB = 30

# Colors for output
function Write-Success { Write-Host "✅ $args" -ForegroundColor Green }
function Write-Error-Custom { Write-Host "❌ $args" -ForegroundColor Red }
function Write-Info { Write-Host "ℹ️  $args" -ForegroundColor Cyan }

Write-Info "==========================================

"
Write-Info "PostgreSQL Backup - Claire de Binare"
Write-Info "Timestamp: $TIMESTAMP"
Write-Info "=========================================="

# 1. Ensure backup directory exists
Write-Info "Creating backup directory..."
try {
    New-Item -ItemType Directory -Force -Path $BACKUP_DIR | Out-Null
    Write-Success "Backup directory ready: $BACKUP_DIR"
} catch {
    Write-Error-Custom "Failed to create backup directory: $_"
    exit 1
}

# 2. Check disk space
Write-Info "Checking disk space..."
try {
    $drive = (Get-Item $BACKUP_DIR).PSDrive
    $freeGB = [math]::Round(($drive.Free / 1GB), 2)
    $totalGB = [math]::Round((($drive.Used + $drive.Free) / 1GB), 2)

    Write-Info "  Total: $totalGB GB"
    Write-Info "  Free:  $freeGB GB"

    if ($freeGB -lt $MIN_FREE_GB) {
        Write-Error-Custom "Insufficient disk space! ($freeGB GB < $MIN_FREE_GB GB)"
        Write-Info "Consider cleaning old backups or increasing disk space."
        exit 1
    }
    Write-Success "Sufficient disk space ($freeGB GB available)"
} catch {
    Write-Error-Custom "Disk space check failed: $_"
    exit 1
}

# 3. Check if Docker is running
Write-Info "Checking Docker..."
try {
    $dockerStatus = docker ps --format "{{.Names}}" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Docker is not running or not accessible"
        exit 1
    }

    if ($dockerStatus -notcontains "cdb_postgres") {
        Write-Error-Custom "PostgreSQL container 'cdb_postgres' not running"
        Write-Info "Start with: docker compose up -d cdb_postgres"
        exit 1
    }
    Write-Success "Docker OK - cdb_postgres running"
} catch {
    Write-Error-Custom "Docker check failed: $_"
    exit 1
}

# 4. Create backup
Write-Info "Creating PostgreSQL backup..."
Write-Info "  Output: $BACKUP_FILE"

try {
    # Run pg_dump via docker exec
    docker exec cdb_postgres pg_dump `
        -U claire_user `
        -d claire_de_binare `
        --no-owner `
        --no-acl `
        | Out-File -FilePath $BACKUP_FILE -Encoding UTF8

    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "pg_dump failed with exit code $LASTEXITCODE"
        exit 1
    }

    # Check if file was created and has content
    if (-Not (Test-Path $BACKUP_FILE)) {
        Write-Error-Custom "Backup file not created"
        exit 1
    }

    $backupSize = (Get-Item $BACKUP_FILE).Length / 1MB
    Write-Success "Backup created: $([math]::Round($backupSize, 2)) MB"

} catch {
    Write-Error-Custom "Backup creation failed: $_"
    exit 1
}

# 5. Compress backup
Write-Info "Compressing backup..."
try {
    Compress-Archive -Path $BACKUP_FILE -DestinationPath "$BACKUP_FILE.zip" -Force

    if (Test-Path "$BACKUP_FILE.zip") {
        $zipSize = (Get-Item "$BACKUP_FILE.zip").Length / 1MB
        Write-Success "Compressed: $([math]::Round($zipSize, 2)) MB"

        # Remove uncompressed SQL file
        Remove-Item $BACKUP_FILE -Force
    } else {
        Write-Error-Custom "Compression failed"
        exit 1
    }
} catch {
    Write-Error-Custom "Compression failed: $_"
    exit 1
}

# 6. Cleanup old backups (retention: 14 days)
Write-Info "Cleaning old backups (retention: 14 days)..."
try {
    $oldBackups = Get-ChildItem "$BACKUP_DIR\*.zip" |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) }

    if ($oldBackups.Count -gt 0) {
        $oldBackups | ForEach-Object {
            Write-Info "  Removing: $($_.Name)"
            Remove-Item $_.FullName -Force
        }
        Write-Success "Removed $($oldBackups.Count) old backup(s)"
    } else {
        Write-Info "No old backups to remove"
    }
} catch {
    Write-Error-Custom "Cleanup failed: $_"
    # Non-fatal, continue
}

# 7. Summary
Write-Info "=========================================="
Write-Success "Backup completed successfully!"
Write-Info "  File: $BACKUP_FILE.zip"
Write-Info "  Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

# Count total backups
$totalBackups = (Get-ChildItem "$BACKUP_DIR\*.zip").Count
$totalSize = [math]::Round(((Get-ChildItem "$BACKUP_DIR\*.zip" | Measure-Object -Property Length -Sum).Sum / 1GB), 2)
Write-Info "  Total backups: $totalBackups"
Write-Info "  Total size: $totalSize GB"
Write-Info "=========================================="

exit 0
