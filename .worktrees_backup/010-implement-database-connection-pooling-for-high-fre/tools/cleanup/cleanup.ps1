<#
.SYNOPSIS
    Safe Docker Cleanup Script for Claire de Binare (Issue #282)

.DESCRIPTION
    Cleans up Docker resources with strict guardrails:
    - NEVER auto-deletes named volumes
    - Dry-run by default
    - Shows what will be cleaned before execution

.PARAMETER Execute
    Actually perform cleanup (default: dry-run only)

.PARAMETER BuildCache
    Include build cache cleanup

.PARAMETER DanglingImages
    Include dangling images cleanup

.EXAMPLE
    .\cleanup.ps1                    # Dry-run, show what would be cleaned
    .\cleanup.ps1 -Execute           # Actually clean
    .\cleanup.ps1 -Execute -BuildCache  # Clean + build cache
#>

param(
    [switch]$Execute,
    [switch]$BuildCache,
    [switch]$DanglingImages
)

$ErrorActionPreference = "Stop"

# Protected volumes (NEVER delete these)
$ProtectedVolumes = @(
    "claire_redis_data",
    "claire_postgres_data",
    "claire_prom_data",
    "claire_grafana_data",
    "cdb_redis_data",
    "cdb_postgres_data",
    "cdb_prom_data",
    "cdb_grafana_data"
)

Write-Host "`n=== Claire de Binare - Safe Cleanup ===" -ForegroundColor Cyan
Write-Host "Mode: $(if ($Execute) { 'EXECUTE' } else { 'DRY-RUN' })`n"

# 1. Show current disk usage
Write-Host "=== Current Docker Disk Usage ===" -ForegroundColor Yellow
docker system df

# 2. List named volumes (protected)
Write-Host "`n=== Protected Named Volumes (NEVER deleted) ===" -ForegroundColor Green
$volumes = docker volume ls --format "{{.Name}}"
foreach ($vol in $volumes) {
    if ($ProtectedVolumes -contains $vol) {
        Write-Host "  [PROTECTED] $vol" -ForegroundColor Green
    } else {
        Write-Host "  [UNPROTECTED] $vol" -ForegroundColor Yellow
    }
}

# 3. Identify cleanup targets
Write-Host "`n=== Cleanup Targets ===" -ForegroundColor Yellow

# Stopped containers
$stoppedContainers = docker ps -a --filter "status=exited" --format "{{.Names}}" | Measure-Object
Write-Host "  Stopped containers: $($stoppedContainers.Count)"

# Dangling images
$danglingImages = docker images --filter "dangling=true" -q | Measure-Object
Write-Host "  Dangling images: $($danglingImages.Count)"

# Build cache
if ($BuildCache) {
    Write-Host "  Build cache: Will be pruned"
}

# 4. Execute or dry-run
if ($Execute) {
    Write-Host "`n=== Executing Cleanup ===" -ForegroundColor Red

    # Remove stopped containers
    Write-Host "Removing stopped containers..."
    docker container prune -f

    # Remove dangling images (if flag set)
    if ($DanglingImages) {
        Write-Host "Removing dangling images..."
        docker image prune -f
    }

    # Remove build cache (if flag set)
    if ($BuildCache) {
        Write-Host "Removing build cache..."
        docker builder prune -f
    }

    # Remove dangling volumes (but NOT named volumes)
    Write-Host "Removing dangling volumes (unnamed only)..."
    docker volume prune -f

    Write-Host "`n=== Cleanup Complete ===" -ForegroundColor Green
    docker system df
} else {
    Write-Host "`n=== DRY-RUN Mode ===" -ForegroundColor Yellow
    Write-Host "No changes made. Use -Execute to actually clean."
    Write-Host "`nCommands that would run:"
    Write-Host "  docker container prune -f"
    if ($DanglingImages) {
        Write-Host "  docker image prune -f"
    }
    if ($BuildCache) {
        Write-Host "  docker builder prune -f"
    }
    Write-Host "  docker volume prune -f"
}

Write-Host "`n=== Guardrails ===" -ForegroundColor Cyan
Write-Host "- Named volumes are NEVER deleted automatically"
Write-Host "- Use 'docker volume rm <name>' manually if needed"
Write-Host "- Always backup before manual volume deletion"
