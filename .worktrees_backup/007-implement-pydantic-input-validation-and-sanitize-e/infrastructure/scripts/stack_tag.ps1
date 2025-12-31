# stack_tag.ps1 - Tag Current Docker Images for Rollback
# Creates timestamped tags of all running containers for fast rollback
# Acceptance Criterion A: Enable rollback < 60 seconds

[CmdletBinding()]
param(
    [string]$TagName = "",
    [switch]$Latest
)

$ErrorActionPreference = "Stop"

Write-Host "=== Claire de Binare - Stack Image Tagging ===" -ForegroundColor Cyan

# Generate tag name if not provided
if (-not $TagName) {
    $TagName = "rollback-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
}

Write-Host "Tag Name: $TagName" -ForegroundColor Yellow

# Get list of all running Claire de Binare containers
$containers = docker ps --filter "name=cdb_" --format "{{.Names}}"

if (-not $containers) {
    Write-Host "No running CdB containers found. Start the stack first." -ForegroundColor Red
    exit 1
}

$taggedImages = @()

# Tag each container's image
foreach ($container in $containers) {
    $imageId = docker inspect $container --format '{{.Image}}'
    $imageName = docker inspect $imageId --format '{{index .RepoTags 0}}'

    if (-not $imageName -or $imageName -eq "<none>:<none>") {
        # Handle built images without tags
        $imageName = docker inspect $container --format '{{.Config.Image}}'
    }

    # Extract repo name without tag
    $repo = $imageName -replace ':.*$', ''

    # Create new tag
    $newTag = "${repo}:${TagName}"

    Write-Host "  Tagging: $imageName -> $newTag" -ForegroundColor Gray
    docker tag $imageId $newTag

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to tag image for $container" -ForegroundColor Red
        continue
    }

    $taggedImages += @{
        Container = $container
        OriginalImage = $imageName
        TaggedImage = $newTag
    }
}

# Also tag with 'latest-rollback' if requested
if ($Latest) {
    Write-Host "`nTagging as 'latest-rollback'..." -ForegroundColor Cyan
    foreach ($item in $taggedImages) {
        $repo = $item.TaggedImage -replace ':.*$', ''
        $latestTag = "${repo}:latest-rollback"
        $imageId = docker inspect $item.TaggedImage --format '{{.Id}}'
        docker tag $imageId $latestTag
    }
}

# Save rollback manifest
$manifestPath = "infrastructure/rollback_manifest.json"
$manifest = @{
    TagName = $TagName
    Timestamp = (Get-Date -Format 'o')
    Images = $taggedImages
} | ConvertTo-Json -Depth 10

$manifest | Out-File -FilePath $manifestPath -Encoding UTF8

Write-Host "`n✓ Successfully tagged $($taggedImages.Count) images" -ForegroundColor Green
Write-Host "✓ Rollback manifest saved to: $manifestPath" -ForegroundColor Green
Write-Host "`nRollback with:" -ForegroundColor Yellow
Write-Host "  .\infrastructure\scripts\stack_rollback.ps1 -TagName $TagName" -ForegroundColor White
