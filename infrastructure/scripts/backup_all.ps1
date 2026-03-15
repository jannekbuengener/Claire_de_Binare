# backup_all.ps1 - Consolidated Backup (Postgres + Redis)
# Target: F:\Claire_Backups
# Creates pg_dump + Redis RDB snapshot, manifest, ZIP archive, 14d retention
#
# Usage:
#   powershell.exe -ExecutionPolicy Bypass -File backup_all.ps1
#   powershell.exe -ExecutionPolicy Bypass -File backup_all.ps1 -BackupDir "D:\Other\Path"
#   powershell.exe -ExecutionPolicy Bypass -File backup_all.ps1 -AllowRedisFailure
#
# Exit codes:
#   0 = both Postgres and Redis backed up successfully
#   1 = any component failed (default: both are required)
#       Use -AllowRedisFailure to tolerate Redis failure (exit 0 if Postgres OK)

[CmdletBinding()]
param(
    [string]$BackupDir = "F:\Claire_Backups",
    [int]$RetentionDays = 14,
    [int]$MinFreeGB = 10,
    [switch]$AllowRedisFailure
)

$ErrorActionPreference = "Stop"

$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$BACKUP_NAME = "cdb_backup_$TIMESTAMP"
$WORK_DIR = Join-Path $BackupDir $BACKUP_NAME

function Write-Pass  { param([string]$Msg) Write-Host "PASS  $Msg" -ForegroundColor Green }
function Write-Fail  { param([string]$Msg) Write-Host "FAIL  $Msg" -ForegroundColor Red }
function Write-Step  { param([string]$Msg) Write-Host "---   $Msg" -ForegroundColor Cyan }

Write-Host ""
Write-Host "=== Claire de Binare - Consolidated Backup ===" -ForegroundColor Cyan
Write-Host "Timestamp:  $TIMESTAMP"
Write-Host "Target:     $BackupDir"
Write-Host ""

# ── 1. Pre-flight checks ────────────────────────────────────────────────

Write-Step "Pre-flight: backup directory"
try {
    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
} catch {
    Write-Fail "Cannot create backup directory: $BackupDir"
    exit 1
}

Write-Step "Pre-flight: disk space"
try {
    $drive = (Get-Item $BackupDir).PSDrive
    $freeGB = [math]::Round(($drive.Free / 1GB), 2)
    if ($freeGB -lt $MinFreeGB) {
        Write-Fail "Insufficient disk space: $freeGB GB free (minimum $MinFreeGB GB)"
        exit 1
    }
    Write-Pass "Disk space OK ($freeGB GB free)"
} catch {
    Write-Fail "Disk space check failed: $_"
    exit 1
}

Write-Step "Pre-flight: Docker"
try {
    $dockerCheck = docker ps --format "{{.Names}}" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Docker is not running"
        exit 1
    }
    Write-Pass "Docker reachable"
} catch {
    Write-Fail "Docker check failed: $_"
    exit 1
}

# Create working directory
New-Item -ItemType Directory -Force -Path $WORK_DIR | Out-Null

$componentStatus = @{
    Postgres = $false
    Redis = $false
}

$startTime = Get-Date

# ── 2. Postgres backup ──────────────────────────────────────────────────

Write-Host ""
Write-Step "[1/2] Postgres backup via pg_dump..."

$pgRunning = docker ps --filter "name=cdb_postgres" --format "{{.Names}}" 2>&1
if ($pgRunning -notmatch "cdb_postgres") {
    Write-Fail "Container cdb_postgres not running - skipping Postgres backup"
} else {
    $pgFile = Join-Path $WORK_DIR "postgres_dump.sql"
    try {
        docker exec cdb_postgres pg_dump -U claire_user -d claire_de_binare --no-owner --no-acl | Out-File -FilePath $pgFile -Encoding UTF8

        if ($LASTEXITCODE -ne 0) {
            Write-Fail "pg_dump returned exit code $LASTEXITCODE"
        } elseif (-not (Test-Path $pgFile) -or (Get-Item $pgFile).Length -eq 0) {
            Write-Fail "pg_dump produced empty file"
        } else {
            $pgSizeMB = [math]::Round((Get-Item $pgFile).Length / 1MB, 2)

            # Basic integrity check: dump must contain CREATE TABLE
            $headContent = Get-Content $pgFile -TotalCount 200 -ErrorAction SilentlyContinue | Out-String
            if ($headContent -match "PostgreSQL database dump") {
                $componentStatus.Postgres = $true
                Write-Pass "Postgres backup: $pgSizeMB MB"
            } else {
                Write-Fail "Postgres dump missing expected header"
            }
        }
    } catch {
        Write-Fail "Postgres backup failed: $_"
    }
}

# ── 3. Redis backup ─────────────────────────────────────────────────────

Write-Step "[2/2] Redis backup via SAVE + cp..."

$redisRunning = docker ps --filter "name=cdb_redis" --format "{{.Names}}" 2>&1
if ($redisRunning -notmatch "cdb_redis") {
    Write-Fail "Container cdb_redis not running - skipping Redis backup"
} else {
    $redisFile = Join-Path $WORK_DIR "redis_dump.rdb"
    try {
        # Trigger synchronous save
        docker exec cdb_redis redis-cli SAVE 2>&1 | Out-Null

        if ($LASTEXITCODE -ne 0) {
            Write-Fail "redis-cli SAVE failed"
        } else {
            # Copy RDB from container
            docker cp cdb_redis:/data/dump.rdb $redisFile 2>&1

            if ($LASTEXITCODE -ne 0 -or -not (Test-Path $redisFile)) {
                Write-Fail "Redis RDB copy failed"
            } else {
                $redisSizeKB = [math]::Round((Get-Item $redisFile).Length / 1KB, 2)
                $componentStatus.Redis = $true
                Write-Pass "Redis backup: $redisSizeKB KB"
            }
        }
    } catch {
        Write-Fail "Redis backup failed: $_"
    }
}

# ── 4. Manifest ──────────────────────────────────────────────────────────

Write-Step "Writing manifest..."

$gitCommit = "unknown"
try {
    $gitCommit = (git rev-parse HEAD 2>&1).Trim()
    if ($LASTEXITCODE -ne 0) { $gitCommit = "unavailable" }
} catch {
    $gitCommit = "unavailable"
}

$manifest = @{
    Timestamp = (Get-Date -Format 'o')
    BackupName = $BACKUP_NAME
    Components = $componentStatus
    GitCommit = $gitCommit
    RetentionDays = $RetentionDays
    BackupDir = $BackupDir
} | ConvertTo-Json -Depth 10

$manifestPath = Join-Path $WORK_DIR "manifest.json"
$manifest | Out-File -FilePath $manifestPath -Encoding UTF8
Write-Pass "Manifest written"

# ── 5. Compress ──────────────────────────────────────────────────────────

Write-Step "Compressing archive..."

$archivePath = Join-Path $BackupDir "$BACKUP_NAME.zip"
try {
    Compress-Archive -Path $WORK_DIR -DestinationPath $archivePath -Force

    if (Test-Path $archivePath) {
        $archiveSizeMB = [math]::Round((Get-Item $archivePath).Length / 1MB, 2)
        Write-Pass "Archive: $archiveSizeMB MB -> $archivePath"
        # Remove uncompressed working directory
        Remove-Item -Path $WORK_DIR -Recurse -Force
    } else {
        Write-Fail "Archive creation failed"
        exit 1
    }
} catch {
    Write-Fail "Compression failed: $_"
    exit 1
}

# ── 6. Retention cleanup ────────────────────────────────────────────────

Write-Step "Retention cleanup ($RetentionDays days)..."

try {
    $cutoff = (Get-Date).AddDays(-$RetentionDays)
    $oldArchives = Get-ChildItem "$BackupDir\cdb_backup_*.zip" -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $cutoff }

    if ($oldArchives.Count -gt 0) {
        $oldArchives | ForEach-Object {
            Write-Host "      Removing: $($_.Name)" -ForegroundColor Gray
            Remove-Item $_.FullName -Force
        }
        Write-Pass "Removed $($oldArchives.Count) old archive(s)"
    } else {
        Write-Host "      No archives older than $RetentionDays days" -ForegroundColor Gray
    }
} catch {
    Write-Host "WARN  Retention cleanup failed: $_ (non-fatal)" -ForegroundColor Yellow
}

# ── 7. Summary ───────────────────────────────────────────────────────────

$duration = [math]::Round(((Get-Date) - $startTime).TotalSeconds, 1)
$totalArchives = (Get-ChildItem "$BackupDir\cdb_backup_*.zip" -ErrorAction SilentlyContinue).Count

Write-Host ""
Write-Host "=== Backup Summary ===" -ForegroundColor Cyan
Write-Host "  Postgres: $(if ($componentStatus.Postgres) { 'OK' } else { 'FAILED' })"
Write-Host "  Redis:    $(if ($componentStatus.Redis) { 'OK' } else { 'FAILED' })"
Write-Host "  Archive:  $archivePath"
Write-Host "  Duration: $duration s"
Write-Host "  Total archives in $BackupDir : $totalArchives"
Write-Host ""

# Exit with failure if any component failed
if (-not $componentStatus.Postgres) {
    Write-Fail "Backup incomplete - Postgres failed"
    exit 1
}

if (-not $componentStatus.Redis) {
    if ($AllowRedisFailure) {
        Write-Host "WARN  Redis backup failed - tolerated via -AllowRedisFailure" -ForegroundColor Yellow
    } else {
        Write-Fail "Backup incomplete - Redis failed (use -AllowRedisFailure to override)"
        exit 1
    }
}

Write-Pass "Backup completed successfully"
Write-Host ""
Write-Host "Restore with:" -ForegroundColor Yellow
Write-Host "  powershell.exe -ExecutionPolicy Bypass -File infrastructure\scripts\restore_all.ps1 -BackupName $BACKUP_NAME" -ForegroundColor White
Write-Host ""

exit 0
