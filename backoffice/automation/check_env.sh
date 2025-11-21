#!/usr/bin/env bash
#
# check_env.sh - ENV Variable Validation for Claire de Binaire
# Purpose: Validates .env against expected variables and values
#
# Usage:
#   ./check_env.sh              # Check .env in current directory
#   ./check_env.sh /path/.env   # Check specific file
#
# Exit Codes:
#   0: All checks passed
#   1: Validation failed (errors found)
#   2: .env file not found

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENV_FILE="${1:-.env}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Counters
ERRORS=0
WARNINGS=0
OK=0

echo -e "${BLUE}=== ENV Validation for Claire de Binaire ===${NC}\n"

# Check if .env exists
if [[ ! -f "$ENV_FILE" ]]; then
    echo -e "${RED}[ERROR]${NC} $ENV_FILE not found!"
    echo -e "${YELLOW}[INFO]${NC} Copy .env.example to .env and fill in values."
    exit 2
fi

echo -e "${GREEN}[OK]${NC} $ENV_FILE found\n"

# Parse .env file
declare -A env_vars
while IFS='=' read -r key value; do
    # Skip comments and empty lines
    [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
    # Trim whitespace
    key=$(echo "$key" | xargs)
    value=$(echo "$value" | xargs)
    env_vars["$key"]="$value"
done < "$ENV_FILE"

echo -e "${BLUE}Found ${#env_vars[@]} variables in $ENV_FILE${NC}\n"

# Validation function
validate_var() {
    local var_name="$1"
    local required="$2"
    local var_type="$3"
    local default="${4:-}"
    local min="${5:-}"
    local max="${6:-}"
    local values="${7:-}"  # For enum type

    local value="${env_vars[$var_name]:-}"

    # Check if required var exists
    if [[ "$required" == "true" && -z "$value" ]]; then
        echo -e "${RED}[ERROR]${NC} $var_name is required but missing!"
        ((ERRORS++))
        return
    fi

    # Skip if optional and not set
    if [[ "$required" == "false" && -z "$value" ]]; then
        if [[ -n "$default" ]]; then
            echo -e "${YELLOW}[INFO]${NC} $var_name not set, default: $default"
        fi
        return
    fi

    # Type validation
    case "$var_type" in
        int)
            if [[ "$value" =~ ^[0-9]+$ ]]; then
                local int_value="$value"
                if [[ -n "$min" && "$int_value" -lt "$min" ]]; then
                    echo -e "${YELLOW}[WARN]${NC} $var_name = $int_value (Min: $min)"
                    ((WARNINGS++))
                elif [[ -n "$max" && "$int_value" -gt "$max" ]]; then
                    echo -e "${YELLOW}[WARN]${NC} $var_name = $int_value (Max: $max)"
                    ((WARNINGS++))
                else
                    echo -e "${GREEN}[OK]${NC} $var_name = $int_value"
                    ((OK++))
                fi
            else
                echo -e "${RED}[ERROR]${NC} $var_name = '$value' (not an integer)"
                ((ERRORS++))
            fi
            ;;

        float)
            if [[ "$value" =~ ^[0-9]+\.?[0-9]*$ ]]; then
                local float_value="$value"
                # Use bc for float comparison
                if [[ -n "$min" ]] && (( $(echo "$float_value < $min" | bc -l) )); then
                    echo -e "${YELLOW}[WARN]${NC} $var_name = $float_value (Min: $min)"
                    ((WARNINGS++))
                elif [[ -n "$max" ]] && (( $(echo "$float_value > $max" | bc -l) )); then
                    echo -e "${YELLOW}[WARN]${NC} $var_name = $float_value (Max: $max)"
                    ((WARNINGS++))
                else
                    echo -e "${GREEN}[OK]${NC} $var_name = $float_value"
                    ((OK++))
                fi
            else
                echo -e "${RED}[ERROR]${NC} $var_name = '$value' (not a float)"
                ((ERRORS++))
            fi
            ;;

        secret)
            local length=${#value}
            if [[ -n "$min" && "$length" -lt "$min" ]]; then
                echo -e "${RED}[ERROR]${NC} $var_name too short ($length < $min)"
                ((ERRORS++))
            else
                local masked=$(printf '%*s' $((length > 8 ? 8 : length)) | tr ' ' '*')
                echo -e "${GREEN}[OK]${NC} $var_name = $masked (Length: $length)"
                ((OK++))
            fi
            ;;

        enum)
            if [[ "$values" == *"$value"* ]]; then
                echo -e "${GREEN}[OK]${NC} $var_name = $value"
                ((OK++))
            else
                echo -e "${RED}[ERROR]${NC} $var_name = '$value' (Allowed: $values)"
                ((ERRORS++))
            fi
            ;;

        string)
            echo -e "${GREEN}[OK]${NC} $var_name = $value"
            ((OK++))
            ;;

        *)
            echo -e "${YELLOW}[WARN]${NC} Unknown type for $var_name: $var_type"
            ((WARNINGS++))
            ;;
    esac
}

# Validate all expected variables
echo -e "${BLUE}=== Validating Variables ===${NC}\n"

# Database
validate_var "POSTGRES_HOST" "true" "string" "cdb_postgres"
validate_var "POSTGRES_PORT" "true" "int" "5432" "1024" "65535"
validate_var "POSTGRES_USER" "true" "string" "claire_user"
validate_var "POSTGRES_PASSWORD" "true" "secret" "" "8"
validate_var "POSTGRES_DB" "true" "string" "claire_de_binare"

# Redis
validate_var "REDIS_HOST" "true" "string" "cdb_redis"
validate_var "REDIS_PORT" "true" "int" "6379" "1024" "65535"
validate_var "REDIS_PASSWORD" "true" "secret" "" "8"
validate_var "REDIS_DB" "false" "int" "0" "0" "15"

# Grafana
validate_var "GRAFANA_PASSWORD" "false" "secret" "admin" "5"

# Risk Limits (NICHT ÄNDERN ohne Rücksprache!)
validate_var "MAX_POSITION_PCT" "true" "float" "0.10" "0.01" "1.0"
validate_var "MAX_DAILY_DRAWDOWN_PCT" "true" "float" "0.05" "0.01" "0.5"
validate_var "MAX_TOTAL_EXPOSURE_PCT" "true" "float" "0.30" "0.1" "1.0"
validate_var "CIRCUIT_BREAKER_THRESHOLD_PCT" "true" "float" "0.10" "0.05" "0.5"
validate_var "MAX_SLIPPAGE_PCT" "true" "float" "0.02" "0.001" "0.1"

# System
validate_var "DATA_STALE_TIMEOUT_SEC" "true" "int" "60" "10" "300"
validate_var "LOG_LEVEL" "false" "enum" "INFO" "" "" "DEBUG,INFO,WARNING,ERROR"

# Trading Configuration
validate_var "TRADING_MODE" "true" "enum" "paper" "" "" "paper,live"
validate_var "ACCOUNT_EQUITY" "true" "float" "100000.0" "1000.0" "10000000.0"

# MEXC API (Optional for N1 Paper-Test, Required for Live-Trading)
validate_var "MEXC_API_KEY" "false" "secret" "" "32"
validate_var "MEXC_API_SECRET" "false" "secret" "" "32"

# Summary
echo ""
echo -e "${BLUE}=== Validation Summary ===${NC}"
echo -e "${GREEN}OK:${NC} $OK"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "${RED}Errors:${NC} $ERRORS"
echo ""

# Exit code logic
if [[ $ERRORS -gt 0 ]]; then
    echo -e "${RED}[FAILED]${NC} ENV Validation failed! ❌\n"
    exit 1
elif [[ $WARNINGS -gt 0 ]]; then
    echo -e "${YELLOW}[WARN]${NC} ENV Validation passed with warnings\n"
    exit 0
else
    echo -e "${GREEN}[SUCCESS]${NC} ENV Validation passed! ✅\n"
    exit 0
fi
