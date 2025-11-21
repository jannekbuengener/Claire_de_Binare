# systemcheck.ps1 - System Health Check for Claire de Binaire
# Purpose: Comprehensive Docker, Service, and Database health validation
#
# Usage:
#   .\systemcheck.ps1                 # Full system check
#   .\systemcheck.ps1 -Quick          # Quick check (skip optional tests)
#   .\systemcheck.ps1 -UpdateDocs     # Update PROJECT_STATUS.md with results
#
# Exit Codes:
#   0: All checks passed
#   1: Critical failures detected
#   2: Warnings present (non-critical)

param(
    [switch]$Quick = $false,
    [switch]$UpdateDocs = $false
)

# ANSI Colors
$RED = "`e[31m"
$GREEN = "`e[32m"
$YELLOW = "`e[33m"
$BLUE = "`e[34m"
$MAGENTA = "`e[35m"
$RESET = "`e[0m"

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = (Get-Item "$ScriptDir\..\..").FullName
$EnvFile = "$RootDir\.env"

# Counters
$ChecksPassed = 0
$ChecksFailed = 0
$ChecksWarned = 0
$CriticalFailures = 0

# Results storage
$ContainerStatus = @{}
$ContainerHealth = @{}

# Expected services configuration
$ExpectedServices = @{
    "cdb_redis" = 6379
    "cdb_postgres" = 5432
    "cdb_ws" = 8000
    "cdb_core" = 8001
    "cdb_risk" = 8002
    "cdb_execution" = 8003
    "cdb_prometheus" = 19090
    "cdb_grafana" = 3000
}

# Services with health endpoints
$HealthServices = @{
    "cdb_ws" = 8000
    "cdb_core" = 8001
    "cdb_risk" = 8002
    "cdb_execution" = 8003
}

Write-Host "${BLUE}╔══════════════════════════════════════════════════════════╗${RESET}"
Write-Host "${BLUE}║  System Health Check - Claire de Binaire                ║${RESET}"
Write-Host "${BLUE}╚══════════════════════════════════════════════════════════╝${RESET}"
Write-Host ""
Write-Host "${MAGENTA}Timestamp:${RESET} $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "${MAGENTA}Mode:${RESET} $(if ($Quick) { 'Quick Check' } else { 'Full Check' })"
Write-Host ""

# Helper function for status output
function Print-Status {
    param(
        [string]$Status,
        [string]$Message
    )

    switch ($Status) {
        "OK" {
            Write-Host "${GREEN}[✓ OK]${RESET} $Message"
            $script:ChecksPassed++
        }
        "FAIL" {
            Write-Host "${RED}[✗ FAIL]${RESET} $Message"
            $script:ChecksFailed++
            $script:CriticalFailures++
        }
        "WARN" {
            Write-Host "${YELLOW}[⚠ WARN]${RESET} $Message"
            $script:ChecksWarned++
        }
        "INFO" {
            Write-Host "${BLUE}[ℹ INFO]${RESET} $Message"
        }
    }
}

# 1. Check Prerequisites
Write-Host "${BLUE}━━━ Prerequisites ━━━${RESET}"

# Check if Docker is installed
try {
    $DockerVersion = (docker --version) -replace '.*version ([^,]+).*','$1'
    Print-Status "OK" "Docker installed (version $DockerVersion)"
} catch {
    Print-Status "FAIL" "Docker not installed"
    exit 1
}

# Check if Docker daemon is running
try {
    docker info | Out-Null
    Print-Status "OK" "Docker daemon is running"
} catch {
    Print-Status "FAIL" "Docker daemon is not running"
    exit 1
}

# Check if docker compose is available
try {
    $ComposeVersion = docker compose version --short
    Print-Status "OK" "Docker Compose available (v$ComposeVersion)"
} catch {
    Print-Status "FAIL" "Docker Compose not available"
    exit 1
}

# Check if .env file exists
if (Test-Path $EnvFile) {
    Print-Status "OK" ".env file found"
} else {
    Print-Status "WARN" ".env file not found (using defaults)"
}

Write-Host ""

# 2. Check Container Status
Write-Host "${BLUE}━━━ Container Status ━━━${RESET}"

# Get container status
Push-Location $RootDir
try {
    $ComposePsOutput = docker compose ps --format json 2>$null | ConvertFrom-Json -ErrorAction SilentlyContinue

    if (-not $ComposePsOutput) {
        Print-Status "WARN" "No containers found (docker compose ps returned empty)"
        foreach ($service in $ExpectedServices.Keys) {
            $ContainerStatus[$service] = "not_running"
            $ContainerHealth[$service] = "n/a"
        }
    } else {
        foreach ($container in $ComposePsOutput) {
            $service = $container.Service
            $state = $container.State
            $health = if ($container.Health) { $container.Health } else { "n/a" }

            $ContainerStatus[$service] = $state
            $ContainerHealth[$service] = $health

            if ($state -eq "running") {
                if ($health -eq "healthy" -or $health -eq "n/a") {
                    $healthStr = if ($health -ne "n/a") { "($health)" } else { "" }
                    Print-Status "OK" "$service`: $state $healthStr"
                } else {
                    Print-Status "WARN" "$service`: $state ($health)"
                }
            } else {
                Print-Status "FAIL" "$service`: $state"
            }
        }
    }
} catch {
    Print-Status "WARN" "Failed to parse docker compose ps output: $_"
}
Pop-Location

# Check for missing services
foreach ($service in $ExpectedServices.Keys) {
    if (-not $ContainerStatus.ContainsKey($service)) {
        Print-Status "WARN" "$service`: not found in docker compose ps"
        $ContainerStatus[$service] = "not_found"
        $ContainerHealth[$service] = "n/a"
    }
}

Write-Host ""

# 3. Check Health Endpoints
Write-Host "${BLUE}━━━ Health Endpoints ━━━${RESET}"

foreach ($service in $HealthServices.Keys) {
    $port = $HealthServices[$service]
    $healthUrl = "http://localhost:$port/health"

    if ($ContainerStatus[$service] -ne "running") {
        Print-Status "WARN" "$service /health - skipped (container not running)"
        continue
    }

    # Test health endpoint
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop

        if ($response.StatusCode -eq 200) {
            $content = $response.Content
            if ($content -match "ok|healthy") {
                Print-Status "OK" "$service /health → 200 OK"
            } else {
                Print-Status "WARN" "$service /health → unexpected response"
            }
        } else {
            Print-Status "FAIL" "$service /health → HTTP $($response.StatusCode)"
        }
    } catch {
        Print-Status "FAIL" "$service /health → connection failed"
    }
}

Write-Host ""

# 4. Check Database Connectivity
if (-not $Quick) {
    Write-Host "${BLUE}━━━ Database Connectivity ━━━${RESET}"

    # Load .env if exists
    if (Test-Path $EnvFile) {
        Get-Content $EnvFile | Where-Object { $_ -match '^\s*[^#]' } | ForEach-Object {
            if ($_ -match '^([^=]+)=(.*)$') {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()
                Set-Variable -Name $key -Value $value -Scope Script
            }
        }
    }

    # PostgreSQL
    if ($ContainerStatus["cdb_postgres"] -eq "running") {
        $pgHost = if ($script:POSTGRES_HOST) { $script:POSTGRES_HOST } else { "localhost" }
        $pgPort = if ($script:POSTGRES_PORT) { $script:POSTGRES_PORT } else { "5432" }
        $pgUser = if ($script:POSTGRES_USER) { $script:POSTGRES_USER } else { "claire_user" }
        $pgDb = if ($script:POSTGRES_DB) { $script:POSTGRES_DB } else { "claire_de_binare" }
        $pgPassword = if ($script:POSTGRES_PASSWORD) { $script:POSTGRES_PASSWORD } else { "" }

        if (Get-Command psql -ErrorAction SilentlyContinue) {
            try {
                $env:PGPASSWORD = $pgPassword
                $result = psql -h $pgHost -p $pgPort -U $pgUser -d $pgDb -c "SELECT 1" 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Print-Status "OK" "PostgreSQL: Connection successful"
                } else {
                    Print-Status "FAIL" "PostgreSQL: Connection failed"
                }
            } catch {
                Print-Status "FAIL" "PostgreSQL: Connection failed - $_"
            } finally {
                Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
            }
        } else {
            Print-Status "WARN" "psql not installed - skipping PostgreSQL test"
        }
    } else {
        Print-Status "WARN" "PostgreSQL container not running - skipping"
    }

    # Redis
    if ($ContainerStatus["cdb_redis"] -eq "running") {
        $redisHost = if ($script:REDIS_HOST) { $script:REDIS_HOST } else { "localhost" }
        $redisPort = if ($script:REDIS_PORT) { $script:REDIS_PORT } else { "6379" }

        if (Get-Command redis-cli -ErrorAction SilentlyContinue) {
            try {
                $result = redis-cli -h $redisHost -p $redisPort PING 2>&1
                if ($result -match "PONG") {
                    Print-Status "OK" "Redis: PING successful"
                } else {
                    Print-Status "FAIL" "Redis: PING failed"
                }
            } catch {
                Print-Status "FAIL" "Redis: PING failed - $_"
            }
        } else {
            Print-Status "WARN" "redis-cli not installed - skipping Redis test"
        }
    } else {
        Print-Status "WARN" "Redis container not running - skipping"
    }

    Write-Host ""
}

# 5. Summary
Write-Host "${BLUE}━━━ Summary ━━━${RESET}"
Write-Host ""
Write-Host "${GREEN}Passed:   $ChecksPassed${RESET}"
Write-Host "${YELLOW}Warnings: $ChecksWarned${RESET}"
Write-Host "${RED}Failed:   $ChecksFailed${RESET}"
Write-Host ""

# Overall status
if ($CriticalFailures -gt 0) {
    Write-Host "${RED}[✗ SYSTEM NOT READY]${RESET} Critical failures detected"
    Write-Host ""
    Write-Host "Fix critical issues before deployment:"
    Write-Host "  1. Start Docker containers: docker compose up -d"
    Write-Host "  2. Check logs: docker compose logs"
    Write-Host "  3. Verify .env configuration"
    exit 1
} elseif ($ChecksWarned -gt 0) {
    Write-Host "${YELLOW}[⚠ SYSTEM PARTIALLY READY]${RESET} Some warnings present"
    Write-Host ""
    Write-Host "Review warnings and consider fixes before production deployment"
    exit 2
} else {
    Write-Host "${GREEN}[✓ SYSTEM READY]${RESET} All checks passed ✅"
    exit 0
}
