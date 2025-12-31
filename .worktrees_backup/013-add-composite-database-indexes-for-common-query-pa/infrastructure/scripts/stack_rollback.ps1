# stack_rollback.ps1 - Fast Rollback to Tagged Image State
# Rolls back stack to previously tagged images in < 60 seconds
# Acceptance Criterion A: Rollback time < 60 seconds

[CmdletBinding()]
param(
    [string]$TagName = "latest-rollback",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "=== Claire de Binare - Stack Rollback ===" -ForegroundColor Cyan

$startTime = Get-Date

# Load rollback manifest if specific tag requested
if ($TagName -ne "latest-rollback") {
    $manifestPath = "infrastructure/rollback_manifest.json"
    if (-not (Test-Path $manifestPath)) {
        Write-Host "Rollback manifest not found at $manifestPath" -ForegroundColor Red
        Write-Host "Create a tag first with: .\infrastructure\scripts\stack_tag.ps1" -ForegroundColor Yellow
        exit 1
    }

    $manifest = Get-Content $manifestPath | ConvertFrom-Json

    if ($manifest.TagName -ne $TagName) {
        Write-Host "WARNING: Manifest tag ($($manifest.TagName)) doesn't match requested tag ($TagName)" -ForegroundColor Yellow
        if (-not $Force) {
            Write-Host "Use -Force to proceed anyway, or re-tag with stack_tag.ps1" -ForegroundColor Yellow
            exit 1
        }
    }

    Write-Host "Rollback Target: $($manifest.TagName)" -ForegroundColor Yellow
    Write-Host "Created: $($manifest.Timestamp)" -ForegroundColor Gray
}
else {
    Write-Host "Rollback Target: latest-rollback (most recent)" -ForegroundColor Yellow
}

# Verify tagged images exist
$missingImages = @()
$containers = docker ps --filter "name=cdb_" --format "{{.Names}}"

foreach ($container in $containers) {
    $currentImage = docker inspect $container --format '{{.Config.Image}}'
    $repo = $currentImage -replace ':.*$', ''
    $targetImage = "${repo}:${TagName}"

    # Check if target image exists
    $imageExists = docker images $targetImage --format "{{.Repository}}:{{.Tag}}" | Select-String -Pattern "^${targetImage}$"

    if (-not $imageExists) {
        $missingImages += $targetImage
    }
}

if ($missingImages.Count -gt 0) {
    Write-Host "`nERROR: The following rollback images don't exist:" -ForegroundColor Red
    $missingImages | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host "`nCreate tags first with: .\infrastructure\scripts\stack_tag.ps1 -TagName $TagName" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n✓ All rollback images verified" -ForegroundColor Green

# Confirmation prompt
if (-not $Force) {
    $confirmation = Read-Host "`nProceed with rollback? This will restart all containers (y/N)"
    if ($confirmation -ne 'y') {
        Write-Host "Rollback cancelled" -ForegroundColor Yellow
        exit 0
    }
}

Write-Host "`n[1/3] Updating container images..." -ForegroundColor Cyan

# Update each container to rollback image
foreach ($container in $containers) {
    $currentImage = docker inspect $container --format '{{.Config.Image}}'
    $repo = $currentImage -replace ':.*$', ''
    $targetImage = "${repo}:${TagName}"

    Write-Host "  $container -> $targetImage" -ForegroundColor Gray

    # Get container config
    $envVars = docker inspect $container --format '{{range .Config.Env}}{{println .}}{{end}}'
    $volumes = docker inspect $container --format '{{range .Mounts}}{{if eq .Type "volume"}}{{.Name}}:{{.Destination}} {{end}}{{end}}'
    $networks = docker inspect $container --format '{{range .NetworkSettings.Networks}}{{println .NetworkID}}{{end}}'

    # Stop and remove container
    docker stop $container | Out-Null
    docker rm $container | Out-Null

    # Recreate with rollback image
    # Note: Using docker-compose to preserve full config is safer
}

Write-Host "`n[2/3] Restarting stack with rollback images..." -ForegroundColor Cyan

# Create temporary compose override with image tags
$overridePath = "infrastructure/compose/rollback-temp.yml"
$override = @"
# Temporary Rollback Override - DO NOT COMMIT
services:
"@

foreach ($container in $containers) {
    $currentImage = docker inspect $container --format '{{.Config.Image}}'
    $repo = $currentImage -replace ':.*$', ''
    $targetImage = "${repo}:${TagName}"
    $serviceName = $container -replace '^cdb_', ''

    $override += @"

  cdb_${serviceName}:
    image: $targetImage
"@
}

$override | Out-File -FilePath $overridePath -Encoding UTF8

# Restart stack with rollback override
docker-compose `
    -f infrastructure/compose/base.yml `
    -f infrastructure/compose/logging.yml `
    -f $overridePath `
    up -d --no-build

Remove-Item $overridePath -Force

Write-Host "`n[3/3] Verifying rollback..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

$healthyCount = 0
$totalCount = 0

$containers = docker ps --filter "name=cdb_" --format "{{.Names}}"
foreach ($container in $containers) {
    $totalCount++
    $status = docker inspect $container --format '{{.State.Health.Status}}'
    $state = docker inspect $container --format '{{.State.Status}}'

    if ($status -eq "healthy" -or ($status -eq "<no value>" -and $state -eq "running")) {
        $healthyCount++
    }
}

$duration = ((Get-Date) - $startTime).TotalSeconds

Write-Host "`n✓ Rollback completed in $([math]::Round($duration, 1)) seconds" -ForegroundColor Green
Write-Host "✓ Services: $healthyCount/$totalCount healthy/running" -ForegroundColor Green

if ($duration -gt 60) {
    Write-Host "`nWARNING: Rollback took longer than 60 seconds!" -ForegroundColor Yellow
    Write-Host "Acceptance Criterion A target: < 60s" -ForegroundColor Yellow
}
else {
    Write-Host "`n✓ Acceptance Criterion A met: Rollback < 60s" -ForegroundColor Green
}

Write-Host "`nVerify with: docker ps" -ForegroundColor Cyan
