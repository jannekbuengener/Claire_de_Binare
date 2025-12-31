# stack_doctor.ps1 - Stack Health & Drift Detection
# Detects configuration drift, orphaned resources, port conflicts
# Acceptance Criterion G: Confusion-proofing (drift detection)

[CmdletBinding()]
param(
    [switch]$Fix,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

Write-Host "=== Claire de Binare - Stack Doctor ===" -ForegroundColor Cyan
Write-Host "Scanning for configuration drift and issues...`n" -ForegroundColor Yellow

$issues = @()
$warnings = @()

# Check 1: Orphaned containers
Write-Host "[1/8] Checking for orphaned containers..." -ForegroundColor Cyan
$allContainers = docker ps -a --format "{{.Names}}"
# Active services (as of 2025-12-24)
# Disabled: cdb_allocation, cdb_regime (missing env vars), cdb_market (not implemented), cdb_ws (no Dockerfile), cdb_paper_runner (not implemented)
$expectedContainers = @("cdb_redis", "cdb_postgres", "cdb_prometheus", "cdb_grafana", "cdb_core", "cdb_db_writer", "cdb_risk", "cdb_execution")

# Exclude loki/promtail (optional logging services) and known disabled services
$orphaned = $allContainers | Where-Object {
    $_ -match "^cdb_|claire_de_binare" -and
    $_ -notin $expectedContainers -and
    $_ -notmatch "^claire_de_binare-cdb_(loki|promtail)" -and
    $_ -notmatch "^cdb_(allocation|regime|market|ws|paper_runner)"
}

if ($orphaned) {
    $issues += "Orphaned containers found: $($orphaned -join ', ')"
    Write-Host "  ✗ Found $($orphaned.Count) orphaned container(s)" -ForegroundColor Red
    if ($Verbose) {
        $orphaned | ForEach-Object { Write-Host "    - $_" -ForegroundColor Gray }
    }

    if ($Fix) {
        Write-Host "  [FIX] Removing orphaned containers..." -ForegroundColor Yellow
        $orphaned | ForEach-Object { docker rm -f $_ | Out-Null }
        Write-Host "  ✓ Orphaned containers removed" -ForegroundColor Green
    }
}
else {
    Write-Host "  ✓ No orphaned containers" -ForegroundColor Green
}

# Check 2: Orphaned volumes
Write-Host "`n[2/8] Checking for orphaned volumes..." -ForegroundColor Cyan
$allVolumes = docker volume ls --filter "name=claire_de_binare_" --format "{{.Name}}"
$expectedVolumes = @("claire_de_binare_redis_data", "claire_de_binare_postgres_data", "claire_de_binare_prom_data", "claire_de_binare_grafana_data", "claire_de_binare_loki_data")

$orphanedVolumes = $allVolumes | Where-Object { $_ -notin $expectedVolumes }

if ($orphanedVolumes) {
    $warnings += "Orphaned volumes found: $($orphanedVolumes -join ', ')"
    Write-Host "  ⚠ Found $($orphanedVolumes.Count) orphaned volume(s)" -ForegroundColor Yellow
    if ($Verbose) {
        $orphanedVolumes | ForEach-Object { Write-Host "    - $_" -ForegroundColor Gray }
    }

    if ($Fix) {
        Write-Host "  [SKIP] Orphaned volumes NOT removed (data safety)" -ForegroundColor Yellow
        Write-Host "  [INFO] Use stack_clean.ps1 -DeepClean to remove" -ForegroundColor Gray
    }
}
else {
    Write-Host "  ✓ No orphaned volumes" -ForegroundColor Green
}

# Check 3: Port conflicts
Write-Host "`n[3/8] Checking for port conflicts..." -ForegroundColor Cyan
# Infrastructure: Redis (6379), Postgres (5432), Prometheus (19090), Grafana (3000)
# Logging (optional): Loki (3100)
# Applications: cdb_core (8001), cdb_risk (8002), cdb_execution (8003)
# Note: Port 8000 removed (cdb_ws disabled, no root Dockerfile)
$expectedPorts = @(6379, 5432, 19090, 3000, 3100, 8001, 8002, 8003)
$listening = netstat -an | Select-String "LISTENING|LISTEN"

$conflicts = @()
foreach ($port in $expectedPorts) {
    $inUse = $listening | Select-String ":$port\s"
    if ($inUse) {
        # Check if it's our container
        $ourContainer = docker ps --format "{{.Names}}" | Where-Object {
            $ports = docker port $_ 2>$null
            $ports -match ":$port->"
        }

        if (-not $ourContainer) {
            $conflicts += $port
        }
    }
}

if ($conflicts) {
    $issues += "Port conflicts detected: $($conflicts -join ', ')"
    Write-Host "  ✗ Found $($conflicts.Count) port conflict(s)" -ForegroundColor Red
    if ($Verbose) {
        $conflicts | ForEach-Object { Write-Host "    - Port $_" -ForegroundColor Gray }
    }
}
else {
    Write-Host "  ✓ No port conflicts" -ForegroundColor Green
}

# Check 4: Secret file integrity
Write-Host "`n[4/8] Checking secret files..." -ForegroundColor Cyan
$secretPath = "..\.cdb_local\.secrets"
$requiredSecrets = @("redis_password", "postgres_password")

$missingSecrets = @()
$emptySecrets = @()

foreach ($secret in $requiredSecrets) {
    $filePath = "$secretPath\$secret"
    if (-not (Test-Path $filePath)) {
        $missingSecrets += $secret
    }
    elseif ((Get-Item $filePath).PSIsContainer) {
        $issues += "Secret '$secret' is a directory, not a file"
        Write-Host "  ✗ $secret is a DIRECTORY (should be FILE)" -ForegroundColor Red
    }
    elseif ((Get-Item $filePath).Length -eq 0) {
        $emptySecrets += $secret
    }
}

if ($missingSecrets) {
    $issues += "Missing secrets: $($missingSecrets -join ', ')"
    Write-Host "  ✗ Missing secret files" -ForegroundColor Red
}

if ($emptySecrets) {
    $warnings += "Empty secrets: $($emptySecrets -join ', ')"
    Write-Host "  ⚠ Empty secret files (OK if DB already initialized)" -ForegroundColor Yellow
}

if (-not $missingSecrets -and -not $emptySecrets) {
    Write-Host "  ✓ All secret files valid" -ForegroundColor Green
}

# Check 5: Environment variable conflicts
Write-Host "`n[5/8] Checking for environment variable conflicts..." -ForegroundColor Cyan
$forbiddenEnvVars = @("POSTGRES_PASSWORD", "REDIS_PASSWORD")

$envConflicts = @()
foreach ($var in $forbiddenEnvVars) {
    if ([Environment]::GetEnvironmentVariable($var, "User")) {
        $envConflicts += $var
    }
}

if ($envConflicts) {
    $issues += "Forbidden environment variables set: $($envConflicts -join ', ')"
    Write-Host "  ✗ Plaintext password env vars detected (policy violation)" -ForegroundColor Red
    if ($Verbose) {
        $envConflicts | ForEach-Object { Write-Host "    - $_" -ForegroundColor Gray }
    }
}
else {
    Write-Host "  ✓ No plaintext password env vars" -ForegroundColor Green
}

# Check 6: Docker network integrity
Write-Host "`n[6/8] Checking Docker network..." -ForegroundColor Cyan
$network = docker network ls --filter "name=claire_de_binare_cdb_network" --format "{{.Name}}"

if ($network) {
    $networkDetails = docker network inspect $network | ConvertFrom-Json
    $connectedContainers = $networkDetails.Containers.PSObject.Properties | Measure-Object | Select-Object -ExpandProperty Count

    Write-Host "  ✓ Network exists with $connectedContainers container(s)" -ForegroundColor Green
}
else {
    $warnings += "Docker network not found (stack probably down)"
    Write-Host "  ⚠ Docker network not found" -ForegroundColor Yellow
}

# Check 7: Compose file consistency
Write-Host "`n[7/8] Checking compose file paths..." -ForegroundColor Cyan
$composeFiles = @(
    "infrastructure/compose/base.yml",
    "infrastructure/compose/dev.yml",
    "infrastructure/compose/logging.yml",
    "infrastructure/compose/network-prod.yml",
    "infrastructure/compose/rollback.yml",
    "infrastructure/compose/healthchecks-mounts.yml",
    "infrastructure/compose/healthchecks-strict.yml"
)

$missingComposeFiles = @()
foreach ($file in $composeFiles) {
    if (-not (Test-Path $file)) {
        $missingComposeFiles += $file
    }
}

if ($missingComposeFiles) {
    $issues += "Missing compose files: $($missingComposeFiles -join ', ')"
    Write-Host "  ✗ Missing $($missingComposeFiles.Count) compose file(s)" -ForegroundColor Red
}
else {
    Write-Host "  ✓ All compose files present" -ForegroundColor Green
}

# Check 8: Service configuration readiness
Write-Host "`n[8/9] Checking service configuration..." -ForegroundColor Cyan
$devYml = "infrastructure/compose/dev.yml"

if (Test-Path $devYml) {
    $devContent = Get-Content $devYml -Raw

    # Check if disabled services have proper TODO comments
    $disabledServices = @("cdb_allocation", "cdb_regime", "cdb_market", "cdb_ws")
    $configIssues = @()

    foreach ($svc in $disabledServices) {
        if ($devContent -match "# .* $svc") {
            # Service is commented out with explanation - good
        } elseif ($devContent -match "^\s+$svc:" -and $devContent -notmatch "$svc.*# DISABLED") {
            $configIssues += "$svc enabled but may have missing dependencies"
        }
    }

    # Check for hardcoded passwords (dev only - warning not error)
    if ($devContent -match "REDIS_PASSWORD:\s*[^$]") {
        $warnings += "REDIS_PASSWORD hardcoded in dev.yml (OK for dev, but refactor for prod)"
    }

    if ($configIssues.Count -gt 0) {
        Write-Host "  ⚠ Configuration issues found" -ForegroundColor Yellow
        $configIssues | ForEach-Object { $warnings += $_ }
    } else {
        Write-Host "  ✓ Service configuration looks good" -ForegroundColor Green
    }
} else {
    $issues += "dev.yml not found"
    Write-Host "  ✗ dev.yml missing" -ForegroundColor Red
}

# Check 9: Running container health
Write-Host "`n[9/9] Checking container health..." -ForegroundColor Cyan
$running = docker ps --filter "name=cdb_" --format "{{.Names}}"

if ($running) {
    $healthy = 0
    $unhealthy = 0
    $noHealth = 0

    foreach ($container in $running) {
        $health = docker inspect $container --format '{{.State.Health.Status}}' 2>$null
        $state = docker inspect $container --format '{{.State.Status}}'

        if ($health -eq "healthy") {
            $healthy++
        }
        elseif ($health -eq "unhealthy") {
            $unhealthy++
            $warnings += "Container $container is unhealthy"
        }
        elseif ($state -eq "running") {
            $noHealth++
        }
    }

    Write-Host "  ✓ Healthy: $healthy | Running: $noHealth | Unhealthy: $unhealthy" -ForegroundColor $(if ($unhealthy -gt 0) { 'Yellow' } else { 'Green' })
}
else {
    Write-Host "  ⚠ No containers running" -ForegroundColor Yellow
}

# Summary
Write-Host "`n=== DIAGNOSIS SUMMARY ===" -ForegroundColor Magenta

if ($issues.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "✓ Stack is healthy - no issues detected" -ForegroundColor Green
    exit 0
}

if ($issues.Count -gt 0) {
    Write-Host "`nISSUES ($($issues.Count)):" -ForegroundColor Red
    $issues | ForEach-Object { Write-Host "  ✗ $_" -ForegroundColor Red }
}

if ($warnings.Count -gt 0) {
    Write-Host "`nWARNINGS ($($warnings.Count)):" -ForegroundColor Yellow
    $warnings | ForEach-Object { Write-Host "  ⚠ $_" -ForegroundColor Yellow }
}

if ($issues.Count -gt 0) {
    Write-Host "`nRun with -Fix to auto-repair some issues" -ForegroundColor Cyan
    exit 1
}
else {
    Write-Host "`nNo critical issues, only warnings" -ForegroundColor Yellow
    exit 0
}
