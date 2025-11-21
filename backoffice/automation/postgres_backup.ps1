# postgres_backup.ps1 - PostgreSQL Backup Script for Claire de Binaire (Windows)
#
# Purpose: Create daily backups of the claire_de_binaire database
# Retention: 14 days
# Backup Type: Full logical backup (pg_dump)
#
# Usage: .\postgres_backup.ps1
# Task Scheduler: Run daily at 01:00
#
# Requirements:
# - PostgreSQL client tools (pg_dump) in PATH
# - Environment variables set in .env or system

param(
    [string]$BackupDir = "$env:USERPROFILE\backups\cdb_postgres",
    [int]$RetentionDays = 14
)

# ============================================
# CONFIGURATION
# ============================================

# Database Configuration (from environment or defaults)
$DbHost = if ($env:POSTGRES_HOST) { $env:POSTGRES_HOST } else { "localhost" }
$DbPort = if ($env:POSTGRES_PORT) { $env:POSTGRES_PORT } else { "5432" }
$DbName = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "claire_de_binaire" }
$DbUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "claire_user" }
$DbPassword = $env:POSTGRES_PASSWORD

# Backup Configuration
$Timestamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$BackupFile = Join-Path $BackupDir "${DbName}_backup_${Timestamp}.sql"
$LogFile = Join-Path $BackupDir "backup_log.txt"

# ============================================
# FUNCTIONS
# ============================================

function Write-Log {
    param(
        [string]$Level,
        [string]$Message
    )

    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"

    # Write to console with colors
    switch ($Level) {
        "ERROR" { Write-Host $LogMessage -ForegroundColor Red }
        "WARN"  { Write-Host $LogMessage -ForegroundColor Yellow }
        "INFO"  { Write-Host $LogMessage -ForegroundColor Green }
        default { Write-Host $LogMessage }
    }

    # Append to log file
    Add-Content -Path $LogFile -Value $LogMessage
}

function Test-Prerequisites {
    Write-Log "INFO" "Checking prerequisites..."

    # Check if pg_dump is available
    try {
        $null = Get-Command pg_dump -ErrorAction Stop
        Write-Log "INFO" "pg_dump found in PATH"
    }
    catch {
        Write-Log "ERROR" "pg_dump not found. Please install PostgreSQL client tools and add to PATH."
        exit 1
    }

    # Check if backup directory exists, create if not
    if (-not (Test-Path $BackupDir)) {
        Write-Log "INFO" "Creating backup directory: $BackupDir"
        try {
            New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
        }
        catch {
            Write-Log "ERROR" "Failed to create backup directory: $_"
            exit 1
        }
    }

    # Check if password is set
    if (-not $DbPassword) {
        Write-Log "ERROR" "POSTGRES_PASSWORD environment variable not set"
        exit 1
    }

    Write-Log "INFO" "Prerequisites check passed"
}

function Test-DatabaseConnection {
    Write-Log "INFO" "Testing database connection..."

    # Set PGPASSWORD environment variable for pg_dump
    $env:PGPASSWORD = $DbPassword

    try {
        # Test connection with schema-only dump to null
        $result = & pg_dump `
            -h $DbHost `
            -p $DbPort `
            -U $DbUser `
            -d $DbName `
            --schema-only `
            -f $null 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Log "INFO" "Database connection successful"
        }
        else {
            throw "Connection test failed"
        }
    }
    catch {
        Write-Log "ERROR" "Database connection failed: $_"
        Write-Log "ERROR" "Check credentials and database availability"
        exit 1
    }
}

function New-DatabaseBackup {
    Write-Log "INFO" "Starting backup: $BackupFile"

    # Set PGPASSWORD environment variable
    $env:PGPASSWORD = $DbPassword

    try {
        # Create backup with pg_dump
        $result = & pg_dump `
            -h $DbHost `
            -p $DbPort `
            -U $DbUser `
            -d $DbName `
            -F p `
            --verbose `
            -f $BackupFile 2>&1

        if ($LASTEXITCODE -eq 0) {
            $FileSize = (Get-Item $BackupFile).Length / 1MB
            $FileSizeFormatted = "{0:N2} MB" -f $FileSize
            Write-Log "INFO" "Backup created successfully: $BackupFile ($FileSizeFormatted)"

            # Compress backup
            try {
                Write-Log "INFO" "Compressing backup..."
                Compress-Archive -Path $BackupFile -DestinationPath "$BackupFile.zip" -CompressionLevel Optimal -Force
                Remove-Item $BackupFile -Force

                $CompressedSize = (Get-Item "$BackupFile.zip").Length / 1MB
                $CompressedSizeFormatted = "{0:N2} MB" -f $CompressedSize
                Write-Log "INFO" "Backup compressed: $BackupFile.zip ($CompressedSizeFormatted)"

                return "$BackupFile.zip"
            }
            catch {
                Write-Log "WARN" "Compression failed: $_. Keeping uncompressed backup."
                return $BackupFile
            }
        }
        else {
            throw "pg_dump failed with exit code $LASTEXITCODE"
        }
    }
    catch {
        Write-Log "ERROR" "Backup failed: $_"
        exit 1
    }
}

function Remove-OldBackups {
    Write-Log "INFO" "Cleaning up backups older than $RetentionDays days..."

    try {
        $CutoffDate = (Get-Date).AddDays(-$RetentionDays)
        $OldBackups = Get-ChildItem -Path $BackupDir -Filter "${DbName}_backup_*.sql*" |
            Where-Object { $_.LastWriteTime -lt $CutoffDate }

        $DeletedCount = 0
        foreach ($file in $OldBackups) {
            Write-Log "INFO" "Deleting old backup: $($file.Name)"
            Remove-Item $file.FullName -Force
            $DeletedCount++
        }

        Write-Log "INFO" "Cleanup completed. Deleted $DeletedCount old backup(s)"
    }
    catch {
        Write-Log "WARN" "Cleanup failed: $_"
    }
}

function Test-BackupIntegrity {
    param([string]$BackupFilePath)

    Write-Log "INFO" "Verifying backup integrity..."

    try {
        if ($BackupFilePath -like "*.zip") {
            # Extract first few bytes to check
            $archive = [System.IO.Compression.ZipFile]::OpenRead($BackupFilePath)
            $entry = $archive.Entries[0]
            $stream = $entry.Open()
            $reader = New-Object System.IO.StreamReader($stream)
            $firstLine = $reader.ReadLine()
            $reader.Close()
            $stream.Close()
            $archive.Dispose()

            if ($firstLine -like "*PostgreSQL database dump*") {
                Write-Log "INFO" "Backup verification passed"
                return $true
            }
        }
        else {
            # Read first line of SQL file
            $firstLine = Get-Content $BackupFilePath -First 1

            if ($firstLine -like "*PostgreSQL database dump*") {
                Write-Log "INFO" "Backup verification passed"
                return $true
            }
        }

        Write-Log "ERROR" "Backup verification failed - file does not appear to be a valid PostgreSQL dump"
        return $false
    }
    catch {
        Write-Log "WARN" "Backup verification failed: $_"
        return $false
    }
}

function Show-BackupSummary {
    param([string]$FinalBackupFile)

    Write-Log "INFO" "Backup Summary:"
    Write-Log "INFO" "  Database: $DbName"
    Write-Log "INFO" "  Backup File: $FinalBackupFile"
    Write-Log "INFO" "  Timestamp: $Timestamp"

    # Count total backups
    $TotalBackups = (Get-ChildItem -Path $BackupDir -Filter "${DbName}_backup_*.sql*").Count
    Write-Log "INFO" "  Total Backups: $TotalBackups"

    # Calculate total size
    $TotalSize = (Get-ChildItem -Path $BackupDir -Filter "${DbName}_backup_*.sql*" |
        Measure-Object -Property Length -Sum).Sum / 1MB
    $TotalSizeFormatted = "{0:N2} MB" -f $TotalSize
    Write-Log "INFO" "  Total Backup Size: $TotalSizeFormatted"
}

# ============================================
# MAIN EXECUTION
# ============================================

function Main {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "PostgreSQL Backup Script" -ForegroundColor Green
    Write-Host "Claire de Binaire - Database Backup" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""

    Write-Log "INFO" "Backup process started"

    # Check prerequisites
    Test-Prerequisites

    # Test database connection
    Test-DatabaseConnection

    # Create backup
    $FinalBackupFile = New-DatabaseBackup

    # Verify backup
    $VerificationResult = Test-BackupIntegrity -BackupFilePath $FinalBackupFile

    if (-not $VerificationResult) {
        Write-Log "ERROR" "Backup verification failed. Backup may be corrupted."
        exit 1
    }

    # Cleanup old backups
    Remove-OldBackups

    # Show summary
    Show-BackupSummary -FinalBackupFile $FinalBackupFile

    Write-Log "INFO" "Backup process completed successfully"
    Write-Host ""
    Write-Host "✅ Backup completed successfully!" -ForegroundColor Green
    Write-Host "Backup file: $FinalBackupFile" -ForegroundColor Green
    Write-Host ""
}

# Run main function
try {
    Main
}
catch {
    Write-Log "ERROR" "Unexpected error: $_"
    exit 1
}
finally {
    # Clear password from environment
    $env:PGPASSWORD = $null
}
