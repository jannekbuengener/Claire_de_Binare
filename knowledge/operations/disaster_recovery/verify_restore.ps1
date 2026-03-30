# Verification Script - Check if restore was successful
#
# Usage:
#   .\verify_restore.ps1
#   .\verify_restore.ps1 -RepoDir "C:\Projects\Claire_de_Binare" -SecretsPath "D:\secrets\.cdb"

param(
    [string]$RepoDir = (git -C $PSScriptRoot rev-parse --show-toplevel 2>$null),
    [string]$SecretsPath = $env:SECRETS_PATH
)

if (-not $RepoDir) {
    Write-Host "ERROR: Could not detect repo root. Pass -RepoDir explicitly." -ForegroundColor Red
    exit 1
}

if (-not $SecretsPath) {
    Write-Host "WARNING: No secrets path configured. Set `$env:SECRETS_PATH or pass -SecretsPath." -ForegroundColor Yellow
}

Write-Host "=== Docker Restore Verification ===" -ForegroundColor Green
Write-Host ""

# Check Docker
Write-Host "1. Docker Installation:" -ForegroundColor Cyan
docker --version
docker compose version
Write-Host ""

# Check Volumes
Write-Host "2. Volumes:" -ForegroundColor Cyan
$volumes = @(
    "claire_de_binare_redis_data",
    "claire_de_binare_grafana_data",
    "claire_de_binare_postgres_data",
    "claire_de_binare_prom_data",
    "claire_de_binare_loki_data",
    "claude-memory"
)

foreach ($vol in $volumes) {
    $exists = docker volume ls --format "{{.Name}}" | Select-String -Pattern "^$vol$"
    if ($exists) {
        Write-Host "  ✅ $vol" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $vol MISSING" -ForegroundColor Red
    }
}
Write-Host ""

# Check .env file
Write-Host "3. Configuration Files:" -ForegroundColor Cyan
$envPath = Join-Path $RepoDir ".env"
if (Test-Path $envPath) {
    $size = (Get-Item $envPath).Length
    Write-Host "  ✅ .env exists ($size bytes)" -ForegroundColor Green
} else {
    Write-Host "  ❌ .env MISSING" -ForegroundColor Red
}
Write-Host ""

# Check secrets
Write-Host "4. Secrets:" -ForegroundColor Cyan
if ($SecretsPath) {
    if (Test-Path $SecretsPath) {
        $count = (Get-ChildItem $SecretsPath -File).Count
        Write-Host "  ✅ Secrets directory exists ($count files)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Secrets directory MISSING at $SecretsPath" -ForegroundColor Red
    }
} else {
    Write-Host "  ⚠️  Secrets path not configured — skipping check" -ForegroundColor Yellow
}
Write-Host ""

# Check containers (if stack is running)
Write-Host "5. Containers:" -ForegroundColor Cyan
$containers = docker ps --format "{{.Names}}" 2>$null
if ($containers) {
    $containers | ForEach-Object {
        $health = docker inspect $_ --format "{{.State.Health.Status}}" 2>$null
        if ($health -eq "healthy") {
            Write-Host "  ✅ $_" -ForegroundColor Green
        } elseif ($health -eq "") {
            Write-Host "  🟡 $_ (no healthcheck)" -ForegroundColor Yellow
        } else {
            Write-Host "  ⚠️  $_ ($health)" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  ℹ️  No containers running (run 'make docker-up' first)" -ForegroundColor Cyan
}
Write-Host ""

Write-Host "=== Verification Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "If stack is not running yet:" -ForegroundColor Cyan
Write-Host "  cd $RepoDir"
Write-Host "  make docker-up"
Write-Host ""
Write-Host "Then check:" -ForegroundColor Cyan
Write-Host "  Grafana: http://localhost:3000"
Write-Host "  Logs:    docker compose logs -f"
Write-Host ""
