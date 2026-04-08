# Verification Script - Check if restore was successful
#
# ⚠️  HISTORISCHES ARTEFAKT — 2025-12-31-Docker-Reinstall-Event
# Nicht aktiver Operator-Canon. Aktiver Canon: manuelle Postgres/Redis-Checks nach make restore
# Hardcoded auf alten Volume-Set + host-spezifische Pfade (C:\Users\janne\..., D:\Dev\...)

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
$envPath = "D:\Dev\Workspaces\Repos\Claire_de_Binare\.env"
if (Test-Path $envPath) {
    $size = (Get-Item $envPath).Length
    Write-Host "  ✅ .env exists ($size bytes)" -ForegroundColor Green
} else {
    Write-Host "  ❌ .env MISSING" -ForegroundColor Red
}
Write-Host ""

# Check secrets
Write-Host "4. Secrets:" -ForegroundColor Cyan
$secretsPath = "C:\Users\janne\Documents\.secrets\.cdb"
if (Test-Path $secretsPath) {
    $count = (Get-ChildItem $secretsPath -File).Count
    Write-Host "  ✅ Secrets directory exists ($count files)" -ForegroundColor Green
} else {
    Write-Host "  ❌ Secrets directory MISSING" -ForegroundColor Red
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
Write-Host "  cd D:\Dev\Workspaces\Repos\Claire_de_Binare"
Write-Host "  make docker-up"
Write-Host ""
Write-Host "Then check:" -ForegroundColor Cyan
Write-Host "  Grafana: http://localhost:3000"
Write-Host "  Logs:    docker compose logs -f"
Write-Host ""
