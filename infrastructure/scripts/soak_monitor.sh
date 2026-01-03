#!/bin/bash
#
# Claire de Binare - 72h Soak Test Monitoring Script
# Issue #428: Zero Restart Policy automation
#
# Usage: Run hourly via cron during 72h Soak Test
#   0 * * * * /path/to/scripts/soak_monitor.sh
#
# Requirements:
# - Docker running with CDB stack
# - artifacts/soak_test_* directory exists
# - Write permissions to artifacts directory

set -euo pipefail

# Configuration
HOUR=$(date +%H)
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
ARTIFACT_DIR="artifacts/soak_test_$(date +%Y%m%d)*"

# Find artifacts directory (created at test start)
if ! ls -d ${ARTIFACT_DIR} &>/dev/null; then
  echo "⚠️  WARNING: No soak test artifacts directory found"
  echo "Expected: artifacts/soak_test_YYYYMMDD_HHMMSS/"
  echo "Skipping monitoring checks"
  exit 0
fi

ARTIFACT_PATH=$(ls -d ${ARTIFACT_DIR} | head -1)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Soak Test Monitoring - Hour $HOUR"
echo "$TIMESTAMP"
echo "Artifact Path: $ARTIFACT_PATH"
echo "========================================="

# =============================================================================
# CRITICAL CHECK: Container Restarts (Every Hour)
# =============================================================================

echo -e "\n${YELLOW}[CHECK 1/5]${NC} Container Restart Detection..."

# Get all CDB containers and check uptime
RESTART_DETECTED=0
while IFS= read -r line; do
  CONTAINER=$(echo "$line" | awk '{print $1}')
  STATUS=$(echo "$line" | awk '{print $2,$3,$4}')

  # Check if status contains "seconds" or "minute" (recently restarted)
  if echo "$STATUS" | grep -qE "second|minute"; then
    echo -e "${RED}⚠️  ALERT: Container restart detected!${NC}"
    echo "  Container: $CONTAINER"
    echo "  Status: $STATUS"
    echo "  Detected At: $TIMESTAMP"

    # Log to file
    echo "$TIMESTAMP - RESTART DETECTED: $CONTAINER ($STATUS)" >> "$ARTIFACT_PATH/restart_alerts.log"

    RESTART_DETECTED=1
  fi
done < <(docker ps --filter "name=cdb_" --format "{{.Names}} {{.Status}}")

if [ "$RESTART_DETECTED" -eq 1 ]; then
  echo -e "${RED}===== ABORT: SOAK TEST FAILED =====${NC}"
  echo "Reason: Service restart detected (Zero Restart Policy violated)"
  echo "Time: $TIMESTAMP"

  # Create failure marker
  echo "$TIMESTAMP - ABORT: Service restart detected" > "$ARTIFACT_PATH/soak_test_FAILED.txt"

  # Capture failure evidence
  echo "Capturing failure evidence..."
  docker ps --all > "$ARTIFACT_PATH/failure_container_status.txt"
  docker stats --no-stream > "$ARTIFACT_PATH/failure_resources.txt"

  # Capture logs for all CDB services
  for service in cdb_ws cdb_signal cdb_risk cdb_execution cdb_db_writer cdb_paper_runner; do
    if docker ps -a --filter "name=$service" --format "{{.Names}}" | grep -q "$service"; then
      echo "  Capturing logs: $service"
      docker logs "$service" --tail 500 > "$ARTIFACT_PATH/failure_logs_${service}.txt" 2>&1 || true
    fi
  done

  echo -e "${RED}Soak Test FAILED. See $ARTIFACT_PATH for evidence.${NC}"
  exit 1
else
  echo -e "${GREEN}✓ No restarts detected${NC}"
  echo "$TIMESTAMP - Hour $HOUR: No restarts" >> "$ARTIFACT_PATH/hourly_checks.log"
fi

# =============================================================================
# CHECK 2: Service Health (Every Hour)
# =============================================================================

echo -e "\n${YELLOW}[CHECK 2/5]${NC} Service Health Status..."

# Count running CDB services
EXPECTED_SERVICES=8
RUNNING_SERVICES=$(docker ps --filter "name=cdb_" --filter "status=running" | grep -c "cdb_" || true)

if [ "$RUNNING_SERVICES" -lt "$EXPECTED_SERVICES" ]; then
  echo -e "${RED}⚠️  WARNING: Only $RUNNING_SERVICES/$EXPECTED_SERVICES services running${NC}"
  docker ps --filter "name=cdb_" --format "{{.Names}}: {{.Status}}"
else
  echo -e "${GREEN}✓ All $RUNNING_SERVICES/$EXPECTED_SERVICES services running${NC}"
fi

# =============================================================================
# CHECK 3: Resource Snapshot (Every 6 hours)
# =============================================================================

if [ "$((HOUR % 6))" -eq 0 ]; then
  echo -e "\n${YELLOW}[CHECK 3/5]${NC} Resource Snapshot (6h interval)..."

  SNAPSHOT_FILE="$ARTIFACT_PATH/resources_snapshot_${HOUR}h.txt"

  echo "Timestamp: $TIMESTAMP" > "$SNAPSHOT_FILE"
  echo "=========================================" >> "$SNAPSHOT_FILE"
  docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}" >> "$SNAPSHOT_FILE"

  echo -e "${GREEN}✓ Snapshot saved to: $SNAPSHOT_FILE${NC}"
else
  echo -e "\n${YELLOW}[CHECK 3/5]${NC} Resource Snapshot (skipped - not 6h interval)"
fi

# =============================================================================
# CHECK 4: Database Growth (Every 12 hours)
# =============================================================================

if [ "$((HOUR % 12))" -eq 0 ]; then
  echo -e "\n${YELLOW}[CHECK 4/5]${NC} Database Growth Check (12h interval)..."

  DB_FILE="$ARTIFACT_PATH/db_growth_${HOUR}h.txt"

  # Check if postgres is running
  if docker ps --filter "name=cdb_postgres" --filter "status=running" | grep -q "cdb_postgres"; then
    echo "Timestamp: $TIMESTAMP" > "$DB_FILE"
    echo "=========================================" >> "$DB_FILE"

    docker exec cdb_postgres psql -U cdb -d cdb_db -t -c "
      SELECT 'orders', COUNT(*) FROM orders UNION ALL
      SELECT 'trades', COUNT(*) FROM trades UNION ALL
      SELECT 'signals', COUNT(*) FROM signals;
    " >> "$DB_FILE" 2>&1 || echo "Error querying database" >> "$DB_FILE"

    echo -e "${GREEN}✓ Database metrics saved to: $DB_FILE${NC}"
  else
    echo -e "${RED}⚠️  PostgreSQL not running - skipping DB check${NC}"
  fi
else
  echo -e "\n${YELLOW}[CHECK 4/5]${NC} Database Growth Check (skipped - not 12h interval)"
fi

# =============================================================================
# CHECK 5: Disk Space (Every Hour)
# =============================================================================

echo -e "\n${YELLOW}[CHECK 5/5]${NC} Disk Space Check..."

# Get disk usage percentage
DISK_USAGE=$(df -h /var/lib/docker 2>/dev/null | awk 'NR==2 {print $5}' | sed 's/%//' || echo "unknown")

if [ "$DISK_USAGE" != "unknown" ]; then
  if [ "$DISK_USAGE" -gt 90 ]; then
    echo -e "${RED}⚠️  CRITICAL: Disk usage at ${DISK_USAGE}%${NC}"
    echo "$TIMESTAMP - CRITICAL: Disk usage ${DISK_USAGE}%" >> "$ARTIFACT_PATH/disk_alerts.log"
  elif [ "$DISK_USAGE" -gt 80 ]; then
    echo -e "${YELLOW}⚠️  WARNING: Disk usage at ${DISK_USAGE}%${NC}"
  else
    echo -e "${GREEN}✓ Disk usage: ${DISK_USAGE}%${NC}"
  fi
else
  echo -e "${YELLOW}⚠️  Could not determine disk usage${NC}"
fi

# =============================================================================
# Summary
# =============================================================================

echo -e "\n========================================="
echo -e "${GREEN}Hour $HOUR monitoring checks complete${NC}"
echo "$TIMESTAMP"
echo "Next check: $(date -d '+1 hour' -u +"%Y-%m-%d %H:%M:%S UTC")"
echo "========================================="

exit 0
