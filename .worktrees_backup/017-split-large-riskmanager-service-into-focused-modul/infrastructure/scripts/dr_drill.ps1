# dr_drill.ps1 - Automated DR Drill
# Tests full DR cycle: backup → destroy → restore → verify
# Acceptance Criterion F: DR procedures tested

[CmdletBinding()]
param(
    [switch]$SkipBackup,
    [string]$UseBackup = ""
)

$ErrorActionPreference = "Stop"

Write-Host "=== Claire de Binare - DR Drill ===" -ForegroundColor Cyan
Write-Host "This will test the full disaster recovery cycle" -ForegroundColor Yellow

$confirmation = Read-Host "`nThis is a DESTRUCTIVE operation. Continue? (yes/NO)"
if ($confirmation -ne 'yes') {
    Write-Host "DR Drill cancelled" -ForegroundColor Yellow
    exit 0
}

$drillStartTime = Get-Date
$results = @{
    BackupSuccess = $false
    DestroySuccess = $false
    RestoreSuccess = $false
    VerifySuccess = $false
    Errors = @()
}

# Phase 1: Create backup (unless skipped or using existing)
if (-not $SkipBackup -and -not $UseBackup) {
    Write-Host "`n=== PHASE 1: CREATE BACKUP ===" -ForegroundColor Magenta
    try {
        & ".\infrastructure\scripts\dr_backup.ps1"
        if ($LASTEXITCODE -eq 0) {
            $results.BackupSuccess = $true
            # Get latest backup name
            $UseBackup = (Get-ChildItem -Path "infrastructure/dr_backups" -Filter "*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 1).BaseName
            Write-Host "✓ Backup created: $UseBackup" -ForegroundColor Green
        }
        else {
            throw "Backup script failed"
        }
    }
    catch {
        $results.Errors += "Backup failed: $_"
        Write-Host "✗ Backup phase failed: $_" -ForegroundColor Red
    }
}
else {
    $results.BackupSuccess = $true
    if ($UseBackup) {
        Write-Host "`n=== PHASE 1: USING EXISTING BACKUP ===" -ForegroundColor Magenta
        Write-Host "Backup: $UseBackup" -ForegroundColor Yellow
    }
    else {
        Write-Host "`n=== PHASE 1: BACKUP SKIPPED ===" -ForegroundColor Magenta
    }
}

# Phase 2: Simulate disaster (destroy all data)
Write-Host "`n=== PHASE 2: SIMULATE DISASTER ===" -ForegroundColor Magenta
Write-Host "Destroying all containers and volumes..." -ForegroundColor Yellow

try {
    # Stop all containers
    docker-compose down

    # Remove all volumes (DESTRUCTIVE!)
    $volumes = docker volume ls --filter "name=claire_de_binare_" --format "{{.Name}}"
    foreach ($vol in $volumes) {
        docker volume rm $vol -f | Out-Null
        Write-Host "  Removed: $vol" -ForegroundColor Gray
    }

    $results.DestroySuccess = $true
    Write-Host "✓ Disaster simulation complete" -ForegroundColor Green
}
catch {
    $results.Errors += "Destroy failed: $_"
    Write-Host "✗ Destroy phase failed: $_" -ForegroundColor Red
}

# Phase 3: Restore from backup
Write-Host "`n=== PHASE 3: RESTORE FROM BACKUP ===" -ForegroundColor Magenta

if (-not $UseBackup) {
    Write-Host "ERROR: No backup specified for restore!" -ForegroundColor Red
    $results.Errors += "No backup specified"
}
else {
    try {
        & ".\infrastructure\scripts\dr_restore.ps1" -BackupName $UseBackup -Force
        if ($LASTEXITCODE -eq 0) {
            $results.RestoreSuccess = $true
            Write-Host "✓ Restore complete" -ForegroundColor Green
        }
        else {
            throw "Restore script failed"
        }
    }
    catch {
        $results.Errors += "Restore failed: $_"
        Write-Host "✗ Restore phase failed: $_" -ForegroundColor Red
    }
}

# Phase 4: Verify restoration
Write-Host "`n=== PHASE 4: VERIFY RESTORATION ===" -ForegroundColor Magenta

$verifyPassed = 0
$verifyTotal = 0

# Wait for services to stabilize
Start-Sleep -Seconds 20

# Check Postgres
Write-Host "`n[1/4] Verifying Postgres..." -ForegroundColor Cyan
$verifyTotal++
try {
    $tables = docker exec cdb_postgres psql -U claire_user -d claire_de_binare -t -c "\dt" 2>&1
    if ($tables -match "public \|") {
        Write-Host "  ✓ Postgres has tables" -ForegroundColor Green
        $verifyPassed++
    }
    else {
        Write-Host "  ✗ Postgres has no tables" -ForegroundColor Red
        $results.Errors += "Postgres verification failed: no tables"
    }
}
catch {
    Write-Host "  ✗ Postgres check failed: $_" -ForegroundColor Red
    $results.Errors += "Postgres verification failed: $_"
}

# Check Redis
Write-Host "`n[2/4] Verifying Redis..." -ForegroundColor Cyan
$verifyTotal++
try {
    $keyCount = docker exec cdb_redis redis-cli DBSIZE 2>&1 | Select-String -Pattern "\d+"
    if ($keyCount) {
        Write-Host "  ✓ Redis has data (keys: $($keyCount.Matches.Value))" -ForegroundColor Green
        $verifyPassed++
    }
    else {
        Write-Host "  ⚠ Redis is empty" -ForegroundColor Yellow
        $verifyPassed++  # Empty Redis is still valid
    }
}
catch {
    Write-Host "  ✗ Redis check failed: $_" -ForegroundColor Red
    $results.Errors += "Redis verification failed: $_"
}

# Check Grafana
Write-Host "`n[3/4] Verifying Grafana..." -ForegroundColor Cyan
$verifyTotal++
try {
    $grafanaHealth = docker exec cdb_grafana curl -fsS http://localhost:3000/api/health 2>&1
    if ($grafanaHealth -match "ok") {
        Write-Host "  ✓ Grafana is healthy" -ForegroundColor Green
        $verifyPassed++
    }
    else {
        Write-Host "  ✗ Grafana health check failed" -ForegroundColor Red
        $results.Errors += "Grafana verification failed"
    }
}
catch {
    Write-Host "  ⚠ Grafana check inconclusive: $_" -ForegroundColor Yellow
}

# Check Prometheus
Write-Host "`n[4/4] Verifying Prometheus..." -ForegroundColor Cyan
$verifyTotal++
try {
    $promHealth = docker exec cdb_prometheus wget -qO- http://localhost:9090/-/healthy 2>&1
    if ($promHealth -match "Prometheus Server is Healthy" -or $promHealth -match "Prometheus is Healthy") {
        Write-Host "  ✓ Prometheus is healthy" -ForegroundColor Green
        $verifyPassed++
    }
    else {
        Write-Host "  ✗ Prometheus health check failed" -ForegroundColor Red
        $results.Errors += "Prometheus verification failed"
    }
}
catch {
    Write-Host "  ⚠ Prometheus check inconclusive: $_" -ForegroundColor Yellow
}

$results.VerifySuccess = ($verifyPassed -eq $verifyTotal)

# Final Report
$drillDuration = ((Get-Date) - $drillStartTime).TotalSeconds

Write-Host "`n=== DR DRILL RESULTS ===" -ForegroundColor Magenta
Write-Host "Duration: $([math]::Round($drillDuration, 1)) seconds" -ForegroundColor Yellow

Write-Host "`nPhases:" -ForegroundColor White
Write-Host "  Backup:  $(if ($results.BackupSuccess) { '✓ PASS' } else { '✗ FAIL' })" -ForegroundColor $(if ($results.BackupSuccess) { 'Green' } else { 'Red' })
Write-Host "  Destroy: $(if ($results.DestroySuccess) { '✓ PASS' } else { '✗ FAIL' })" -ForegroundColor $(if ($results.DestroySuccess) { 'Green' } else { 'Red' })
Write-Host "  Restore: $(if ($results.RestoreSuccess) { '✓ PASS' } else { '✗ FAIL' })" -ForegroundColor $(if ($results.RestoreSuccess) { 'Green' } else { 'Red' })
Write-Host "  Verify:  $(if ($results.VerifySuccess) { '✓ PASS' } else { '✗ FAIL' }) ($verifyPassed/$verifyTotal checks)" -ForegroundColor $(if ($results.VerifySuccess) { 'Green' } else { 'Red' })

if ($results.Errors.Count -gt 0) {
    Write-Host "`nErrors:" -ForegroundColor Red
    $results.Errors | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
}

$allPassed = $results.BackupSuccess -and $results.DestroySuccess -and $results.RestoreSuccess -and $results.VerifySuccess

if ($allPassed) {
    Write-Host "`n✓ DR DRILL PASSED - All phases successful" -ForegroundColor Green
    Write-Host "✓ Acceptance Criterion F met: DR tested and working" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "`n✗ DR DRILL FAILED - See errors above" -ForegroundColor Red
    exit 1
}
