# Docker Volume Backup Script für Claire de Binare
# Erstellt vollständiges Backup aller kritischen Volumes

param(
    [string]$BackupRoot = "D:\Dev\Backups",
    [switch]$IncludePostgres = $false
)

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BACKUP_DIR = Join-Path $BackupRoot "docker_backup_$timestamp"
$REPO_DIR = "D:\Dev\Workspaces\Repos\Claire_de_Binare"

Write-Host "=== Docker Volume Backup ===" -ForegroundColor Green
Write-Host "Timestamp: $timestamp" -ForegroundColor Cyan
Write-Host "Backup Dir: $BACKUP_DIR" -ForegroundColor Cyan
Write-Host ""

# Create backup directory
New-Item -ItemType Directory -Path $BACKUP_DIR -Force | Out-Null

# Function to backup volume
function Backup-Volume {
    param(
        [string]$VolumeName,
        [string]$BackupFileName
    )
    
    Write-Host "Backing up: $VolumeName" -ForegroundColor Yellow
    
    docker run --rm `
        -v ${VolumeName}:/data `
        -v ${BACKUP_DIR}:/backup `
        alpine tar czf /backup/${BackupFileName} -C /data .
    
    if ($LASTEXITCODE -eq 0) {
        $size = (Get-Item "${BACKUP_DIR}\${BackupFileName}").Length / 1KB
        Write-Host "  ✅ $VolumeName → $BackupFileName ($([math]::Round($size, 2)) KB)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $VolumeName FAILED" -ForegroundColor Red
    }
    Write-Host ""
}

# Backup all volumes
Backup-Volume -VolumeName "claire_de_binare_redis_data" -BackupFileName "redis_data.tar.gz"
Backup-Volume -VolumeName "claire_de_binare_grafana_data" -BackupFileName "grafana_data.tar.gz"
Backup-Volume -VolumeName "claire_de_binare_prom_data" -BackupFileName "prometheus_data.tar.gz"
Backup-Volume -VolumeName "claire_de_binare_loki_data" -BackupFileName "loki_data.tar.gz"
Backup-Volume -VolumeName "claude-memory" -BackupFileName "claude_memory.tar.gz"

if ($IncludePostgres) {
    Write-Host "Backing up PostgreSQL (SQL dump)..." -ForegroundColor Yellow
    docker exec cdb_postgres pg_dumpall -U postgres > "${BACKUP_DIR}\postgres_backup.sql"
    if ($LASTEXITCODE -eq 0) {
        $size = (Get-Item "${BACKUP_DIR}\postgres_backup.sql").Length / 1KB
        Write-Host "  ✅ PostgreSQL → postgres_backup.sql ($([math]::Round($size, 2)) KB)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ PostgreSQL backup FAILED" -ForegroundColor Red
    }
    Write-Host ""
}

# Backup configuration
Write-Host "Backing up configuration..." -ForegroundColor Yellow

if (Test-Path "${REPO_DIR}\.env") {
    Copy-Item "${REPO_DIR}\.env" "${BACKUP_DIR}\.env_backup"
    Write-Host "  ✅ .env file" -ForegroundColor Green
}

if (Test-Path "${REPO_DIR}\.secrets.example") {
    Copy-Item -Recurse "${REPO_DIR}\.secrets.example" "${BACKUP_DIR}\.secrets_example_backup"
    Write-Host "  ✅ .secrets.example" -ForegroundColor Green
}

# Document container state
docker ps -a --format "{{.Names}}`t{{.Image}}`t{{.Status}}`t{{.Ports}}" | Out-File "${BACKUP_DIR}\container_list.txt"
docker volume ls | Out-File "${BACKUP_DIR}\volume_list.txt"
docker network ls | Out-File "${BACKUP_DIR}\network_list.txt"

Write-Host "  ✅ Container/Volume/Network lists" -ForegroundColor Green
Write-Host ""

# Document secrets location
"SECRETS_PATH=C:\Users\janne\Documents\.secrets\.cdb\" | Out-File "${BACKUP_DIR}\secrets_location.txt"
"Contains: MEXC API keys, Grafana, Postgres, Redis passwords" | Out-File "${BACKUP_DIR}\secrets_location.txt" -Append

# Calculate total size
$totalSize = (Get-ChildItem $BACKUP_DIR -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB

Write-Host "=== Backup Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Location: $BACKUP_DIR" -ForegroundColor Cyan
Write-Host "Total Size: $([math]::Round($totalSize, 2)) MB" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backed up volumes:" -ForegroundColor Cyan
Write-Host "  - Redis Data" -ForegroundColor White
Write-Host "  - Grafana Dashboards" -ForegroundColor White
Write-Host "  - Prometheus Metrics" -ForegroundColor White
Write-Host "  - Loki Logs" -ForegroundColor White
Write-Host "  - Claude Memory" -ForegroundColor White
if ($IncludePostgres) {
    Write-Host "  - PostgreSQL (SQL dump)" -ForegroundColor White
}
Write-Host ""
Write-Host "To restore, use: restore_volumes.ps1" -ForegroundColor Yellow
Write-Host ""

# Copy restore scripts to backup
Copy-Item "$PSScriptRoot\restore_volumes.ps1" $BACKUP_DIR -ErrorAction SilentlyContinue
Copy-Item "$PSScriptRoot\verify_restore.ps1" $BACKUP_DIR -ErrorAction SilentlyContinue
Copy-Item "$PSScriptRoot\QUICK_START.md" $BACKUP_DIR -ErrorAction SilentlyContinue
Copy-Item "$PSScriptRoot\RESTORE_GUIDE.md" $BACKUP_DIR -ErrorAction SilentlyContinue

if ($?) {
    Write-Host "✅ Restore scripts included in backup" -ForegroundColor Green
}
