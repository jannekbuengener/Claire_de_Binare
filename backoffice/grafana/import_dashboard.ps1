# Import Claire de Binare Dashboard into Grafana
# Version: 1.0.0

# ANSI Colors
$RED = "`e[31m"
$GREEN = "`e[32m"
$YELLOW = "`e[33m"
$BLUE = "`e[34m"
$RESET = "`e[0m"

Write-Host "${BLUE}=== Grafana Dashboard Import ===${RESET}`n"

# Configuration from .env or defaults
$GRAFANA_URL = if ($env:GRAFANA_URL) { $env:GRAFANA_URL } else { "http://localhost:3000" }
$GRAFANA_USER = if ($env:GRAFANA_USER) { $env:GRAFANA_USER } else { "admin" }
$GRAFANA_PASSWORD = if ($env:GRAFANA_PASSWORD) { $env:GRAFANA_PASSWORD } else { "Jannek246853" }
$DASHBOARD_FILE = "CLAIRE_DE_BINARE_DASHBOARD.json"

Write-Host "${BLUE}Configuration:${RESET}"
Write-Host "  Grafana URL: $GRAFANA_URL"
Write-Host "  Dashboard: $DASHBOARD_FILE"
Write-Host ""

# Check if dashboard file exists
if (-not (Test-Path $DASHBOARD_FILE)) {
    Write-Host "${RED}[ERROR]${RESET} Dashboard file not found: $DASHBOARD_FILE"
    exit 1
}

Write-Host "${GREEN}[OK]${RESET} Dashboard file found`n"

# Check Grafana health
Write-Host "${BLUE}Checking Grafana health...${RESET}"
try {
    $healthResponse = Invoke-RestMethod -Uri "$GRAFANA_URL/api/health" -Method Get -ErrorAction Stop
    Write-Host "${GREEN}[OK]${RESET} Grafana is healthy (Version: $($healthResponse.version))`n"
} catch {
    Write-Host "${RED}[ERROR]${RESET} Grafana not reachable: $_"
    Write-Host "  Is Grafana running? Try: docker compose ps cdb_grafana"
    exit 1
}

# Import Dashboard
Write-Host "${BLUE}Importing dashboard...${RESET}"

# Read dashboard JSON
$dashboardContent = Get-Content $DASHBOARD_FILE -Raw | ConvertFrom-Json

# Prepare credentials
$base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${GRAFANA_USER}:${GRAFANA_PASSWORD}"))

# Import via API
try {
    $headers = @{
        "Content-Type" = "application/json"
        "Authorization" = "Basic $base64Auth"
    }

    $response = Invoke-RestMethod -Uri "$GRAFANA_URL/api/dashboards/db" `
        -Method Post `
        -Headers $headers `
        -Body (Get-Content $DASHBOARD_FILE -Raw) `
        -ErrorAction Stop

    if ($response.status -eq "success") {
        $dashboardId = $response.id
        $dashboardUid = $response.uid
        $dashboardUrl = "$GRAFANA_URL/d/$dashboardUid"

        Write-Host "${GREEN}[SUCCESS]${RESET} Dashboard imported successfully! ✅`n"
        Write-Host "${GREEN}Dashboard ID:${RESET} $dashboardId"
        Write-Host "${GREEN}Dashboard UID:${RESET} $dashboardUid"
        Write-Host "${GREEN}Dashboard URL:${RESET} $dashboardUrl"
        Write-Host ""
        Write-Host "${BLUE}Access the dashboard:${RESET}"
        Write-Host "  1. Open: $dashboardUrl"
        Write-Host "  2. Login: $GRAFANA_USER / <your_password>"
        Write-Host ""
    } else {
        Write-Host "${RED}[ERROR]${RESET} Dashboard import failed: $($response.message)"
        exit 1
    }
} catch {
    $errorMessage = $_.Exception.Message
    Write-Host "${RED}[ERROR]${RESET} Dashboard import failed: $errorMessage"
    Write-Host ""
    Write-Host "${YELLOW}Common Issues:${RESET}"
    Write-Host "  1. Wrong credentials → Check GRAFANA_PASSWORD in .env"
    Write-Host "  2. Dashboard exists → Use overwrite: true in JSON"
    Write-Host "  3. Invalid JSON → Validate with: Get-Content $DASHBOARD_FILE | ConvertFrom-Json"
    exit 1
}

# Verify dashboard is accessible
Write-Host "${BLUE}Verifying dashboard accessibility...${RESET}"
try {
    $verifyResponse = Invoke-RestMethod -Uri "$GRAFANA_URL/api/dashboards/uid/$dashboardUid" `
        -Method Get `
        -Headers $headers `
        -ErrorAction Stop

    Write-Host "${GREEN}[OK]${RESET} Dashboard is accessible ✅`n"
} catch {
    Write-Host "${YELLOW}[WARN]${RESET} Dashboard import succeeded but not accessible yet"
    Write-Host "  Wait a few seconds and try again"
}

Write-Host "${GREEN}=== Import Complete ===${RESET}"
