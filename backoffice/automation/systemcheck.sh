#!/usr/bin/env bash
#
# systemcheck.sh - System Health Check for Claire de Binaire
# Purpose: Comprehensive Docker, Service, and Database health validation
#
# Usage:
#   ./systemcheck.sh                # Full system check
#   ./systemcheck.sh --quick        # Quick check (skip optional tests)
#   ./systemcheck.sh --update-docs  # Update PROJECT_STATUS.md with results
#
# Exit Codes:
#   0: All checks passed
#   1: Critical failures detected
#   2: Warnings present (non-critical)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
QUICK_MODE="${1:-}"
UPDATE_DOCS=false

# Parse arguments
if [[ "$QUICK_MODE" == "--quick" ]]; then
    QUICK_MODE=true
elif [[ "$QUICK_MODE" == "--update-docs" ]]; then
    UPDATE_DOCS=true
    QUICK_MODE=false
else
    QUICK_MODE=false
fi

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNED=0
CRITICAL_FAILURES=0

# Results storage
declare -A CONTAINER_STATUS
declare -A CONTAINER_HEALTH
declare -A SERVICE_PORTS

# Expected services configuration
declare -A EXPECTED_SERVICES=(
    ["cdb_redis"]="6379"
    ["cdb_postgres"]="5432"
    ["cdb_ws"]="8000"
    ["cdb_core"]="8001"
    ["cdb_risk"]="8002"
    ["cdb_execution"]="8003"
    ["cdb_prometheus"]="19090"
    ["cdb_grafana"]="3000"
)

# Services with health endpoints
declare -A HEALTH_SERVICES=(
    ["cdb_ws"]="8000"
    ["cdb_core"]="8001"
    ["cdb_risk"]="8002"
    ["cdb_execution"]="8003"
)

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  System Health Check - Claire de Binaire                ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${MAGENTA}Timestamp:${NC} $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo -e "${MAGENTA}Mode:${NC} $([ "$QUICK_MODE" == "true" ] && echo "Quick Check" || echo "Full Check")"
echo ""

# Helper function for status output
print_status() {
    local status="$1"
    local message="$2"

    case "$status" in
        "OK")
            echo -e "${GREEN}[✓ OK]${NC} $message"
            ((CHECKS_PASSED++))
            ;;
        "FAIL")
            echo -e "${RED}[✗ FAIL]${NC} $message"
            ((CHECKS_FAILED++))
            ((CRITICAL_FAILURES++))
            ;;
        "WARN")
            echo -e "${YELLOW}[⚠ WARN]${NC} $message"
            ((CHECKS_WARNED++))
            ;;
        "INFO")
            echo -e "${BLUE}[ℹ INFO]${NC} $message"
            ;;
    esac
}

# 1. Check Prerequisites
echo -e "${BLUE}━━━ Prerequisites ━━━${NC}"

# Check if Docker is installed
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | sed 's/,//')
    print_status "OK" "Docker installed (version $DOCKER_VERSION)"
else
    print_status "FAIL" "Docker not installed"
    exit 1
fi

# Check if Docker daemon is running
if docker info &> /dev/null; then
    print_status "OK" "Docker daemon is running"
else
    print_status "FAIL" "Docker daemon is not running"
    exit 1
fi

# Check if docker compose is available
if docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version --short)
    print_status "OK" "Docker Compose available (v$COMPOSE_VERSION)"
else
    print_status "FAIL" "Docker Compose not available"
    exit 1
fi

# Check if .env file exists
if [[ -f "$ENV_FILE" ]]; then
    print_status "OK" ".env file found"
else
    print_status "WARN" ".env file not found (using defaults)"
fi

echo ""

# 2. Check Container Status
echo -e "${BLUE}━━━ Container Status ━━━${NC}"

# Get container status
COMPOSE_PS_OUTPUT=$(cd "$ROOT_DIR" && docker compose ps --format json 2>/dev/null || echo "[]")

if [[ "$COMPOSE_PS_OUTPUT" == "[]" || -z "$COMPOSE_PS_OUTPUT" ]]; then
    print_status "WARN" "No containers found (docker compose ps returned empty)"
    for service in "${!EXPECTED_SERVICES[@]}"; do
        CONTAINER_STATUS["$service"]="not_running"
        CONTAINER_HEALTH["$service"]="n/a"
    done
else
    # Parse JSON output (requires jq or manual parsing)
    if command -v jq &> /dev/null; then
        while IFS= read -r line; do
            if [[ -n "$line" ]]; then
                SERVICE=$(echo "$line" | jq -r '.Service')
                STATE=$(echo "$line" | jq -r '.State')
                HEALTH=$(echo "$line" | jq -r '.Health // "n/a"')

                CONTAINER_STATUS["$SERVICE"]="$STATE"
                CONTAINER_HEALTH["$SERVICE"]="$HEALTH"

                if [[ "$STATE" == "running" ]]; then
                    if [[ "$HEALTH" == "healthy" || "$HEALTH" == "n/a" ]]; then
                        print_status "OK" "$SERVICE: $STATE $([ "$HEALTH" != "n/a" ] && echo "($HEALTH)")"
                    else
                        print_status "WARN" "$SERVICE: $STATE ($HEALTH)"
                    fi
                else
                    print_status "FAIL" "$SERVICE: $STATE"
                fi
            fi
        done < <(echo "$COMPOSE_PS_OUTPUT" | jq -c '.')
    else
        # Fallback: Parse without jq (less reliable)
        print_status "WARN" "jq not installed - using basic parsing"
        cd "$ROOT_DIR" && docker compose ps --format "table {{.Service}}\t{{.State}}\t{{.Health}}" | tail -n +2 | while read -r service state health; do
            CONTAINER_STATUS["$service"]="$state"
            CONTAINER_HEALTH["$service"]="${health:-n/a}"

            if [[ "$state" == "running" ]]; then
                print_status "OK" "$service: $state"
            else
                print_status "FAIL" "$service: $state"
            fi
        done
    fi
fi

# Check for missing services
for service in "${!EXPECTED_SERVICES[@]}"; do
    if [[ -z "${CONTAINER_STATUS[$service]:-}" ]]; then
        print_status "WARN" "$service: not found in docker compose ps"
        CONTAINER_STATUS["$service"]="not_found"
        CONTAINER_HEALTH["$service"]="n/a"
    fi
done

echo ""

# 3. Check Health Endpoints
echo -e "${BLUE}━━━ Health Endpoints ━━━${NC}"

for service in "${!HEALTH_SERVICES[@]}"; do
    port="${HEALTH_SERVICES[$service]}"
    health_url="http://localhost:$port/health"

    if [[ "${CONTAINER_STATUS[$service]:-}" != "running" ]]; then
        print_status "WARN" "$service /health - skipped (container not running)"
        continue
    fi

    # Test health endpoint
    if response=$(curl -sf --max-time 5 "$health_url" 2>/dev/null); then
        # Check if response contains "ok" or "healthy"
        if echo "$response" | grep -qi "ok\|healthy"; then
            print_status "OK" "$service /health → 200 OK"
        else
            print_status "WARN" "$service /health → unexpected response"
        fi
    else
        print_status "FAIL" "$service /health → connection failed"
    fi
done

echo ""

# 4. Check Database Connectivity
if [[ "$QUICK_MODE" != "true" ]]; then
    echo -e "${BLUE}━━━ Database Connectivity ━━━${NC}"

    # Load .env if exists
    if [[ -f "$ENV_FILE" ]]; then
        export $(grep -v '^#' "$ENV_FILE" | xargs)
    fi

    # PostgreSQL
    if [[ "${CONTAINER_STATUS[cdb_postgres]:-}" == "running" ]]; then
        PGHOST="${POSTGRES_HOST:-localhost}"
        PGPORT="${POSTGRES_PORT:-5432}"
        PGUSER="${POSTGRES_USER:-claire_user}"
        PGDB="${POSTGRES_DB:-claire_de_binare}"
        PGPASSWORD="${POSTGRES_PASSWORD:-}"

        if command -v psql &> /dev/null; then
            if PGPASSWORD="$PGPASSWORD" psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDB" -c "SELECT 1" &> /dev/null; then
                print_status "OK" "PostgreSQL: Connection successful"
            else
                print_status "FAIL" "PostgreSQL: Connection failed"
            fi
        else
            print_status "WARN" "psql not installed - skipping PostgreSQL test"
        fi
    else
        print_status "WARN" "PostgreSQL container not running - skipping"
    fi

    # Redis
    if [[ "${CONTAINER_STATUS[cdb_redis]:-}" == "running" ]]; then
        REDIS_HOST="${REDIS_HOST:-localhost}"
        REDIS_PORT="${REDIS_PORT:-6379}"

        if command -v redis-cli &> /dev/null; then
            if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" PING &> /dev/null; then
                print_status "OK" "Redis: PING successful"
            else
                print_status "FAIL" "Redis: PING failed"
            fi
        else
            print_status "WARN" "redis-cli not installed - skipping Redis test"
        fi
    else
        print_status "WARN" "Redis container not running - skipping"
    fi

    echo ""
fi

# 5. Summary
echo -e "${BLUE}━━━ Summary ━━━${NC}"
echo ""
echo -e "${GREEN}Passed:  $CHECKS_PASSED${NC}"
echo -e "${YELLOW}Warnings: $CHECKS_WARNED${NC}"
echo -e "${RED}Failed:   $CHECKS_FAILED${NC}"
echo ""

# Overall status
if [[ $CRITICAL_FAILURES -gt 0 ]]; then
    echo -e "${RED}[✗ SYSTEM NOT READY]${NC} Critical failures detected"
    echo ""
    echo "Fix critical issues before deployment:"
    echo "  1. Start Docker containers: docker compose up -d"
    echo "  2. Check logs: docker compose logs"
    echo "  3. Verify .env configuration"
    exit 1
elif [[ $CHECKS_WARNED -gt 0 ]]; then
    echo -e "${YELLOW}[⚠ SYSTEM PARTIALLY READY]${NC} Some warnings present"
    echo ""
    echo "Review warnings and consider fixes before production deployment"
    exit 2
else
    echo -e "${GREEN}[✓ SYSTEM READY]${NC} All checks passed ✅"
    exit 0
fi
