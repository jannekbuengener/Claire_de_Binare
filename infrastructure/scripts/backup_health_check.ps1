# backup_health_check.ps1 - Backup Health Check with exit codes
# Checks F:\Claire_Backups for recent backup archives
#
# Usage:
#   powershell.exe -ExecutionPolicy Bypass -File backup_health_check.ps1
#   powershell.exe -ExecutionPolicy Bypass -File backup_health_check.ps1 -MaxAgeHours 4
#   powershell.exe -ExecutionPolicy Bypass -File backup_health_check.ps1 -BackupDir "D:\Other"
#
# Exit codes:
#   0 = PASS (recent backup found)
#   1 = FAIL (no backup, stale, or directory missing)

[CmdletBinding()]
param(
    [string]$BackupDir = "F:\Claire_Backups",
    [int]$MaxAgeHours = 2
)

# Check directory exists
if (-not (Test-Path $BackupDir)) {
    Write-Host "FAIL  Backup directory not accessible: $BackupDir" -ForegroundColor Red
    exit 1
}

# Find latest cdb_backup archive (from backup_all.ps1)
$latestConsolidated = Get-ChildItem "$BackupDir\cdb_backup_*.zip" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

# Fallback: also check legacy claire_de_binare_*.zip (from backup_postgres.ps1)
$latestLegacy = Get-ChildItem "$BackupDir\claire_de_binare_*.sql.zip" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

# Pick the most recent of either
$latest = $null
if ($latestConsolidated -and $latestLegacy) {
    if ($latestConsolidated.LastWriteTime -ge $latestLegacy.LastWriteTime) {
        $latest = $latestConsolidated
    } else {
        $latest = $latestLegacy
    }
} elseif ($latestConsolidated) {
    $latest = $latestConsolidated
} elseif ($latestLegacy) {
    $latest = $latestLegacy
}

if (-not $latest) {
    Write-Host "FAIL  No backup archives found in $BackupDir" -ForegroundColor Red
    exit 1
}

$age = (Get-Date) - $latest.LastWriteTime
$ageHours = [math]::Round($age.TotalHours, 1)
$sizeMB = [math]::Round($latest.Length / 1MB, 2)

if ($age.TotalHours -lt $MaxAgeHours) {
    Write-Host "PASS  Latest backup: $($latest.Name) ($sizeMB MB, ${ageHours}h old)" -ForegroundColor Green
    exit 0
} else {
    Write-Host "FAIL  Backup stale: $($latest.Name) is ${ageHours}h old (threshold: ${MaxAgeHours}h)" -ForegroundColor Red
    exit 1
}
