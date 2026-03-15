# restore_all.ps1 - Consolidated Restore (Postgres + Redis)
# Source: F:\Claire_Backups
# Restores from backup_all.ps1 archives
#
# Usage:
#   powershell.exe -ExecutionPolicy Bypass -File restore_all.ps1 -BackupName cdb_backup_20260315_120000
#   powershell.exe -ExecutionPolicy Bypass -File restore_all.ps1 -BackupName cdb_backup_20260315_120000 -Force
#   powershell.exe -ExecutionPolicy Bypass -File restore_all.ps1 -ListAvailable

[CmdletBinding()]
param(
    [string]$BackupName = "",
    [string]$BackupDir = "F:\Claire_Backups",
    [switch]$Force,
    [switch]$ListAvailable
)

$ErrorActionPreference = "Stop"

function Write-Pass { param([string]$Msg) Write-Host "PASS  $Msg" -ForegroundColor Green }
function Write-Fail { param([string]$Msg) Write-Host "FAIL  $Msg" -ForegroundColor Red }
function Write-Step { param([string]$Msg) Write-Host "---   $Msg" -ForegroundColor Cyan }

Write-Host ""
Write-Host "=== Claire de Binare - Consolidated Restore ===" -ForegroundColor Cyan
Write-Host ""

# ── List available backups ───────────────────────────────────────────────

if ($ListAvailable -or $BackupName -eq "") {
    Write-Step "Available backups in $BackupDir :"

    if (-not (Test-Path $BackupDir)) {
        Write-Fail "Backup directory not found: $BackupDir"
        exit 1
    }

    $archives = Get-ChildItem "$BackupDir\cdb_backup_*.zip" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending

    if ($archives.Count -eq 0) {
        Write-Host "      No backup archives found" -ForegroundColor Yellow
        exit 1
    }

    foreach ($a in $archives) {
        $sizeMB = [math]::Round($a.Length / 1MB, 2)
        $age = [math]::Round(((Get-Date) - $a.LastWriteTime).TotalHours, 1)
        Write-Host "      $($a.BaseName)  ($sizeMB MB, ${age}h ago)" -ForegroundColor White
    }

    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\restore_all.ps1 -BackupName <name>" -ForegroundColor White
    Write-Host ""

    if ($BackupName -eq "") { exit 0 }
}

# ── Pre-flight ───────────────────────────────────────────────────────────

$archivePath = Join-Path $BackupDir "$BackupName.zip"

if (-not (Test-Path $archivePath)) {
    Write-Fail "Archive not found: $archivePath"
    Write-Host ""
    Write-Host "Run with -ListAvailable to see available backups" -ForegroundColor Yellow
    exit 1
}

$archiveSizeMB = [math]::Round((Get-Item $archivePath).Length / 1MB, 2)
Write-Host "Archive:  $archivePath ($archiveSizeMB MB)"
Write-Host ""

# ── Extract ──────────────────────────────────────────────────────────────

Write-Step "Extracting archive..."

$extractDir = Join-Path $BackupDir "${BackupName}_restore_temp"
if (Test-Path $extractDir) {
    Remove-Item -Path $extractDir -Recurse -Force
}

Expand-Archive -Path $archivePath -DestinationPath $extractDir

# Find manifest (may be nested in subdirectory from Compress-Archive)
$manifestFile = Get-ChildItem -Path $extractDir -Filter "manifest.json" -Recurse | Select-Object -First 1

if (-not $manifestFile) {
    Write-Fail "No manifest.json found in archive - is this a backup_all.ps1 archive?"
    Remove-Item -Path $extractDir -Recurse -Force
    exit 1
}

$manifest = Get-Content $manifestFile.FullName | ConvertFrom-Json
$backupRoot = $manifestFile.DirectoryName

Write-Pass "Manifest loaded"
Write-Host "      Backup from:  $($manifest.Timestamp)"
Write-Host "      Git commit:   $($manifest.GitCommit)"
Write-Host "      Postgres:     $(if ($manifest.Components.Postgres) { 'included' } else { 'not included' })"
Write-Host "      Redis:        $(if ($manifest.Components.Redis) { 'included' } else { 'not included' })"
Write-Host ""

# ── Safety confirmation ──────────────────────────────────────────────────

if (-not $Force) {
    Write-Host "WARNING: This will REPLACE current Postgres and Redis data!" -ForegroundColor Red
    Write-Host ""
    $confirmation = Read-Host "Type 'yes' to proceed (anything else cancels)"
    if ($confirmation -ne 'yes') {
        Write-Host "Restore cancelled" -ForegroundColor Yellow
        Remove-Item -Path $extractDir -Recurse -Force
        exit 0
    }
    Write-Host ""
}

$startTime = Get-Date
$restoreResults = @{
    Postgres = $false
    Redis = $false
}

# ── Restore Postgres ─────────────────────────────────────────────────────

if ($manifest.Components.Postgres) {
    Write-Step "[1/2] Restoring Postgres..."

    $pgDump = Get-ChildItem -Path $backupRoot -Filter "postgres_dump.sql" -Recurse | Select-Object -First 1

    if (-not $pgDump) {
        Write-Fail "postgres_dump.sql not found in archive"
    } else {
        # Check container is running
        $pgRunning = docker ps --filter "name=cdb_postgres" --format "{{.Names}}" 2>&1
        if ($pgRunning -notmatch "cdb_postgres") {
            Write-Fail "Container cdb_postgres not running - start the stack first"
        } else {
            try {
                # Drop and recreate database
                docker exec cdb_postgres psql -U claire_user -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'claire_de_binare' AND pid <> pg_backend_pid();" 2>&1 | Out-Null
                docker exec cdb_postgres psql -U claire_user -d postgres -c "DROP DATABASE IF EXISTS claire_de_binare;" 2>&1 | Out-Null
                docker exec cdb_postgres psql -U claire_user -d postgres -c "CREATE DATABASE claire_de_binare;" 2>&1 | Out-Null

                if ($LASTEXITCODE -ne 0) {
                    Write-Fail "Database drop/create failed"
                } else {
                    # Restore dump via stdin pipe
                    Get-Content $pgDump.FullName | docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare 2>&1 | Out-Null

                    # Verify: check that tables exist
                    $tableCheck = docker exec cdb_postgres psql -U claire_user -d claire_de_binare -t -c "\dt" 2>&1
                    if ($tableCheck -match "public") {
                        $restoreResults.Postgres = $true
                        Write-Pass "Postgres restored and verified (tables present)"
                    } else {
                        Write-Fail "Postgres restore completed but no tables found"
                    }
                }
            } catch {
                Write-Fail "Postgres restore failed: $_"
            }
        }
    }
} else {
    Write-Host "      Postgres not included in this backup - skipping" -ForegroundColor Gray
}

# ── Restore Redis ────────────────────────────────────────────────────────

if ($manifest.Components.Redis) {
    Write-Step "[2/2] Restoring Redis..."

    $redisDump = Get-ChildItem -Path $backupRoot -Filter "redis_dump.rdb" -Recurse | Select-Object -First 1

    if (-not $redisDump) {
        Write-Fail "redis_dump.rdb not found in archive"
    } else {
        $redisRunning = docker ps --filter "name=cdb_redis" --format "{{.Names}}" 2>&1
        if ($redisRunning -notmatch "cdb_redis") {
            Write-Fail "Container cdb_redis not running - start the stack first"
        } else {
            try {
                # Stop Redis to replace RDB safely
                docker stop cdb_redis 2>&1 | Out-Null

                # Copy RDB into container volume via alpine helper
                # The volume name follows Docker Compose convention
                docker run --rm `
                    -v claire_de_binare_redis_data:/data `
                    -v "$($redisDump.DirectoryName):/backup:ro" `
                    alpine sh -c "cp /backup/redis_dump.rdb /data/dump.rdb && chmod 644 /data/dump.rdb"

                if ($LASTEXITCODE -ne 0) {
                    Write-Fail "Redis RDB copy into volume failed"
                } else {
                    # Restart Redis
                    docker start cdb_redis 2>&1 | Out-Null
                    Start-Sleep -Seconds 3

                    # Verify Redis is up
                    $redisPing = docker exec cdb_redis redis-cli PING 2>&1
                    if ($redisPing -match "PONG") {
                        $restoreResults.Redis = $true
                        Write-Pass "Redis restored and responding"
                    } else {
                        Write-Fail "Redis not responding after restore"
                    }
                }
            } catch {
                Write-Fail "Redis restore failed: $_"
                # Try to restart Redis even on failure
                docker start cdb_redis 2>&1 | Out-Null
            }
        }
    }
} else {
    Write-Host "      Redis not included in this backup - skipping" -ForegroundColor Gray
}

# ── Cleanup temp ─────────────────────────────────────────────────────────

Write-Step "Cleaning up temp files..."
Remove-Item -Path $extractDir -Recurse -Force -ErrorAction SilentlyContinue

# ── Summary ──────────────────────────────────────────────────────────────

$duration = [math]::Round(((Get-Date) - $startTime).TotalSeconds, 1)

Write-Host ""
Write-Host "=== Restore Summary ===" -ForegroundColor Cyan
Write-Host "  Postgres: $(if ($restoreResults.Postgres) { 'OK' } else { 'FAILED / skipped' })"
Write-Host "  Redis:    $(if ($restoreResults.Redis) { 'OK' } else { 'FAILED / skipped' })"
Write-Host "  Duration: $duration s"
Write-Host ""
Write-Host "Verify manually:" -ForegroundColor Yellow
Write-Host "  docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c '\dt'" -ForegroundColor White
Write-Host "  docker exec cdb_redis redis-cli DBSIZE" -ForegroundColor White
Write-Host ""

# Exit code: fail only if Postgres restore was expected and failed
if ($manifest.Components.Postgres -and -not $restoreResults.Postgres) {
    Write-Fail "Restore incomplete - Postgres failed"
    exit 1
}

Write-Pass "Restore completed"
exit 0
