<#
.SYNOPSIS
First-time setup for memory backend.

.DESCRIPTION
Infrastructure: Graphiti MCP Server (with FalkorDB) + Ollama

This script:
1. Starts the memory stack containers
2. Waits for Ollama API to be healthy
3. Pulls required embedding and LLM models
4. Waits for Graphiti MCP Server to be healthy
5. Displays MCP endpoint URL for Auto-Claude integration

Note: build_indices_and_constraints() is called automatically
by the MCP server on first episode ingestion.

.EXAMPLE
.\infrastructure\scripts\init-memory.ps1

.EXAMPLE
.\infrastructure\scripts\init-memory.ps1 -HealthTimeout 600
#>

param(
    [int]$HealthTimeout = 300,      # Timeout in seconds (default 5 minutes)
    [int]$HealthInterval = 5,       # Polling interval in seconds
    [string]$OllamaHost = 'localhost',
    [int]$OllamaPort = 11434,
    [string]$GraphitiHost = 'localhost',
    [int]$GraphitiPort = 8000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# CONFIGURATION
# ============================================================================

$COMPOSE_FILE = 'infrastructure\compose\memory.yml'

# Models to pull
$EMBEDDING_MODEL = 'nomic-embed-text'
$LLM_MODEL = 'deepseek-r1:7b'

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] " -ForegroundColor Cyan -NoNewline
    Write-Host $Message
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host "[ERROR] " -ForegroundColor Red -NoNewline
    Write-Host $Message
}

function Find-RepoRoot {
    <#
    .SYNOPSIS
    Find repository root (where infrastructure/ folder exists)
    #>
    $dir = Get-Location
    while ($dir) {
        $composePath = Join-Path $dir 'infrastructure\compose'
        if (Test-Path $composePath) {
            return $dir.Path
        }
        $parent = Split-Path -Parent $dir.Path
        if ($parent -eq $dir.Path) {
            return $null
        }
        $dir = Get-Item $parent
    }
    return $null
}

function Wait-ForEndpoint {
    <#
    .SYNOPSIS
    Wait for HTTP endpoint to respond with 200 OK
    #>
    param(
        [string]$Url,
        [string]$Description,
        [int]$Timeout,
        [int]$Interval
    )

    Write-Info "Waiting for $Description..."

    $startTime = Get-Date
    $elapsed = 0

    while ($elapsed -lt $Timeout) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Success "$Description is healthy"
                return $true
            }
        } catch {
            # Endpoint not ready yet, continue waiting
        }

        Start-Sleep -Seconds $Interval
        $elapsed = ((Get-Date) - $startTime).TotalSeconds
        Write-Host "`r  Waiting... $([int]$elapsed)s / ${Timeout}s" -NoNewline
    }

    Write-Host ""
    Write-ErrorMsg "$Description did not become healthy within ${Timeout}s"
    return $false
}

function Pull-OllamaModel {
    <#
    .SYNOPSIS
    Pull an Ollama model via docker compose exec
    #>
    param(
        [string]$Model,
        [string]$Description,
        [string]$ComposeFile
    )

    Write-Info "Pulling $Description ($Model)..."

    $result = & docker compose -f $ComposeFile exec -T cdb_ollama ollama pull $Model 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "$Description pulled successfully"
        return $true
    } else {
        Write-ErrorMsg "Failed to pull $Description"
        Write-Host $result
        return $false
    }
}

function Invoke-MemoryCompose {
    <#
    .SYNOPSIS
    Execute docker compose command for memory stack
    #>
    param([string[]]$CommandArgs)

    $cmd = @('compose', '-f', $COMPOSE_FILE) + $CommandArgs
    & 'docker' @cmd
}

# ============================================================================
# MAIN SCRIPT
# ============================================================================

$scriptDir = $PSScriptRoot
if (-not $scriptDir) {
    $definition = $MyInvocation.MyCommand.Definition
    $scriptDir = if ($definition) { Split-Path -Parent $definition } else { Get-Location }
}

# Find and change to repository root
$repoRoot = Find-RepoRoot
if (-not $repoRoot) {
    # Try navigating from script directory
    $repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
}

if (-not $repoRoot -or -not (Test-Path (Join-Path $repoRoot 'infrastructure\compose'))) {
    Write-ErrorMsg "Could not find repository root (infrastructure\compose folder)"
    Write-ErrorMsg "Run this script from within the repository"
    exit 1
}

Push-Location -LiteralPath $repoRoot
try {
    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "  Memory Backend Initialization" -ForegroundColor Cyan
    Write-Host "  Graphiti MCP Server + Ollama" -ForegroundColor Cyan
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host ""

    Write-Info "Repository root: $repoRoot"

    # Verify compose file exists
    if (-not (Test-Path $COMPOSE_FILE)) {
        Write-ErrorMsg "Compose file not found: $COMPOSE_FILE"
        exit 1
    }
    Write-Success "Compose file found: $COMPOSE_FILE"

    # Step 1: Start containers
    Write-Host ""
    Write-Info "Step 1/4: Starting memory stack containers..."

    Invoke-MemoryCompose -CommandArgs @('up', '-d')
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Failed to start containers"
        Invoke-MemoryCompose -CommandArgs @('logs')
        exit 1
    }
    Write-Success "Containers started"

    # Step 2: Wait for Ollama
    Write-Host ""
    Write-Info "Step 2/4: Waiting for Ollama API..."

    $ollamaUrl = "http://${OllamaHost}:${OllamaPort}/api/tags"
    $ollamaReady = Wait-ForEndpoint -Url $ollamaUrl -Description "Ollama API" -Timeout $HealthTimeout -Interval $HealthInterval

    if (-not $ollamaReady) {
        Write-ErrorMsg "Ollama failed to start. Check logs:"
        Invoke-MemoryCompose -CommandArgs @('logs', 'cdb_ollama')
        exit 1
    }

    # Step 3: Pull models
    Write-Host ""
    Write-Info "Step 3/4: Pulling required models..."

    $embeddingPulled = Pull-OllamaModel -Model $EMBEDDING_MODEL -Description "embedding model" -ComposeFile $COMPOSE_FILE
    if (-not $embeddingPulled) {
        exit 1
    }

    $llmPulled = Pull-OllamaModel -Model $LLM_MODEL -Description "LLM model" -ComposeFile $COMPOSE_FILE
    if (-not $llmPulled) {
        exit 1
    }

    # Step 4: Wait for Graphiti MCP Server
    Write-Host ""
    Write-Info "Step 4/4: Waiting for Graphiti MCP Server..."

    $graphitiUrl = "http://${GraphitiHost}:${GraphitiPort}/health"
    $graphitiReady = Wait-ForEndpoint -Url $graphitiUrl -Description "Graphiti MCP Server" -Timeout $HealthTimeout -Interval $HealthInterval

    if (-not $graphitiReady) {
        Write-ErrorMsg "Graphiti MCP Server failed to start. Check logs:"
        Invoke-MemoryCompose -CommandArgs @('logs', 'cdb_graphiti')
        exit 1
    }

    # Success
    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host "  Initialization Complete!" -ForegroundColor Green
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Services:" -ForegroundColor White
    Write-Host "    - Ollama API:        http://${OllamaHost}:${OllamaPort}"
    Write-Host "    - Graphiti MCP:      http://${GraphitiHost}:${GraphitiPort}/mcp/"
    Write-Host "    - FalkorDB Browser:  http://${GraphitiHost}:3000"
    Write-Host ""
    Write-Host "  Models loaded:" -ForegroundColor White
    Write-Host "    - Embedding: $EMBEDDING_MODEL"
    Write-Host "    - LLM:       $LLM_MODEL"
    Write-Host ""
    Write-Host "  Next steps:" -ForegroundColor White
    Write-Host "    1. Add MCP server to your Claude settings (see docs/infra/memory-backend-setup.md)"
    Write-Host "    2. Use the MCP endpoint in Auto-Claude agents"
    Write-Host ""
    Write-Host "  Note: Database indices are created automatically on first use."
    Write-Host ""

} finally {
    Pop-Location
}
