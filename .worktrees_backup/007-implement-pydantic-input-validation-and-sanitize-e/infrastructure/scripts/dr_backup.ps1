# dr_backup.ps1 - Disaster Recovery Backup
# Creates compressed backup of all persistent data (Postgres, Redis, Grafana, Prometheus)
# Acceptance Criterion F: DR procedures tested and documented

[CmdletBinding()]
param(
    [string]$BackupDir = "infrastructure/dr_backups",
    [switch]$SkipCompression
)

$ErrorActionPreference = "Stop"

Write-Host "=== Claire de Binare - DR Backup ===" -ForegroundColor Cyan

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupName = "cdb_backup_$timestamp"
$backupPath = "$BackupDir/$backupName"

# Create backup directory
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

New-Item -ItemType Directory -Path $backupPath | Out-Null

Write-Host "Backup Location: $backupPath" -ForegroundColor Yellow

# Check if containers are running
$running = docker ps --filter "name=cdb_" --format "{{.Names}}"
if (-not $running) {
    Write-Host "WARNING: No containers running. Starting stack..." -ForegroundColor Yellow
    docker-compose -f infrastructure/compose/base.yml up -d
    Start-Sleep -Seconds 15
}

$startTime = Get-Date

# Backup Postgres
Write-Host "`n[1/4] Backing up Postgres..." -ForegroundColor Cyan
$pgBackupFile = "$backupPath/postgres_dump.sql"

docker exec cdb_postgres pg_dump -U claire_user -d claire_de_binare > $pgBackupFile

if ($LASTEXITCODE -eq 0) {
    $size = [math]::Round((Get-Item $pgBackupFile).Length / 1MB, 2)
    Write-Host "  ✓ Postgres backup: ${size} MB" -ForegroundColor Green
}
else {
    Write-Host "  ✗ Postgres backup failed!" -ForegroundColor Red
}

# Backup Redis
Write-Host "`n[2/4] Backing up Redis..." -ForegroundColor Cyan
$redisBackupFile = "$backupPath/redis_dump.rdb"

# Trigger Redis save
docker exec cdb_redis redis-cli SAVE | Out-Null

# Copy RDB file from container
docker cp cdb_redis:/data/dump.rdb $redisBackupFile

if (Test-Path $redisBackupFile) {
    $size = [math]::Round((Get-Item $redisBackupFile).Length / 1MB, 2)
    Write-Host "  ✓ Redis backup: ${size} MB" -ForegroundColor Green
}
else {
    Write-Host "  ✗ Redis backup failed!" -ForegroundColor Red
}

# Backup Grafana
Write-Host "`n[3/4] Backing up Grafana..." -ForegroundColor Cyan
$grafanaBackupDir = "$backupPath/grafana_data"

# Copy Grafana volume data
New-Item -ItemType Directory -Path $grafanaBackupDir | Out-Null
docker run --rm `
    -v claire_de_binare_grafana_data:/source:ro `
    -v "${PWD}/${grafanaBackupDir}:/backup" `
    alpine sh -c "cd /source && cp -r . /backup/"

if (Test-Path "$grafanaBackupDir/grafana.db") {
    $size = [math]::Round((Get-ChildItem -Path $grafanaBackupDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
    Write-Host "  ✓ Grafana backup: ${size} MB" -ForegroundColor Green
}
else {
    Write-Host "  ✗ Grafana backup failed!" -ForegroundColor Red
}

# Backup Prometheus
Write-Host "`n[4/4] Backing up Prometheus..." -ForegroundColor Cyan
$promBackupDir = "$backupPath/prometheus_data"

# Copy Prometheus volume data
New-Item -ItemType Directory -Path $promBackupDir | Out-Null
docker run --rm `
    -v claire_de_binare_prom_data:/source:ro `
    -v "${PWD}/${promBackupDir}:/backup" `
    alpine sh -c "cd /source && cp -r . /backup/"

if (Test-Path $promBackupDir) {
    $size = [math]::Round((Get-ChildItem -Path $promBackupDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
    Write-Host "  ✓ Prometheus backup: ${size} MB" -ForegroundColor Green
}
else {
    Write-Host "  ✗ Prometheus backup failed!" -ForegroundColor Red
}

# Create backup manifest
$manifest = @{
    Timestamp = (Get-Date -Format 'o')
    BackupName = $backupName
    Components = @{
        Postgres = (Test-Path $pgBackupFile)
        Redis = (Test-Path $redisBackupFile)
        Grafana = (Test-Path "$grafanaBackupDir/grafana.db")
        Prometheus = (Test-Path $promBackupDir)
    }
    GitCommit = (git rev-parse HEAD)
    DockerComposeVersion = (docker-compose --version)
} | ConvertTo-Json -Depth 10

$manifest | Out-File -FilePath "$backupPath/manifest.json" -Encoding UTF8

# Compress backup
if (-not $SkipCompression) {
    Write-Host "`n[Compression] Creating archive..." -ForegroundColor Cyan
    $archivePath = "$BackupDir/${backupName}.zip"

    Compress-Archive -Path $backupPath -DestinationPath $archivePath -Force

    if (Test-Path $archivePath) {
        $size = [math]::Round((Get-Item $archivePath).Length / 1MB, 2)
        Write-Host "  ✓ Archive created: ${size} MB" -ForegroundColor Green

        # Remove uncompressed backup
        Remove-Item -Path $backupPath -Recurse -Force
    }
}

$duration = ((Get-Date) - $startTime).TotalSeconds

Write-Host "`n✓ Backup completed in $([math]::Round($duration, 1)) seconds" -ForegroundColor Green

if (-not $SkipCompression) {
    Write-Host "✓ Backup archive: $BackupDir/${backupName}.zip" -ForegroundColor Green
}
else {
    Write-Host "✓ Backup directory: $backupPath" -ForegroundColor Green
}

Write-Host "`nRestore with:" -ForegroundColor Yellow
Write-Host "  .\infrastructure\scripts\dr_restore.ps1 -BackupName $backupName" -ForegroundColor White
