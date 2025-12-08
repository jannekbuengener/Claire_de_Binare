#!/bin/bash

# StatusLine Script for Claire de Binare Trading Bot
# Displays: Model | Phase | Docker Health | Block Status | Incidents | Git Branch | Cost/Duration
# Implements caching for performance optimization

# Read JSON from stdin (provided by Claude Code)
input=$(cat)

# Extract Claude Code context
MODEL=$(echo "$input" | jq -r '.model.display_name // "Unknown"')
COST=$(echo "$input" | jq -r '.cost.total_cost_usd // 0' | tr -d '\r' | xargs printf "%.4f" 2>/dev/null || echo "0.0000")
DURATION=$(echo "$input" | jq -r '.cost.total_duration_ms // 0' | tr -d '\r')
PROJECT_DIR=$(echo "$input" | jq -r '.workspace.project_dir // "."' | tr -d '\r')

# Git branch
GIT_BRANCH=""
if git rev-parse --git-dir > /dev/null 2>&1; then
    BRANCH=$(git branch --show-current 2>/dev/null)
    [ -n "$BRANCH" ] && GIT_BRANCH=" | \033[36m$BRANCH\033[0m"
fi

# Cache file paths
CACHE_DIR="/tmp/cdb_statusline_cache"
mkdir -p "$CACHE_DIR"
DOCKER_CACHE="$CACHE_DIR/docker_status"
PHASE_CACHE="$CACHE_DIR/phase_status"
BLOCK_CACHE="$CACHE_DIR/block_status"
INCIDENT_CACHE="$CACHE_DIR/incident_alert"

# Helper: check if cache is fresh (param: cache_file, ttl_seconds)
is_cache_fresh() {
    [ -f "$1" ] && [ $(($(date +%s) - $(stat -c %Y "$1" 2>/dev/null || stat -f %m "$1"))) -lt $2 ]
}

# Docker status (cache 30s)
if is_cache_fresh "$DOCKER_CACHE" 30; then
    DOCKER_STATUS=$(cat "$DOCKER_CACHE")
else
    HEALTHY=$(docker ps --filter "name=cdb_" --filter "status=running" --format "{{.Names}}" 2>/dev/null | wc -l)
    TOTAL=$(docker ps -a --filter "name=cdb_" --format "{{.Names}}" 2>/dev/null | wc -l)
    if [ "$TOTAL" -gt 0 ]; then
        if [ "$HEALTHY" -ge 9 ]; then
            DOCKER_STATUS="\033[32m✅ $HEALTHY/$TOTAL\033[0m"
        else
            DOCKER_STATUS="\033[33m⚠ $HEALTHY/$TOTAL\033[0m"
        fi
    else
        DOCKER_STATUS="\033[90mDocker N/A\033[0m"
    fi
    echo -e "$DOCKER_STATUS" > "$DOCKER_CACHE"
fi

# Trading phase (cache 300s)
if is_cache_fresh "$PHASE_CACHE" 300; then
    PHASE=$(cat "$PHASE_CACHE")
else
    PHASE=$(grep -A1 "## 15\. Aktueller 3-Tage-Block" "$PROJECT_DIR/CLAUDE.md" 2>/dev/null | grep "Phase" | sed 's/.*Phase //' | sed 's/ .*//' || echo "N1")
    [ -z "$PHASE" ] && PHASE="N1"
    PHASE="\033[32m$PHASE-Paper\033[0m"
    echo -e "$PHASE" > "$PHASE_CACHE"
fi

# Block status (cache 60s)
if is_cache_fresh "$BLOCK_CACHE" 60; then
    BLOCK_STATUS=$(cat "$BLOCK_CACHE")
else
    LATEST_SESSION=$(ls -t "$PROJECT_DIR/backoffice/docs/runbooks/SESSION_"*.md 2>/dev/null | head -1)
    if [ -n "$LATEST_SESSION" ]; then
        STATUS=$(grep "Status:" "$LATEST_SESSION" | head -1 | cut -d: -f2 | xargs)
        case "$STATUS" in
            *RUNNING*) BLOCK_STATUS="\033[32m🔄 Running\033[0m" ;;
            *COMPLETE*) BLOCK_STATUS="\033[36m✅ Complete\033[0m" ;;
            *) BLOCK_STATUS="\033[33mReady\033[0m" ;;
        esac
    else
        BLOCK_STATUS="\033[33mReady\033[0m"
    fi
    echo -e "$BLOCK_STATUS" > "$BLOCK_CACHE"
fi

# Incident alerts (cache 10s)
if is_cache_fresh "$INCIDENT_CACHE" 10; then
    INCIDENT=$(cat "$INCIDENT_CACHE")
else
    INCIDENT=""
    INCIDENT_FLAGS="$PROJECT_DIR/.claude/incident-flags"
    if [ -d "$INCIDENT_FLAGS" ] && [ -n "$(ls -A "$INCIDENT_FLAGS" 2>/dev/null)" ]; then
        ALERTS=$(ls "$INCIDENT_FLAGS" | tr '\n' ',' | sed 's/,$//')
        INCIDENT="\033[31m⚠️ $ALERTS\033[0m | "
    fi
    echo -e "$INCIDENT" > "$INCIDENT_CACHE"
fi

# Final output (single line)
echo -e "[\033[35m$MODEL\033[0m] $PHASE | $DOCKER_STATUS | $BLOCK_STATUS | ${INCIDENT}$GIT_BRANCH | \$$COST (${DURATION}ms)"
