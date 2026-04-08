# restore_all.ps1 - Consolidated Restore (Postgres + Redis + optional SurrealDB)
# Source: F:\Claire_Backups
# Restores from backup_all.ps1 archives
#
# Usage:
#   powershell.exe -ExecutionPolicy Bypass -File restore_all.ps1 -BackupName cdb_backup_20260315_120000
#   powershell.exe -ExecutionPolicy Bypass -File restore_all.ps1 -BackupName cdb_backup_20260315_120000 -Force
#   powershell.exe -ExecutionPolicy Bypass -File restore_all.ps1 -ListAvailable
#   powershell.exe -ExecutionPolicy Bypass -File restore_all.ps1 -BackupName cdb_backup_20260315_120000 -SurrealDbVolumeName cdb_database_surrealdb_data
#
# Exit codes:
#   0 = included components restored successfully
#   1 = archive missing, verification failure, or any included component restore failed

[CmdletBinding()]
param(
    [string]$BackupName = "",
    [string]$BackupDir = "F:\Claire_Backups",
    [switch]$Force,
    [switch]$ListAvailable,
    [string]$SurrealDbVolumeName = ""
)

$ErrorActionPreference = "Stop"

function Write-Pass { param([string]$Msg) Write-Host "PASS  $Msg" -ForegroundColor Green }
function Write-Fail { param([string]$Msg) Write-Host "FAIL  $Msg" -ForegroundColor Red }
function Write-Step { param([string]$Msg) Write-Host "---   $Msg" -ForegroundColor Cyan }

function Test-ObjectProperty {
    param(
        $Object,
        [string]$Name
    )

    if ($null -eq $Object) {
        return $false
    }

    return ($Object.PSObject.Properties.Name -contains $Name)
}

function ConvertTo-StringMap {
    param($Object)

    $map = @{}
    if ($null -eq $Object) {
        return $map
    }

    if ($Object -is [hashtable]) {
        return $Object
    }

    foreach ($property in $Object.PSObject.Properties) {
        $map[$property.Name] = $property.Value
    }

    return $map
}

function Get-DockerVolumeMetrics {
    param([string]$VolumeName)

    $metricsCommand = 'file_count=$(find /data -type f | wc -l); total_bytes=$(find /data -type f -exec wc -c {} \; | awk ''{sum+=$1} END {print sum+0}''); printf ''%s %s'' "$file_count" "$total_bytes"'

    try {
        $rawMetrics = docker run --rm -v "${VolumeName}:/data" alpine sh -c $metricsCommand 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($rawMetrics)) {
            return $null
        }

        $parts = ($rawMetrics.Trim() -split "\s+")
        if ($parts.Count -lt 2) {
            return $null
        }

        return @{
            FileCount = [int64]$parts[0]
            TotalBytes = [int64]$parts[1]
        }
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

    try {
        $rawResponse = $Query | docker exec -i cdb_surrealdb /surreal sql --hide-welcome --json --endpoint ws://127.0.0.1:8000 --namespace $Namespace --database $Database 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($rawResponse)) {
            return $null
        }

        return ($rawResponse.Trim() | ConvertFrom-Json)
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

    $tableNames = @()
    $responseItems = @($info)
    if ($responseItems.Count -gt 0) {
        $result = $responseItems[0].result
        if ($result -and $result.PSObject.Properties.Name -contains "tb" -and $result.tb) {
            $tableNames = @($result.tb.PSObject.Properties.Name)
        }
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

function Wait-SurrealDbHealthy {
    param(
        [int]$Retries = 10,
        [int]$DelaySeconds = 3
    )

    for ($attempt = 1; $attempt -le $Retries; $attempt++) {
        docker exec cdb_surrealdb /surreal is-ready -e ws://127.0.0.1:8000 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            return $true
        }

        Start-Sleep -Seconds $DelaySeconds
    }

    return $false
}

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

$surrealDbEvidence = $null
if (Test-ObjectProperty -Object $manifest -Name "Evidence" -and (Test-ObjectProperty -Object $manifest.Evidence -Name "SurrealDB")) {
    $surrealDbEvidence = $manifest.Evidence.SurrealDB
}

$surrealDbRequested = $false
if ($surrealDbEvidence -and (Test-ObjectProperty -Object $surrealDbEvidence -Name "Requested")) {
    $surrealDbRequested = [bool]$surrealDbEvidence.Requested
} elseif ((Test-ObjectProperty -Object $manifest -Name "ComponentSelection") -and (Test-ObjectProperty -Object $manifest.ComponentSelection -Name "SurrealDB")) {
    $surrealDbRequested = [bool]$manifest.ComponentSelection.SurrealDB
}

$surrealDbIncluded = (Test-ObjectProperty -Object $manifest.Components -Name "SurrealDB") -and [bool]$manifest.Components.SurrealDB
$resolvedSurrealDbVolumeName = $SurrealDbVolumeName
if ([string]::IsNullOrWhiteSpace($resolvedSurrealDbVolumeName)) {
    if ($surrealDbEvidence -and (Test-ObjectProperty -Object $surrealDbEvidence -Name "VolumeName") -and -not [string]::IsNullOrWhiteSpace([string]$surrealDbEvidence.VolumeName)) {
        $resolvedSurrealDbVolumeName = [string]$surrealDbEvidence.VolumeName
    } else {
        $resolvedSurrealDbVolumeName = "cdb_database_surrealdb_data"
    }
}

$surrealDbNamespace = "governance"
if ($surrealDbEvidence -and (Test-ObjectProperty -Object $surrealDbEvidence -Name "Namespace") -and -not [string]::IsNullOrWhiteSpace([string]$surrealDbEvidence.Namespace)) {
    $surrealDbNamespace = [string]$surrealDbEvidence.Namespace
}

$surrealDbDatabase = "governance_mirror"
if ($surrealDbEvidence -and (Test-ObjectProperty -Object $surrealDbEvidence -Name "Database") -and -not [string]::IsNullOrWhiteSpace([string]$surrealDbEvidence.Database)) {
    $surrealDbDatabase = [string]$surrealDbEvidence.Database
}

$surrealDbExpectedTables = @()
if ($surrealDbEvidence -and (Test-ObjectProperty -Object $surrealDbEvidence -Name "Tables") -and $surrealDbEvidence.Tables) {
    $surrealDbExpectedTables = @($surrealDbEvidence.Tables)
}

$surrealDbExpectedCounts = @{}
if ($surrealDbEvidence -and (Test-ObjectProperty -Object $surrealDbEvidence -Name "RecordCounts")) {
    $surrealDbExpectedCounts = ConvertTo-StringMap -Object $surrealDbEvidence.RecordCounts
}

$surrealDbExpectedFileCount = 0
if ($surrealDbEvidence -and (Test-ObjectProperty -Object $surrealDbEvidence -Name "FileCount")) {
    $surrealDbExpectedFileCount = [int64]$surrealDbEvidence.FileCount
}

$surrealDbExpectedTotalBytes = 0
if ($surrealDbEvidence -and (Test-ObjectProperty -Object $surrealDbEvidence -Name "TotalBytes")) {
    $surrealDbExpectedTotalBytes = [int64]$surrealDbEvidence.TotalBytes
}

$surrealDbDisplay = "not requested"
if ($surrealDbIncluded) {
    $surrealDbDisplay = "included"
} elseif ($surrealDbRequested) {
    $surrealDbDisplay = "requested but not captured"
}

Write-Pass "Manifest loaded"
Write-Host "      Backup from:  $($manifest.Timestamp)"
Write-Host "      Git commit:   $($manifest.GitCommit)"
Write-Host "      Postgres:     $(if ($manifest.Components.Postgres) { 'included' } else { 'not included' })"
Write-Host "      Redis:        $(if ($manifest.Components.Redis) { 'included' } else { 'not included' })"
Write-Host "      SurrealDB:    $surrealDbDisplay"
Write-Host ""

# ── Safety confirmation ──────────────────────────────────────────────────

$restoreTargets = @()
if ($manifest.Components.Postgres) { $restoreTargets += "Postgres" }
if ($manifest.Components.Redis) { $restoreTargets += "Redis" }
if ($surrealDbIncluded) { $restoreTargets += "SurrealDB" }

if ($restoreTargets.Count -eq 0) {
    Write-Fail "Archive does not contain any restorable components"
    Remove-Item -Path $extractDir -Recurse -Force
    exit 1
}

if (-not $Force) {
    Write-Host "WARNING: This will DESTRUCTIVELY REPLACE current $($restoreTargets -join ', ') data!" -ForegroundColor Red
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
    SurrealDB = $false
}

# ── Restore Postgres ─────────────────────────────────────────────────────

if ($manifest.Components.Postgres) {
    Write-Step "Restoring Postgres..."

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
    Write-Step "Restoring Redis..."

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
                    Start-Sleep -Seconds 5

                    # Resolve Redis password from Docker secret
                    $redisPassword = ""
                    try {
                        $redisPassword = (docker exec cdb_redis sh -c 'cat /run/secrets/redis_password 2>/dev/null' 2>&1).Trim()
                        if ($LASTEXITCODE -ne 0) { $redisPassword = "" }
                    } catch { $redisPassword = "" }

                    # Verify Redis is up (with auth if available)
                    if ($redisPassword -ne "") {
                        $redisPing = docker exec cdb_redis redis-cli -a $redisPassword --no-auth-warning PING 2>&1
                    } else {
                        $redisPing = docker exec cdb_redis redis-cli PING 2>&1
                    }
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

# ── Restore SurrealDB ────────────────────────────────────────────────────

if ($surrealDbIncluded) {
    Write-Step "Restoring SurrealDB sidecar volume..."

    $surrealBackup = Get-ChildItem -Path $backupRoot -Directory -Filter "surrealdb_data" -Recurse | Select-Object -First 1

    if (-not $surrealBackup) {
        Write-Fail "surrealdb_data directory not found in archive"
    } else {
        $surrealContainer = docker ps -a --filter "name=cdb_surrealdb" --format "{{.Names}}" 2>&1
        if ($surrealContainer -notmatch "cdb_surrealdb") {
            Write-Fail "Container cdb_surrealdb not found - create the SurrealDB sidecar stack before restore"
        } else {
            try {
                $surrealRunning = docker ps --filter "name=cdb_surrealdb" --format "{{.Names}}" 2>&1
                if ($surrealRunning -match "cdb_surrealdb") {
                    docker stop cdb_surrealdb 2>&1 | Out-Null
                }

                $null = docker volume inspect $resolvedSurrealDbVolumeName 2>&1
                if ($LASTEXITCODE -ne 0) {
                    docker volume create $resolvedSurrealDbVolumeName 2>&1 | Out-Null
                }

                if ($LASTEXITCODE -ne 0) {
                    Write-Fail "Failed to create SurrealDB volume: $resolvedSurrealDbVolumeName"
                } else {
                    $clearCommand = 'mkdir -p /data && rm -rf /data/* /data/.[!.]* /data/..?*'
                    docker run --rm -v "${resolvedSurrealDbVolumeName}:/data" alpine sh -c $clearCommand 2>&1 | Out-Null

                    if ($LASTEXITCODE -ne 0) {
                        Write-Fail "Failed to clear SurrealDB volume before restore"
                    } else {
                        docker run --rm `
                            -v "${resolvedSurrealDbVolumeName}:/target" `
                            -v "$($surrealBackup.FullName):/source:ro" `
                            alpine sh -c "mkdir -p /target && cp -a /source/. /target/" 2>&1 | Out-Null

                        if ($LASTEXITCODE -ne 0) {
                            Write-Fail "Failed to copy SurrealDB backup into volume"
                        } else {
                            $postCopyMetrics = Get-DockerVolumeMetrics -VolumeName $resolvedSurrealDbVolumeName
                            if (-not $postCopyMetrics) {
                                Write-Fail "Unable to measure restored SurrealDB volume"
                            } elseif (($surrealDbExpectedFileCount -gt 0 -or $surrealDbExpectedTotalBytes -gt 0) -and `
                                ($postCopyMetrics.FileCount -ne $surrealDbExpectedFileCount -or $postCopyMetrics.TotalBytes -ne $surrealDbExpectedTotalBytes)) {
                                Write-Fail "SurrealDB volume verification failed: expected $surrealDbExpectedFileCount files / $surrealDbExpectedTotalBytes bytes, got $($postCopyMetrics.FileCount) files / $($postCopyMetrics.TotalBytes) bytes"
                            } else {
                                docker start cdb_surrealdb 2>&1 | Out-Null

                                if ($LASTEXITCODE -ne 0) {
                                    Write-Fail "Failed to start cdb_surrealdb after restore"
                                } elseif (-not (Wait-SurrealDbHealthy)) {
                                    Write-Fail "SurrealDB health check failed after restore"
                                } else {
                                    $postTables = Get-SurrealDbTableNames -Namespace $surrealDbNamespace -Database $surrealDbDatabase
                                    if ($surrealDbExpectedCounts.Count -gt 0) {
                                        $postCounts = Get-SurrealDbRecordCounts -Tables @($surrealDbExpectedCounts.Keys) -Namespace $surrealDbNamespace -Database $surrealDbDatabase
                                        $countMismatches = @()

                                        foreach ($tableName in @($surrealDbExpectedCounts.Keys | Sort-Object)) {
                                            if (-not $postCounts.ContainsKey($tableName)) {
                                                $countMismatches += "${tableName}:missing"
                                            } elseif ([int64]$postCounts[$tableName] -ne [int64]$surrealDbExpectedCounts[$tableName]) {
                                                $countMismatches += "${tableName}:expected=$($surrealDbExpectedCounts[$tableName]),actual=$($postCounts[$tableName])"
                                            }
                                        }

                                        if ($countMismatches.Count -gt 0) {
                                            Write-Fail "SurrealDB count verification failed ($($countMismatches -join '; '))"
                                        } else {
                                            $restoreResults.SurrealDB = $true
                                            Write-Pass "SurrealDB restored, healthy, and count-verified"
                                        }
                                    } elseif ($surrealDbExpectedTables.Count -gt 0) {
                                        $missingTables = @($surrealDbExpectedTables | Where-Object { $postTables -notcontains $_ })
                                        if ($missingTables.Count -gt 0) {
                                            Write-Fail "SurrealDB restored but expected tables are missing: $($missingTables -join ', ')"
                                        } else {
                                            $restoreResults.SurrealDB = $true
                                            Write-Pass "SurrealDB restored, healthy, and table inventory verified"
                                        }
                                    } elseif ($postTables.Count -gt 0) {
                                        $restoreResults.SurrealDB = $true
                                        Write-Pass "SurrealDB restored and healthy (table inventory present)"
                                    } else {
                                        Write-Fail "SurrealDB health check passed but no table inventory was visible"
                                    }
                                }
                            }
                        }
                    }
                }
            } catch {
                Write-Fail "SurrealDB restore failed: $_"
            }
        }
    }
} elseif ($surrealDbRequested) {
    Write-Host "      SurrealDB was requested when the backup was created but not captured successfully - skipping" -ForegroundColor Gray
} else {
    Write-Host "      SurrealDB not included in this backup - skipping" -ForegroundColor Gray
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
Write-Host "  SurrealDB: $(if ($surrealDbIncluded) { if ($restoreResults.SurrealDB) { 'OK' } else { 'FAILED' } } elseif ($surrealDbRequested) { 'NOT CAPTURED IN BACKUP' } else { 'SKIPPED' })"
Write-Host "  Duration: $duration s"
Write-Host ""
Write-Host "Verify manually:" -ForegroundColor Yellow
Write-Host "  docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c '\dt'" -ForegroundColor White
Write-Host "  docker exec cdb_redis redis-cli DBSIZE" -ForegroundColor White
if ($surrealDbIncluded) {
    Write-Host "  docker exec cdb_surrealdb /surreal is-ready -e ws://127.0.0.1:8000" -ForegroundColor White
}
Write-Host ""

# Exit code: fail if any included component failed
if ($manifest.Components.Postgres -and -not $restoreResults.Postgres) {
    Write-Fail "Restore incomplete - Postgres failed"
    exit 1
}

if ($manifest.Components.Redis -and -not $restoreResults.Redis) {
    Write-Fail "Restore incomplete - Redis failed"
    exit 1
}

if ($surrealDbIncluded -and -not $restoreResults.SurrealDB) {
    Write-Fail "Restore incomplete - SurrealDB failed"
    exit 1
}

Write-Pass "Restore completed"
exit 0
