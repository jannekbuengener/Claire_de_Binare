#!/usr/bin/env bash
# init-memory.sh - First-time setup for memory backend
# Infrastructure: Graphiti MCP Server (with FalkorDB) + Ollama
# Usage: ./infrastructure/scripts/init-memory.sh
#
# This script:
# 1. Starts the memory stack containers
# 2. Waits for Ollama API to be healthy
# 3. Pulls required embedding and LLM models
# 4. Waits for Graphiti MCP Server to be healthy
# 5. Displays MCP endpoint URL for Auto-Claude integration
#
# Note: build_indices_and_constraints() is called automatically
# by the MCP server on first episode ingestion.

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

COMPOSE_FILE="infrastructure/compose/memory.yml"
OLLAMA_HOST="${OLLAMA_HOST:-localhost}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
GRAPHITI_HOST="${GRAPHITI_HOST:-localhost}"
GRAPHITI_PORT="${GRAPHITI_PORT:-8000}"

# Models to pull
EMBEDDING_MODEL="nomic-embed-text"
LLM_MODEL="deepseek-r1:7b"

# Timeouts
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-300}"  # 5 minutes default
HEALTH_INTERVAL=5

# ============================================================================
# COLOR OUTPUT
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# Find repository root (where infrastructure/ folder exists)
find_repo_root() {
    local dir="$PWD"
    while [[ "$dir" != "/" ]]; do
        if [[ -d "$dir/infrastructure/compose" ]]; then
            echo "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    return 1
}

# Wait for HTTP endpoint to respond
wait_for_endpoint() {
    local url="$1"
    local description="$2"
    local timeout="$3"
    local start_time
    local elapsed=0

    start_time=$(date +%s)

    log_info "Waiting for $description..."

    while [[ $elapsed -lt $timeout ]]; do
        if curl -fsS "$url" > /dev/null 2>&1; then
            log_success "$description is healthy"
            return 0
        fi

        sleep "$HEALTH_INTERVAL"
        elapsed=$(($(date +%s) - start_time))
        echo -ne "\r  Waiting... ${elapsed}s / ${timeout}s"
    done

    echo ""
    log_error "$description did not become healthy within ${timeout}s"
    return 1
}

# Pull an Ollama model
pull_model() {
    local model="$1"
    local description="$2"

    log_info "Pulling $description ($model)..."

    if docker compose -f "$COMPOSE_FILE" exec -T cdb_ollama ollama pull "$model"; then
        log_success "$description pulled successfully"
        return 0
    else
        log_error "Failed to pull $description"
        return 1
    fi
}

# ============================================================================
# MAIN SCRIPT
# ============================================================================

main() {
    echo ""
    echo "========================================="
    echo "  Memory Backend Initialization"
    echo "  Graphiti MCP Server + Ollama"
    echo "========================================="
    echo ""

    # Change to repo root
    REPO_ROOT=$(find_repo_root) || {
        log_error "Could not find repository root (infrastructure/compose folder)"
        log_error "Run this script from within the repository"
        exit 1
    }

    cd "$REPO_ROOT"
    log_info "Repository root: $REPO_ROOT"

    # Verify compose file exists
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "Compose file not found: $COMPOSE_FILE"
        exit 1
    fi
    log_success "Compose file found: $COMPOSE_FILE"

    # Step 1: Start containers
    echo ""
    log_info "Step 1/4: Starting memory stack containers..."
    if docker compose -f "$COMPOSE_FILE" up -d; then
        log_success "Containers started"
    else
        log_error "Failed to start containers"
        docker compose -f "$COMPOSE_FILE" logs
        exit 1
    fi

    # Step 2: Wait for Ollama
    echo ""
    log_info "Step 2/4: Waiting for Ollama API..."
    wait_for_endpoint "http://${OLLAMA_HOST}:${OLLAMA_PORT}/api/tags" "Ollama API" "$HEALTH_TIMEOUT" || {
        log_error "Ollama failed to start. Check logs:"
        docker compose -f "$COMPOSE_FILE" logs cdb_ollama
        exit 1
    }

    # Step 3: Pull models
    echo ""
    log_info "Step 3/4: Pulling required models..."
    pull_model "$EMBEDDING_MODEL" "embedding model" || exit 1
    pull_model "$LLM_MODEL" "LLM model" || exit 1

    # Step 4: Wait for Graphiti MCP Server
    echo ""
    log_info "Step 4/4: Waiting for Graphiti MCP Server..."
    wait_for_endpoint "http://${GRAPHITI_HOST}:${GRAPHITI_PORT}/health" "Graphiti MCP Server" "$HEALTH_TIMEOUT" || {
        log_error "Graphiti MCP Server failed to start. Check logs:"
        docker compose -f "$COMPOSE_FILE" logs cdb_graphiti
        exit 1
    }

    # Success
    echo ""
    echo "========================================="
    echo -e "  ${GREEN}Initialization Complete!${NC}"
    echo "========================================="
    echo ""
    echo "  Services:"
    echo "    - Ollama API:        http://${OLLAMA_HOST}:${OLLAMA_PORT}"
    echo "    - Graphiti MCP:      http://${GRAPHITI_HOST}:${GRAPHITI_PORT}/mcp/"
    echo "    - FalkorDB Browser:  http://${GRAPHITI_HOST}:3000"
    echo ""
    echo "  Models loaded:"
    echo "    - Embedding: $EMBEDDING_MODEL"
    echo "    - LLM:       $LLM_MODEL"
    echo ""
    echo "  Next steps:"
    echo "    1. Add MCP server to your Claude settings (see docs/infra/memory-backend-setup.md)"
    echo "    2. Use the MCP endpoint in Auto-Claude agents"
    echo ""
    echo "  Note: Database indices are created automatically on first use."
    echo ""
}

# Run main function
main "$@"
