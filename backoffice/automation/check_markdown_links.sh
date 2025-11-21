#!/usr/bin/env bash
#
# Markdown Link Checker for Claire de Binaire
#
# This script checks all markdown files for broken links (both internal and external).
# It uses markdown-link-check (npm package) with custom configuration.
#
# Usage:
#   ./check_markdown_links.sh                  # Check all markdown files
#   ./check_markdown_links.sh README.md        # Check specific file
#   ./check_markdown_links.sh --ci             # CI mode (exit 1 on errors)
#
# Requirements:
#   - Node.js and npm installed
#   - markdown-link-check: npm install -g markdown-link-check
#
# Exit Codes:
#   0: All links OK
#   1: Broken links found (in CI mode)
#   2: Script error (missing dependencies, etc.)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_FILE="$ROOT_DIR/.markdown-link-check.json"
LOG_FILE="$ROOT_DIR/markdown-link-check.log"
CI_MODE=false

# Parse arguments
if [[ "${1:-}" == "--ci" ]]; then
    CI_MODE=true
    shift
fi

TARGET_FILES=("$@")

# Check prerequisites
check_prerequisites() {
    if ! command -v markdown-link-check &> /dev/null; then
        echo -e "${RED}❌ markdown-link-check not found${NC}"
        echo "Install with: npm install -g markdown-link-check"
        exit 2
    fi

    echo -e "${GREEN}✅ markdown-link-check found${NC}"
}

# Find all markdown files (excluding node_modules, .venv, archive)
find_markdown_files() {
    find "$ROOT_DIR" -type f -name "*.md" \
        ! -path "*/node_modules/*" \
        ! -path "*/.venv/*" \
        ! -path "*/archive/*" \
        ! -path "*/.pytest_cache/*" \
        ! -path "*/.git/*" \
        | sort
}

# Check links in a single file
check_file() {
    local file="$1"
    local relative_path="${file#$ROOT_DIR/}"

    echo -e "${BLUE}Checking: ${relative_path}${NC}"

    if markdown-link-check "$file" --config "$CONFIG_FILE" --quiet 2>&1 | tee -a "$LOG_FILE"; then
        echo -e "${GREEN}  ✓ All links OK${NC}"
        return 0
    else
        echo -e "${RED}  ✗ Broken links found${NC}"
        return 1
    fi
}

# Main execution
main() {
    echo "================================================"
    echo "  Markdown Link Checker - Claire de Binaire"
    echo "================================================"
    echo ""

    # Check prerequisites
    check_prerequisites
    echo ""

    # Determine files to check
    if [[ ${#TARGET_FILES[@]} -eq 0 ]]; then
        echo "Scanning for markdown files..."
        mapfile -t TARGET_FILES < <(find_markdown_files)
        echo -e "Found ${#TARGET_FILES[@]} markdown files\n"
    fi

    # Clear previous log
    > "$LOG_FILE"

    # Check each file
    local total_files=${#TARGET_FILES[@]}
    local failed_files=0
    local checked_files=0

    for file in "${TARGET_FILES[@]}"; do
        ((checked_files++))
        echo ""
        echo "[$checked_files/$total_files] $file"

        if ! check_file "$file"; then
            ((failed_files++))
        fi
    done

    # Summary
    echo ""
    echo "================================================"
    echo "  Summary"
    echo "================================================"
    echo -e "Total files checked: ${total_files}"
    echo -e "Files with broken links: ${failed_files}"

    if [[ $failed_files -eq 0 ]]; then
        echo -e "${GREEN}✅ All links are valid!${NC}"
        echo ""
        echo "Log saved to: $LOG_FILE"
        exit 0
    else
        echo -e "${RED}❌ Found broken links in ${failed_files} file(s)${NC}"
        echo ""
        echo "Log saved to: $LOG_FILE"
        echo "Review the log for details"

        if [[ "$CI_MODE" == true ]]; then
            exit 1
        else
            echo ""
            echo -e "${YELLOW}⚠️  Non-CI mode: Exiting with status 0${NC}"
            exit 0
        fi
    fi
}

# Trap errors
trap 'echo -e "${RED}❌ Script failed at line $LINENO${NC}"' ERR

# Run main
main
