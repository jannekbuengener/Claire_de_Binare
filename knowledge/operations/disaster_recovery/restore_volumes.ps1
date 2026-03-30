# Automatic Docker Volume Restore Script
# Run this after Docker Desktop reinstallation
#
# Usage:
#   .\restore_volumes.ps1 -BackupDir "F:\Claire_Backups\docker_backup_20260330_120000"
#   .\restore_volumes.ps1 -BackupDir "..." -RepoDir "C:\Projects\Claire_de_Binare"

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupDir,

    [string]$RepoDir = (git -C $PSScriptRoot rev-parse --show-toplevel 2>$null)
)

if (-not $RepoDir) {
    Write-Host "ERROR: Could not detect repo root. Pass -RepoDir explicitly." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $BackupDir)) {
    Write-Host "ERROR: Backup directory not found: $BackupDir" -ForegroundColor Red
    exit 1
}

$BACKUP_DIR = $BackupDir
$REPO_DIR = $RepoDir

Write-Host "=== Docker Volume Restore - Starting ===" -ForegroundColor Green
Write-Host "Backup: $BACKUP_DIR" -ForegroundColor Cyan
Write-Host ""

# Function to restore volume
function Restore-Volume {
    param(
        [string]$VolumeName,
        [string]$BackupPath,
        [string]$TargetPath,
        [string]$IsTarGz = $false
    )
    
    Write-Host "Restoring: $VolumeName" -ForegroundColor Yellow
    
    # Create volume
    docker volume create $VolumeName | Out-Null
    
    if ($IsTarGz -eq $true) {
        # Restore from tar.gz
        docker run --rm `
            -v ${VolumeName}:/data `
            -v ${BACKUP_DIR}:/backup `
            alpine sh -c "cd /data && tar xzf /backup/$BackupPath"
    } else {
        # Restore from directory
        docker run --rm `
            -v ${VolumeName}:${TargetPath} `
            -v ${BACKUP_DIR}/${BackupPath}:/backup `
            alpine cp -r /backup/. ${TargetPath}/
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ $VolumeName restored" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $VolumeName FAILED" -ForegroundColor Red
    }
    Write-Host ""
}

# Restore Redis
Restore-Volume -VolumeName "claire_de_binare_redis_data" `
               -BackupPath "redis_data" `
               -TargetPath "/data"

# Restore Grafana
Restore-Volume -VolumeName "claire_de_binare_grafana_data" `
               -BackupPath "grafana_data" `
               -TargetPath "/var/lib/grafana"

# Restore Claude Memory
Restore-Volume -VolumeName "claude-memory" `
               -BackupPath "claude_memory.tar.gz" `
               -TargetPath "/data" `
               -IsTarGz $true

# Restore Prometheus
Restore-Volume -VolumeName "claire_de_binare_prom_data" `
               -BackupPath "prometheus_data.tar.gz" `
               -TargetPath "/data" `
               -IsTarGz $true

# Restore Loki
Restore-Volume -VolumeName "claire_de_binare_loki_data" `
               -BackupPath "loki_data.tar.gz" `
               -TargetPath "/data" `
               -IsTarGz $true

# Create Postgres volume (data might still exist from before)
Write-Host "Creating PostgreSQL volume (data may already exist)..." -ForegroundColor Yellow
docker volume create claire_de_binare_postgres_data | Out-Null
Write-Host "  ✅ PostgreSQL volume ready" -ForegroundColor Green
Write-Host ""

# Restore .env file
Write-Host "Restoring .env file..." -ForegroundColor Yellow
Copy-Item "$BACKUP_DIR\.env_backup" "$REPO_DIR\.env" -Force
Write-Host "  ✅ .env restored" -ForegroundColor Green
Write-Host ""

Write-Host "=== Volume Restore Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. cd $REPO_DIR"
Write-Host "2. Run: make docker-up"
Write-Host "3. Check: docker ps"
Write-Host "4. Verify: http://localhost:3000 (Grafana)"
Write-Host ""
