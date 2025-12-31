# dr_restore.ps1 - Disaster Recovery Restore
# Restores from DR backup archive
# Acceptance Criterion F: DR procedures tested and documented

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$BackupName,

    [string]$BackupDir = "infrastructure/dr_backups",

    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "=== Claire de Binare - DR Restore ===" -ForegroundColor Cyan

$archivePath = "$BackupDir/${BackupName}.zip"
$extractPath = "$BackupDir/${BackupName}_restore"

# Check if backup exists
if (-not (Test-Path $archivePath)) {
    Write-Host "ERROR: Backup archive not found: $archivePath" -ForegroundColor Red
    Write-Host "`nAvailable backups:" -ForegroundColor Yellow
    Get-ChildItem -Path $BackupDir -Filter "*.zip" | ForEach-Object { Write-Host "  - $($_.BaseName)" }
    exit 1
}

Write-Host "Backup Archive: $archivePath" -ForegroundColor Yellow

# Extract archive
Write-Host "`n[Extraction] Decompressing backup..." -ForegroundColor Cyan

if (Test-Path $extractPath) {
    Remove-Item -Path $extractPath -Recurse -Force
}

Expand-Archive -Path $archivePath -DestinationPath $extractPath

# Read manifest
$manifestPath = Get-ChildItem -Path $extractPath -Filter "manifest.json" -Recurse | Select-Object -First 1
if (-not $manifestPath) {
    Write-Host "ERROR: Backup manifest not found!" -ForegroundColor Red
    exit 1
}

$manifest = Get-Content $manifestPath.FullName | ConvertFrom-Json

Write-Host "✓ Backup from: $($manifest.Timestamp)" -ForegroundColor Green
Write-Host "  Git Commit: $($manifest.GitCommit)" -ForegroundColor Gray

# Confirmation
if (-not $Force) {
    Write-Host "`nWARNING: This will REPLACE all current data!" -ForegroundColor Red
    $confirmation = Read-Host "Proceed with restore? (yes/NO)"
    if ($confirmation -ne 'yes') {
        Write-Host "Restore cancelled" -ForegroundColor Yellow
        exit 0
    }
}

$startTime = Get-Date

# Stop stack
Write-Host "`n[Preparation] Stopping stack..." -ForegroundColor Cyan
docker-compose down

# Find backup files
$backupFiles = Get-ChildItem -Path $extractPath -Recurse
$pgBackup = $backupFiles | Where-Object { $_.Name -eq "postgres_dump.sql" } | Select-Object -First 1
$redisBackup = $backupFiles | Where-Object { $_.Name -eq "redis_dump.rdb" } | Select-Object -First 1
$grafanaBackup = $backupFiles | Where-Object { $_.PSIsContainer -and $_.Name -eq "grafana_data" } | Select-Object -First 1
$promBackup = $backupFiles | Where-Object { $_.PSIsContainer -and $_.Name -eq "prometheus_data" } | Select-Object -First 1

# Restore Postgres
if ($manifest.Components.Postgres -and $pgBackup) {
    Write-Host "`n[1/4] Restoring Postgres..." -ForegroundColor Cyan

    # Start Postgres only
    docker-compose -f infrastructure/compose/base.yml up -d cdb_postgres
    Start-Sleep -Seconds 10

    # Drop and recreate database
    docker exec cdb_postgres psql -U claire_user -d postgres -c "DROP DATABASE IF EXISTS claire_de_binare;"
    docker exec cdb_postgres psql -U claire_user -d postgres -c "CREATE DATABASE claire_de_binare;"

    # Restore dump
    Get-Content $pgBackup.FullName | docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Postgres restored" -ForegroundColor Green
    }
    else {
        Write-Host "  ✗ Postgres restore failed!" -ForegroundColor Red
    }

    docker-compose down
}

# Restore Redis
if ($manifest.Components.Redis -and $redisBackup) {
    Write-Host "`n[2/4] Restoring Redis..." -ForegroundColor Cyan

    # Clear Redis volume
    docker volume rm claire_de_binare_redis_data -f | Out-Null
    docker volume create claire_de_binare_redis_data | Out-Null

    # Copy RDB file to volume
    docker run --rm `
        -v claire_de_binare_redis_data:/data `
        -v "${PWD}/$($redisBackup.DirectoryName):/backup:ro" `
        alpine sh -c "cp /backup/$($redisBackup.Name) /data/dump.rdb && chmod 644 /data/dump.rdb"

    Write-Host "  ✓ Redis restored" -ForegroundColor Green
}

# Restore Grafana
if ($manifest.Components.Grafana -and $grafanaBackup) {
    Write-Host "`n[3/4] Restoring Grafana..." -ForegroundColor Cyan

    # Clear Grafana volume
    docker volume rm claire_de_binare_grafana_data -f | Out-Null
    docker volume create claire_de_binare_grafana_data | Out-Null

    # Copy data to volume
    docker run --rm `
        -v claire_de_binare_grafana_data:/target `
        -v "${PWD}/$($grafanaBackup.FullName):/source:ro" `
        alpine sh -c "cp -r /source/. /target/"

    Write-Host "  ✓ Grafana restored" -ForegroundColor Green
}

# Restore Prometheus
if ($manifest.Components.Prometheus -and $promBackup) {
    Write-Host "`n[4/4] Restoring Prometheus..." -ForegroundColor Cyan

    # Clear Prometheus volume
    docker volume rm claire_de_binare_prom_data -f | Out-Null
    docker volume create claire_de_binare_prom_data | Out-Null

    # Copy data to volume
    docker run --rm `
        -v claire_de_binare_prom_data:/target `
        -v "${PWD}/$($promBackup.FullName):/source:ro" `
        alpine sh -c "cp -r /source/. /target/"

    Write-Host "  ✓ Prometheus restored" -ForegroundColor Green
}

# Restart stack
Write-Host "`n[Final] Restarting stack..." -ForegroundColor Cyan
docker-compose -f infrastructure/compose/base.yml -f infrastructure/compose/logging.yml up -d

Start-Sleep -Seconds 15

# Cleanup
Remove-Item -Path $extractPath -Recurse -Force

$duration = ((Get-Date) - $startTime).TotalSeconds

Write-Host "`n✓ Restore completed in $([math]::Round($duration, 1)) seconds" -ForegroundColor Green
Write-Host "`nVerify data integrity:" -ForegroundColor Yellow
Write-Host "  - Check Postgres: docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c '\dt'" -ForegroundColor White
Write-Host "  - Check Redis: docker exec cdb_redis redis-cli DBSIZE" -ForegroundColor White
Write-Host "  - Check Grafana: Open http://localhost:3000" -ForegroundColor White
