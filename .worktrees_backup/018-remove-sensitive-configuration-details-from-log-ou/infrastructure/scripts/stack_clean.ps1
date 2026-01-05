# stack_clean.ps1 - Safe Stack Cleanup
# Removes containers, networks, and optionally volumes
# Acceptance Criterion G: Confusion-proofing (safe clean command)

[CmdletBinding()]
param(
    [switch]$DeepClean,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "=== Claire de Binare - Stack Clean ===" -ForegroundColor Cyan

if ($DeepClean) {
    Write-Host "Mode: DEEP CLEAN (removes volumes - DATA LOSS!)" -ForegroundColor Red
}
else {
    Write-Host "Mode: SAFE CLEAN (preserves volumes)" -ForegroundColor Green
}

# Safety check
if ($DeepClean -and -not $Force) {
    Write-Host "`nWARNING: Deep clean will DELETE all persistent data:" -ForegroundColor Red
    Write-Host "  - Postgres database" -ForegroundColor Yellow
    Write-Host "  - Redis cache" -ForegroundColor Yellow
    Write-Host "  - Grafana dashboards & settings" -ForegroundColor Yellow
    Write-Host "  - Prometheus metrics" -ForegroundColor Yellow

    $confirmation = Read-Host "`nType 'GO DEEP CLEAN' to confirm"
    if ($confirmation -ne 'GO DEEP CLEAN') {
        Write-Host "Deep clean cancelled" -ForegroundColor Yellow
        exit 0
    }
}
elseif (-not $Force) {
    Write-Host "`nThis will remove all containers and networks (volumes preserved)" -ForegroundColor Yellow
    $confirmation = Read-Host "Continue? (y/N)"
    if ($confirmation -ne 'y') {
        Write-Host "Clean cancelled" -ForegroundColor Yellow
        exit 0
    }
}

Write-Host ""

# Step 1: Stop and remove containers
Write-Host "[1/4] Stopping containers..." -ForegroundColor Cyan
docker-compose down 2>&1 | Out-Null

$containers = docker ps -a --filter "name=cdb_|claire_de_binare" --format "{{.Names}}"
if ($containers) {
    Write-Host "  Removing $($containers.Count) container(s)..." -ForegroundColor Gray
    $containers | ForEach-Object {
        docker rm -f $_ 2>&1 | Out-Null
        Write-Host "    Removed: $_" -ForegroundColor Gray
    }
    Write-Host "  ✓ Containers removed" -ForegroundColor Green
}
else {
    Write-Host "  ✓ No containers to remove" -ForegroundColor Green
}

# Step 2: Remove networks
Write-Host "`n[2/4] Removing networks..." -ForegroundColor Cyan
$networks = docker network ls --filter "name=claire_de_binare" --format "{{.Name}}"

if ($networks) {
    $networks | ForEach-Object {
        docker network rm $_ 2>&1 | Out-Null
        Write-Host "    Removed: $_" -ForegroundColor Gray
    }
    Write-Host "  ✓ Networks removed" -ForegroundColor Green
}
else {
    Write-Host "  ✓ No networks to remove" -ForegroundColor Green
}

# Step 3: Remove volumes (only if DeepClean)
Write-Host "`n[3/4] Handling volumes..." -ForegroundColor Cyan

if ($DeepClean) {
    $volumes = docker volume ls --filter "name=claire_de_binare_" --format "{{.Name}}"

    if ($volumes) {
        Write-Host "  Removing $($volumes.Count) volume(s)..." -ForegroundColor Red
        $volumes | ForEach-Object {
            docker volume rm $_ 2>&1 | Out-Null
            Write-Host "    Removed: $_" -ForegroundColor Red
        }
        Write-Host "  ✓ Volumes removed (DATA DELETED)" -ForegroundColor Red
    }
    else {
        Write-Host "  ✓ No volumes to remove" -ForegroundColor Green
    }
}
else {
    $volumes = docker volume ls --filter "name=claire_de_binare_" --format "{{.Name}}"

    if ($volumes) {
        Write-Host "  ✓ Preserved $($volumes.Count) volume(s) (data safe)" -ForegroundColor Green
        Write-Host "    Data volumes:" -ForegroundColor Gray
        $volumes | ForEach-Object { Write-Host "      - $_" -ForegroundColor Gray }
    }
    else {
        Write-Host "  ✓ No volumes found" -ForegroundColor Green
    }
}

# Step 4: Cleanup orphaned resources
Write-Host "`n[4/4] Cleaning up orphaned resources..." -ForegroundColor Cyan

# Remove dangling images (if any)
$danglingImages = docker images -f "dangling=true" -q
if ($danglingImages) {
    Write-Host "  Removing dangling images..." -ForegroundColor Gray
    docker rmi $danglingImages 2>&1 | Out-Null
    Write-Host "  ✓ Dangling images removed" -ForegroundColor Green
}
else {
    Write-Host "  ✓ No dangling images" -ForegroundColor Green
}

# Summary
Write-Host "`n=== CLEANUP SUMMARY ===" -ForegroundColor Magenta

if ($DeepClean) {
    Write-Host "✓ Deep clean completed - ALL data removed" -ForegroundColor Red
    Write-Host "`nTo restore from backup:" -ForegroundColor Yellow
    Write-Host "  .\infrastructure\scripts\dr_restore.ps1 -BackupName <backup>" -ForegroundColor White
}
else {
    Write-Host "✓ Safe clean completed - Data volumes preserved" -ForegroundColor Green
    Write-Host "`nTo start fresh stack with existing data:" -ForegroundColor Yellow
    Write-Host "  .\infrastructure\scripts\stack_up.ps1" -ForegroundColor White
}

Write-Host "`nFor deep clean (removes data):" -ForegroundColor Cyan
Write-Host "  .\infrastructure\scripts\stack_clean.ps1 -DeepClean" -ForegroundColor White
