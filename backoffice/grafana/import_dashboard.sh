#!/bin/bash
# Import Claire de Binare Dashboard into Grafana
# Version: 1.0.0

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Grafana Dashboard Import ===${NC}\n"

# Configuration
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-Jannek246853}"
DASHBOARD_FILE="CLAIRE_DE_BINARE_DASHBOARD.json"

echo -e "${BLUE}Configuration:${NC}"
echo "  Grafana URL: $GRAFANA_URL"
echo "  Dashboard: $DASHBOARD_FILE"
echo ""

# Check if dashboard file exists
if [ ! -f "$DASHBOARD_FILE" ]; then
    echo -e "${RED}[ERROR]${NC} Dashboard file not found: $DASHBOARD_FILE"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Dashboard file found\n"

# Check Grafana health
echo -e "${BLUE}Checking Grafana health...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$GRAFANA_URL/api/health")

if [ "$HTTP_CODE" -ne 200 ]; then
    echo -e "${RED}[ERROR]${NC} Grafana not reachable (HTTP $HTTP_CODE)"
    echo "  Is Grafana running? Try: docker compose ps cdb_grafana"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Grafana is healthy (HTTP $HTTP_CODE)\n"

# Import Dashboard
echo -e "${BLUE}Importing dashboard...${NC}"

RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
    -d @"$DASHBOARD_FILE" \
    "$GRAFANA_URL/api/dashboards/db")

# Check response
if echo "$RESPONSE" | grep -q '"status":"success"'; then
    DASHBOARD_ID=$(echo "$RESPONSE" | grep -o '"id":[0-9]*' | head -1 | grep -o '[0-9]*')
    DASHBOARD_UID=$(echo "$RESPONSE" | grep -o '"uid":"[^"]*"' | head -1 | grep -o '[^"]*"$' | tr -d '"')
    DASHBOARD_URL="$GRAFANA_URL/d/$DASHBOARD_UID"

    echo -e "${GREEN}[SUCCESS]${NC} Dashboard imported successfully! ✅\n"
    echo -e "${GREEN}Dashboard ID:${NC} $DASHBOARD_ID"
    echo -e "${GREEN}Dashboard UID:${NC} $DASHBOARD_UID"
    echo -e "${GREEN}Dashboard URL:${NC} $DASHBOARD_URL"
    echo ""
    echo -e "${BLUE}Access the dashboard:${NC}"
    echo "  1. Open: $DASHBOARD_URL"
    echo "  2. Login: $GRAFANA_USER / <your_password>"
    echo ""
elif echo "$RESPONSE" | grep -q '"message"'; then
    ERROR_MSG=$(echo "$RESPONSE" | grep -o '"message":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo -e "${RED}[ERROR]${NC} Dashboard import failed: $ERROR_MSG"
    echo ""
    echo -e "${YELLOW}Common Issues:${NC}"
    echo "  1. Wrong credentials → Check GRAFANA_PASSWORD in .env"
    echo "  2. Dashboard exists → Use overwrite: true in JSON"
    echo "  3. Invalid JSON → Validate with: jq . $DASHBOARD_FILE"
    exit 1
else
    echo -e "${RED}[ERROR]${NC} Unexpected response from Grafana API"
    echo "Response: $RESPONSE"
    exit 1
fi

# Verify dashboard is accessible
echo -e "${BLUE}Verifying dashboard accessibility...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
    "$GRAFANA_URL/api/dashboards/uid/$DASHBOARD_UID")

if [ "$HTTP_CODE" -eq 200 ]; then
    echo -e "${GREEN}[OK]${NC} Dashboard is accessible ✅\n"
else
    echo -e "${YELLOW}[WARN]${NC} Dashboard import succeeded but not accessible (HTTP $HTTP_CODE)"
    echo "  Wait a few seconds and try again"
fi

echo -e "${GREEN}=== Import Complete ===${NC}"
