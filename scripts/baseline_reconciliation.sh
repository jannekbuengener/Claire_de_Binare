#!/usr/bin/env bash
#
# Baseline Reconciliation Script
# Compares Redis stream.fills count with PostgreSQL orders count
# Usage: ./scripts/baseline_reconciliation.sh
#
# Exit codes:
#   0 = Reconciliation OK (counts match)
#   1 = Reconciliation FAILED (mismatch detected)
#   2 = Error (missing tools, connection issues)
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Baseline Reconciliation Check"
echo "Date: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo "========================================="

# Check if running in Docker environment
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: docker command not found${NC}"
    exit 2
fi

# Get Redis stream.fills count
echo -n "Fetching Redis stream.fills count... "
REDIS_COUNT=$(docker exec cdb_redis sh -c 'redis-cli -a $(cat /run/secrets/redis_password) XLEN stream.fills' 2>/dev/null || echo "ERROR")

if [ "$REDIS_COUNT" = "ERROR" ]; then
    echo -e "${RED}FAILED${NC}"
    echo "ERROR: Could not connect to Redis or read stream.fills"
    exit 2
fi
echo -e "${GREEN}OK${NC} (Count: $REDIS_COUNT)"

# Get PostgreSQL orders count (FILLED + REJECTED only, matching stream.fills content)
echo -n "Fetching PostgreSQL orders count... "
POSTGRES_COUNT=$(docker exec cdb_postgres psql -U claire_user -d claire_de_binare -t -c \
    "SELECT COUNT(*) FROM orders WHERE status IN ('filled', 'rejected');" 2>/dev/null | tr -d ' ' || echo "ERROR")

if [ "$POSTGRES_COUNT" = "ERROR" ]; then
    echo -e "${RED}FAILED${NC}"
    echo "ERROR: Could not connect to PostgreSQL or query orders table"
    exit 2
fi
echo -e "${GREEN}OK${NC} (Count: $POSTGRES_COUNT)"

# Compare counts
echo ""
echo "Reconciliation Results:"
echo "  Redis stream.fills:  $REDIS_COUNT"
echo "  PostgreSQL orders:   $POSTGRES_COUNT"

if [ "$REDIS_COUNT" -eq "$POSTGRES_COUNT" ]; then
    echo -e "${GREEN}✓ RECONCILIATION OK${NC} - Counts match!"
    exit 0
else
    DIFF=$((REDIS_COUNT - POSTGRES_COUNT))
    echo -e "${RED}✗ RECONCILIATION FAILED${NC} - Mismatch detected!"
    echo "  Difference: $DIFF (Redis - Postgres)"

    if [ "$DIFF" -gt 0 ]; then
        echo -e "${YELLOW}WARNING: Redis has MORE entries than Postgres${NC}"
        echo "  Possible causes:"
        echo "    - DB write failure (orders not persisted)"
        echo "    - DB rollback/transaction issue"
        echo "    - Schema migration incomplete"
    else
        echo -e "${YELLOW}WARNING: Postgres has MORE entries than Redis${NC}"
        echo "  Possible causes:"
        echo "    - Redis stream maxlen limit reached (old entries trimmed)"
        echo "    - Manual DB inserts (not via execution service)"
        echo "    - Redis data loss/restart"
    fi

    exit 1
fi
