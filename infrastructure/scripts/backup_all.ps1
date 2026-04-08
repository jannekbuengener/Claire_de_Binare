# backup_all.ps1 - Consolidated Backup (Postgres + Redis + optional SurrealDB)
# Target: F:\Claire_Backups
# Creates pg_dump + Redis RDB snapshot, optional SurrealDB file-volume copy,
# manifest, ZIP archive, 14d retention
#
# Usage:
#   powershell.exe -ExecutionPolicy Bypass -File backup_all.ps1
#   powershell.exe -ExecutionPolicy Bypass -File backup_all.ps1 -BackupDir "D:\Other\Path"
#   powershell.exe -ExecutionPolicy Bypass -File backup_all.ps1 -AllowRedisFailure
#   powershell.exe -ExecutionPolicy Bypass -File backup_all.ps1 -IncludeSurrealDB
#   powershell.exe -ExecutionPolicy Bypass -File backup_all.ps1 -IncludeSurrealDB -AllowSurrealDBFailure
#
# Exit codes:
#   0 = required components backed up successfully
#   1 = any required component failed
#       Use -AllowRedisFailure to tolerate Redis failure (exit 0 if Postgres OK)
#       Use -IncludeSurrealDB to capture the SurrealDB sidecar volume
#       Use -AllowSurrealDBFailure to tolerate optional SurrealDB capture failure

[CmdletBinding()]
param(
    [string]$BackupDir = "F:\Claire_Backups",
    [int]$RetentionDays = 14,
    [int]$MinFreeGB = 10,
    [switch]$AllowRedisFailure,
    [switch]$IncludeSurrealDB,
    [switch]$AllowSurrealDBFailure,
    [string]$SurrealDbVolumeName = "cdb_database_surrealdb_data",
    [string]$SurrealNamespace = "governance",
    [string]$SurrealDatabase = "governance_mirror"
)

$ErrorActionPreference = "Stop"

$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$BACKUP_NAME = "cdb_backup_$TIMESTAMP"
$WORK_DIR = Join-Path $BackupDir $BACKUP_NAME

function Write-Pass  { param([string]$Msg) Write-Host "PASS  $Msg" -ForegroundColor Green }
function Write-Fail  { param([string]$Msg) Write-Host "FAIL  $Msg" -ForegroundColor Red }
function Write-Step  { param([string]$Msg) Write-Host "---   $Msg" -ForegroundColor Cyan }

function Get-DirectoryMetrics {
    param([string]$Path)

    $files = @()
    if (Test-Path $Path) {
        $files = @(Get-ChildItem -Path $Path -File -Recurse -Force -ErrorAction SilentlyContinue)
    }

    $totalBytes = 0
    if ($files.Count -gt 0) {
        $totalBytes = ($files | Measure-Object -Property Length -Sum).Sum
    }

    return @{
        FileCount = $files.Count
        TotalBytes = [int64]$totalBytes
    }
}

$script:SurrealDbAuthHeader = $null

function Get-SurrealDbAuthHeader {
    if ($script:SurrealDbAuthHeader) {
        return $script:SurrealDbAuthHeader
    }

    try {
        $user = (docker exec cdb_surrealdb printenv SURREAL_USER 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($user)) {
            return $null
        }

        $pass = (docker exec cdb_surrealdb printenv SURREAL_PASS 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($pass)) {
            return $null
        }

        $tokenBytes = [System.Text.Encoding]::UTF8.GetBytes("${user}:${pass}")
        $script:SurrealDbAuthHeader = "Basic " + [Convert]::ToBase64String($tokenBytes)
        return $script:SurrealDbAuthHeader
    } catch {
        return $null
    }
}

function Invoke-SurrealDbSql {
    param(
        [string]$Namespace,
        [string]$Database,
        [string]$Query
    )

    $authHeader = Get-SurrealDbAuthHeader
    if (-not $authHeader) {
        return $null
    }

    try {
        $curlCommand = "curl -fsS -H `"Authorization: $authHeader`" -H `"NS: $Namespace`" -H `"DB: $Database`" -H `"Accept: application/json`" --data-binary @- http://localhost:8000/sql"
        $rawResponse = $Query | docker exec -i cdb_surrealdb sh -lc $curlCommand 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($rawResponse)) {
            return $null
        }

        return ($rawResponse | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Get-SurrealDbTableNames {
    param(
        [string]$Namespace,
        [string]$Database
    )

    $knownTables = @(
        "governance_events",
        "audit_trail",
        "deployment_approvals_mirror",
        "system_config",
        "security_policy_refs",
        "access_matrix",
        "ledger_event"
    )

    $info = Invoke-SurrealDbSql -Namespace $Namespace -Database $Database -Query "INFO FOR DB;"
    if (-not $info) {
        return @()
    }

    $responseItems = @($info)
    if ($responseItems.Count -eq 0) {
        return @()
    }

    $tableNames = @()
    $result = $responseItems[0].result
    if ($result -and $result.PSObject.Properties.Name -contains "tb" -and $result.tb) {
        $tableNames = @($result.tb.PSObject.Properties.Name)
    }

    if ($tableNames.Count -eq 0) {
        $serialized = $info | ConvertTo-Json -Depth 10
        foreach ($tableName in $knownTables) {
            if ($serialized -match [regex]::Escape($tableName)) {
                $tableNames += $tableName
            }
        }
    }

    return @($tableNames | Sort-Object -Unique)
}

function Get-SurrealDbRecordCounts {
    param(
        [string[]]$Tables,
        [string]$Namespace,
        [string]$Database
    )

    $counts = @{}
    foreach ($tableName in $Tables) {
        $countResponse = Invoke-SurrealDbSql -Namespace $Namespace -Database $Database -Query "SELECT count() AS record_count FROM $tableName GROUP ALL;"
        if (-not $countResponse) {
            continue
        }

        try {
            $rows = @(@($countResponse)[0].result)
            if ($rows.Count -eq 0) {
                continue
            }

            if ($rows[0].PSObject.Properties.Name -contains "record_count") {
                $counts[$tableName] = [int64]$rows[0].record_count
            } elseif ($rows[0].PSObject.Properties.Name -contains "count") {
                $counts[$tableName] = [int64]$rows[0].count
            }
        } catch {
            continue
        }
    }

    return $counts
}

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

# Resolve Redis password from Docker secret (same source as compose stack)
$redisPassword = ""
try {
    $redisPassword = (docker exec cdb_redis sh -c 'cat /run/secrets/redis_password 2>/dev/null' 2>&1).Trim()
    if ($LASTEXITCODE -ne 0 -or $redisPassword -eq "") {
        $redisPassword = ""
        Write-Host "      Redis password not found in container secrets - will try without auth" -ForegroundColor Gray
    }
} catch {
    $redisPassword = ""
}

# Create working directory
New-Item -ItemType Directory -Force -Path $WORK_DIR | Out-Null

$componentStatus = @{
    Postgres = $false
    Redis = $false
    SurrealDB = $false
}

$componentSelection = @{
    Postgres = $true
    Redis = $true
    SurrealDB = [bool]$IncludeSurrealDB
}

$componentEvidence = @{
    Postgres = @{}
    Redis = @{}
    SurrealDB = @{
        Requested = [bool]$IncludeSurrealDB
        ContainerName = "cdb_surrealdb"
        VolumeName = $SurrealDbVolumeName
        Storage = "file:/data/surrealdb"
        Namespace = $SurrealNamespace
        Database = $SurrealDatabase
        Artifact = "surrealdb_data"
        QueryStatus = $(if ($IncludeSurrealDB) { "not_collected" } else { "not_requested" })
        Tables = @()
        RecordCounts = @{}
        FileCount = 0
        TotalBytes = 0
    }
}

$startTime = Get-Date

# ── 2. Postgres backup ──────────────────────────────────────────────────

Write-Host ""
Write-Step "Postgres backup via pg_dump..."

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
                $componentEvidence.Postgres = @{
                    Artifact = "postgres_dump.sql"
                    SizeBytes = [int64](Get-Item $pgFile).Length
                }
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

Write-Step "Redis backup via SAVE + cp..."

$redisRunning = docker ps --filter "name=cdb_redis" --format "{{.Names}}" 2>&1
if ($redisRunning -notmatch "cdb_redis") {
    Write-Fail "Container cdb_redis not running - skipping Redis backup"
} else {
    $redisFile = Join-Path $WORK_DIR "redis_dump.rdb"
    try {
        # Trigger synchronous save (with auth if available)
        if ($redisPassword -ne "") {
            docker exec cdb_redis redis-cli -a $redisPassword --no-auth-warning SAVE 2>&1 | Out-Null
        } else {
            docker exec cdb_redis redis-cli SAVE 2>&1 | Out-Null
        }

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
                $componentEvidence.Redis = @{
                    Artifact = "redis_dump.rdb"
                    SizeBytes = [int64](Get-Item $redisFile).Length
                }
                Write-Pass "Redis backup: $redisSizeKB KB"
            }
        }
    } catch {
        Write-Fail "Redis backup failed: $_"
    }
}

# ── 4. Optional SurrealDB backup ───────────────────────────────────────────

if ($IncludeSurrealDB) {
    Write-Step "SurrealDB sidecar backup via volume copy..."

    $surrealBackupPath = Join-Path $WORK_DIR "surrealdb_data"
    try {
        $null = docker volume inspect $SurrealDbVolumeName 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Fail "SurrealDB volume not found: $SurrealDbVolumeName"
        } else {
            New-Item -ItemType Directory -Force -Path $surrealBackupPath | Out-Null
            docker run --rm `
                -v "${SurrealDbVolumeName}:/source:ro" `
                -v "${surrealBackupPath}:/backup" `
                alpine sh -c "cd /source && cp -a . /backup/" 2>&1 | Out-Null

            if ($LASTEXITCODE -ne 0) {
                Write-Fail "SurrealDB volume copy failed"
            } else {
                $metrics = Get-DirectoryMetrics -Path $surrealBackupPath
                if ($metrics.FileCount -eq 0 -and $metrics.TotalBytes -eq 0) {
                    Write-Fail "SurrealDB backup produced an empty directory"
                } else {
                    $componentStatus.SurrealDB = $true
                    $componentEvidence.SurrealDB.FileCount = [int64]$metrics.FileCount
                    $componentEvidence.SurrealDB.TotalBytes = [int64]$metrics.TotalBytes

                    $surrealRunning = docker ps --filter "name=cdb_surrealdb" --format "{{.Names}}" 2>&1
                    if ($surrealRunning -match "cdb_surrealdb") {
                        $tableNames = Get-SurrealDbTableNames -Namespace $SurrealNamespace -Database $SurrealDatabase
                        if ($tableNames.Count -gt 0) {
                            $componentEvidence.SurrealDB.QueryStatus = "count_check_collected"
                            $componentEvidence.SurrealDB.Tables = @($tableNames)
                            $componentEvidence.SurrealDB.RecordCounts = Get-SurrealDbRecordCounts -Tables $tableNames -Namespace $SurrealNamespace -Database $SurrealDatabase
                        } else {
                            $componentEvidence.SurrealDB.QueryStatus = "count_check_unavailable"
                        }
                    } else {
                        $componentEvidence.SurrealDB.QueryStatus = "container_not_running"
                    }

                    $surrealSizeMB = [math]::Round(($metrics.TotalBytes / 1MB), 2)
                    Write-Pass "SurrealDB backup: $surrealSizeMB MB ($($metrics.FileCount) files)"
                    if ($componentEvidence.SurrealDB.QueryStatus -eq "count_check_unavailable") {
                        Write-Host "WARN  SurrealDB count evidence unavailable - physical backup still captured" -ForegroundColor Yellow
                    }
                    if ($componentEvidence.SurrealDB.QueryStatus -eq "container_not_running") {
                        Write-Host "WARN  SurrealDB container not running - count evidence skipped, physical backup only" -ForegroundColor Yellow
                    }
                }
            }
        }
    } catch {
        Write-Fail "SurrealDB backup failed: $_"
    }
}

# ── 5. Manifest ──────────────────────────────────────────────────────────

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
    ComponentSelection = $componentSelection
    Evidence = $componentEvidence
    GitCommit = $gitCommit
    RetentionDays = $RetentionDays
    BackupDir = $BackupDir
} | ConvertTo-Json -Depth 10

$manifestPath = Join-Path $WORK_DIR "manifest.json"
$manifest | Out-File -FilePath $manifestPath -Encoding UTF8
Write-Pass "Manifest written"

# ── 6. Compress ──────────────────────────────────────────────────────────

Write-Step "Compressing archive..."

$archivePath = Join-Path $BackupDir "$BACKUP_NAME.zip"
try {
    # Use .NET streaming ZIP to avoid Compress-Archive OutOfMemoryException on large dumps
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if (Test-Path $archivePath) { Remove-Item $archivePath -Force }
    [System.IO.Compression.ZipFile]::CreateFromDirectory($WORK_DIR, $archivePath)

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

# ── 7. Retention cleanup ────────────────────────────────────────────────

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

# ── 8. Summary ───────────────────────────────────────────────────────────

$duration = [math]::Round(((Get-Date) - $startTime).TotalSeconds, 1)
$totalArchives = (Get-ChildItem "$BackupDir\cdb_backup_*.zip" -ErrorAction SilentlyContinue).Count

Write-Host ""
Write-Host "=== Backup Summary ===" -ForegroundColor Cyan
Write-Host "  Postgres: $(if ($componentStatus.Postgres) { 'OK' } else { 'FAILED' })"
Write-Host "  Redis:    $(if ($componentStatus.Redis) { 'OK' } else { 'FAILED' })"
Write-Host "  SurrealDB: $(if ($IncludeSurrealDB) { if ($componentStatus.SurrealDB) { 'OK' } else { 'FAILED' } } else { 'SKIPPED' })"
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

if ($IncludeSurrealDB -and -not $componentStatus.SurrealDB) {
    if ($AllowSurrealDBFailure) {
        Write-Host "WARN  SurrealDB backup failed - tolerated via -AllowSurrealDBFailure" -ForegroundColor Yellow
    } else {
        Write-Fail "Backup incomplete - SurrealDB failed (use -AllowSurrealDBFailure to override)"
        exit 1
    }
}

Write-Pass "Backup completed successfully"
Write-Host ""
Write-Host "Restore with:" -ForegroundColor Yellow
Write-Host "  powershell.exe -ExecutionPolicy Bypass -File infrastructure\scripts\restore_all.ps1 -BackupName $BACKUP_NAME" -ForegroundColor White
Write-Host ""

exit 0
