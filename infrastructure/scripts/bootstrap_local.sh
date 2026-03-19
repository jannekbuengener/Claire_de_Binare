#!/usr/bin/env bash
#
# Secondary convenience bootstrap for Claire de Binare (Linux/Mac)
#
# This script initializes secrets, validates the environment,
# starts the Docker stack, and runs basic health checks.
#
# Windows/PowerShell canonical v1 front door:
#   .\tools\cdb.ps1
#
# Note:
#   This helper is not the canonical PowerShell v1 front door and retains
#   convenience-oriented local bootstrap behavior.
#
# Usage:
#   ./infrastructure/scripts/bootstrap_local.sh

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}=== Claire de Binare - Local Bootstrap (Secondary Convenience Wrapper) ===${NC}"
echo -e "${YELLOW}Windows/PowerShell canonical v1 front door: .\\tools\\cdb.ps1${NC}"

# 1. Initialize Secrets
echo -e "\n${YELLOW}1. Initializing secrets...${NC}"
chmod +x infrastructure/scripts/init-secrets.sh
./infrastructure/scripts/init-secrets.sh

# 2. Setup Environment File
if [[ ! -f ".env" ]]; then
    echo -e "\n${YELLOW}2. Creating .env from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}[OK] .env created${NC}"
else
    echo -e "\n${YELLOW}2. .env already exists, skipping...${NC}"
fi

# 3. Validate Environment
echo -e "\n${YELLOW}3. Validating environment...${NC}"
chmod +x infrastructure/scripts/validate-environment.sh
./infrastructure/scripts/validate-environment.sh

# 4. Export Secrets for Docker Compose
echo -e "\n${YELLOW}4. Loading secrets into environment...${NC}"
# Use SECRETS_PATH if defined in .env or environment, fallback to standard path
if [[ -f ".env" ]]; then
    export $(grep ^SECRETS_PATH= .env | xargs) || true
fi
export SECRETS_PATH="${SECRETS_PATH:-${HOME}/Documents/.secrets/.cdb}"

if [[ -d "$SECRETS_PATH" ]]; then
    export REDIS_PASSWORD=$(cat "${SECRETS_PATH}/REDIS_PASSWORD")
    export POSTGRES_PASSWORD=$(cat "${SECRETS_PATH}/POSTGRES_PASSWORD")
    export GRAFANA_PASSWORD=$(cat "${SECRETS_PATH}/GRAFANA_PASSWORD")
    export POSTGRES_USER="claire_user"
    export STACK_NAME="cdb"
    echo -e "${GREEN}[OK] Secrets loaded successfully${NC}"
else
    echo -e "${RED}[FAIL] Secrets directory not found at $SECRETS_PATH${NC}"
    exit 1
fi

# 5. Start Docker Stack
# Secondary convenience path: retains legacy base.yml + dev.yml behavior.
echo -e "\n${YELLOW}5. Starting Docker Compose stack...${NC}"
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml up -d

# 6. Health Check Loop
echo -e "\n${YELLOW}6. Waiting for services to be healthy...${NC}"
MAX_RETRIES=30
COUNT=0
while [[ $COUNT -lt $MAX_RETRIES ]]; do
    PENDING=$(docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml ps --format json | jq -r 'select(.Health != "healthy") | .Service' | xargs)
    if [[ -z "$PENDING" ]]; then
        echo -e "${GREEN}✅ All services are healthy!${NC}"
        break
    fi
    echo -e "   Waiting for: $PENDING..."
    sleep 5
    COUNT=$((COUNT + 1))
done

if [[ $COUNT -eq $MAX_RETRIES ]]; then
    echo -e "${RED}❌ Timeout waiting for services to be healthy.${NC}"
    docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml ps
fi

# 7. Basic Smoke Test
echo -e "\n${YELLOW}7. Running basic smoke test...${NC}"
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo -e "${GREEN}[PASS] WS Service healthy${NC}"
else
    echo -e "${YELLOW}[WARN] WS Service health check failed or port not mapped${NC}"
fi

# 8. Database Check
echo -e "\n${YELLOW}8. Checking database status...${NC}"
if docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "\dt" > /dev/null 2>&1; then
    echo -e "${GREEN}[PASS] Database connection and tables verified${NC}"
else
    echo -e "${YELLOW}[WARN] Could not verify database tables (is it still initializing?)${NC}"
fi

echo -e "\n${CYAN}==========================================${NC}"
echo -e "${GREEN}Bootstrap complete!${NC}"
echo -e "Access Grafana at http://localhost:3000 (admin / see secrets)"
echo -e "Run tests with: make test"
echo -e "Canonical Windows/PowerShell v1 commands: .\\tools\\cdb.ps1 help"
echo -e "${CYAN}==========================================${NC}"
