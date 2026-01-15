#!/usr/bin/env bash
#
# Environment Validation Script for Claire de Binare
#
# Validates that the development environment is correctly set up before
# attempting to start the stack. Checks prerequisites, configuration files,
# secrets, and Docker setup.
#
# Usage:
#   ./validate-environment.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track validation status
ERRORS=0
WARNINGS=0

echo ""
echo "=========================================="
echo " Claire de Binare - Environment Validation"
echo "=========================================="
echo ""

#------------------------------------------
# Helper Functions
#------------------------------------------

pass() {
    echo -e "  ${GREEN}[PASS]${NC} $1"
}

fail() {
    echo -e "  ${RED}[FAIL]${NC} $1"
    ((ERRORS++))
}

warn() {
    echo -e "  ${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++))
}

info() {
    echo -e "  ${BLUE}[INFO]${NC} $1"
}

#------------------------------------------
# 1. Check Prerequisites
#------------------------------------------

echo "1. Checking Prerequisites..."

# Check Docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
    pass "Docker installed (version: $DOCKER_VERSION)"

    # Check if Docker daemon is running
    if docker info &> /dev/null; then
        pass "Docker daemon is running"
    else
        fail "Docker daemon is not running - start Docker Desktop"
    fi
else
    fail "Docker is not installed - visit https://docs.docker.com/get-docker/"
fi

# Check Docker Compose
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version | awk '{print $4}' | head -1)
    pass "Docker Compose installed (version: $COMPOSE_VERSION)"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version | awk '{print $4}' | tr -d ',')
    warn "Using legacy docker-compose (version: $COMPOSE_VERSION) - consider upgrading"
else
    fail "Docker Compose is not installed"
fi

# Check Git
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version | awk '{print $3}')
    pass "Git installed (version: $GIT_VERSION)"
else
    fail "Git is not installed - visit https://git-scm.com/downloads"
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    pass "Python installed (version: $PYTHON_VERSION)"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version | awk '{print $2}')
    pass "Python installed (version: $PYTHON_VERSION)"
else
    fail "Python is not installed - visit https://www.python.org/downloads/"
fi

# Check Make (optional)
if command -v make &> /dev/null; then
    MAKE_VERSION=$(make --version | head -1 | awk '{print $3}')
    pass "Make installed (version: $MAKE_VERSION)"
else
    warn "Make is not installed (optional) - some Makefile commands will not work"
fi

echo ""

#------------------------------------------
# 2. Check Configuration Files
#------------------------------------------

echo "2. Checking Configuration Files..."

# Check .env file
if [[ -f ".env" ]]; then
    pass ".env file exists"

    # Check critical env vars
    if grep -q "^SECRETS_PATH=" .env; then
        SECRETS_PATH=$(grep "^SECRETS_PATH=" .env | cut -d'=' -f2- | envsubst)
        pass "SECRETS_PATH defined in .env"
        info "Secrets path: $SECRETS_PATH"
    else
        fail "SECRETS_PATH not defined in .env"
    fi

    if grep -q "^MEXC_TESTNET=true" .env; then
        pass "MEXC_TESTNET=true (safe for development)"
    elif grep -q "^MEXC_TESTNET=false" .env; then
        fail "MEXC_TESTNET=false (DANGER: do not use in development!)"
    else
        warn "MEXC_TESTNET not defined in .env (defaults to false - risky)"
    fi

    if grep -q "^SIGNAL_STRATEGY_ID=paper" .env; then
        pass "SIGNAL_STRATEGY_ID=paper (safe for development)"
    elif grep -q "^SIGNAL_STRATEGY_ID=live" .env; then
        fail "SIGNAL_STRATEGY_ID=live (DANGER: do not use in development!)"
    else
        warn "SIGNAL_STRATEGY_ID not defined in .env"
    fi

else
    fail ".env file is missing - run: cp .env.example .env"
fi

# Check .env.example exists (template)
if [[ -f ".env.example" ]]; then
    pass ".env.example template exists"
else
    warn ".env.example template is missing"
fi

# Check docker compose file
if [[ -f "infrastructure/compose/dev.yml" ]]; then
    pass "Docker Compose configuration exists (dev.yml)"
else
    fail "infrastructure/compose/dev.yml is missing"
fi

echo ""

#------------------------------------------
# 3. Check Secrets
#------------------------------------------

echo "3. Checking Secrets..."

# Determine secrets path
if [[ -f ".env" ]] && grep -q "^SECRETS_PATH=" .env; then
    SECRETS_PATH=$(grep "^SECRETS_PATH=" .env | cut -d'=' -f2- | envsubst)
else
    SECRETS_PATH="${HOME}/Documents/.secrets/.cdb"
    info "Using default secrets path: $SECRETS_PATH"
fi

# Check secrets directory exists
if [[ -d "$SECRETS_PATH" ]]; then
    pass "Secrets directory exists: $SECRETS_PATH"

    # Check individual secret files
    required_secrets=("REDIS_PASSWORD" "POSTGRES_PASSWORD" "GRAFANA_PASSWORD")
    for secret in "${required_secrets[@]}"; do
        secret_file="$SECRETS_PATH/$secret"
        if [[ -f "$secret_file" ]]; then
            # Check file is not empty
            if [[ -s "$secret_file" ]]; then
                pass "$secret exists and is not empty"
            else
                fail "$secret exists but is empty - regenerate secrets"
            fi

            # Check permissions (should be 600 or 400)
            if [[ "$(uname)" != "Darwin" ]]; then  # Skip on macOS (permissions work differently)
                perms=$(stat -c "%a" "$secret_file" 2>/dev/null || echo "unknown")
                if [[ "$perms" == "600" ]] || [[ "$perms" == "400" ]]; then
                    pass "$secret has secure permissions ($perms)"
                elif [[ "$perms" != "unknown" ]]; then
                    warn "$secret permissions too open ($perms) - run: chmod 600 $secret_file"
                fi
            fi
        else
            fail "$secret is missing - run: ./infrastructure/scripts/init-secrets.sh"
        fi
    done
else
    fail "Secrets directory is missing: $SECRETS_PATH"
    info "Run: ./infrastructure/scripts/init-secrets.sh to create secrets"
fi

echo ""

#------------------------------------------
# 4. Check Docker Network
#------------------------------------------

echo "4. Checking Docker Network..."

# Check if docker is running before checking networks
if docker info &> /dev/null; then
    NETWORK_NAME=$(grep "^NETWORK=" .env 2>/dev/null | cut -d'=' -f2- || echo "cdb_network")

    if docker network ls | grep -q "$NETWORK_NAME"; then
        pass "Docker network '$NETWORK_NAME' exists"
    else
        info "Docker network '$NETWORK_NAME' will be created on first startup"
    fi
else
    warn "Cannot check Docker network - Docker daemon not running"
fi

echo ""

#------------------------------------------
# 5. Check Disk Space
#------------------------------------------

echo "5. Checking System Resources..."

# Check available disk space (need at least 10GB)
if command -v df &> /dev/null; then
    AVAILABLE_GB=$(df -h . | awk 'NR==2 {print $4}' | sed 's/G//')
    if (( $(echo "$AVAILABLE_GB > 10" | bc -l 2>/dev/null || echo 0) )); then
        pass "Sufficient disk space available (${AVAILABLE_GB}GB)"
    else
        warn "Low disk space: ${AVAILABLE_GB}GB available (recommend 20GB+)"
    fi
fi

# Check available memory (need at least 4GB)
if command -v free &> /dev/null; then
    AVAILABLE_GB=$(free -g | awk 'NR==2 {print $7}')
    if (( AVAILABLE_GB >= 4 )); then
        pass "Sufficient memory available (${AVAILABLE_GB}GB free)"
    else
        warn "Low memory: ${AVAILABLE_GB}GB free (recommend 8GB+ total)"
    fi
fi

echo ""

#------------------------------------------
# Summary
#------------------------------------------

echo "=========================================="
echo " Validation Summary"
echo "=========================================="
echo ""

if [[ $ERRORS -eq 0 ]] && [[ $WARNINGS -eq 0 ]]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "Your environment is ready. Start the stack with:"
    echo "  docker compose -f infrastructure/compose/dev.yml up -d"
    echo ""
    exit 0
elif [[ $ERRORS -eq 0 ]]; then
    echo -e "${YELLOW}⚠️  $WARNINGS warning(s) found${NC}"
    echo ""
    echo "Your environment has minor issues but should work."
    echo "Review warnings above and fix if needed."
    echo ""
    echo "Start the stack with:"
    echo "  docker compose -f infrastructure/compose/dev.yml up -d"
    echo ""
    exit 0
else
    echo -e "${RED}❌ $ERRORS error(s) found${NC}"
    if [[ $WARNINGS -gt 0 ]]; then
        echo -e "${YELLOW}⚠️  $WARNINGS warning(s) found${NC}"
    fi
    echo ""
    echo "Please fix the errors above before starting the stack."
    echo "See DEVELOPER_ONBOARDING.md for detailed setup instructions."
    echo ""
    exit 1
fi
