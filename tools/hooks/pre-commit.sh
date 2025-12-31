#!/bin/sh
# Pre-commit hook: root baseline enforcement + contract example validation

set -e

echo "Checking Working Repo root baseline..."

if command -v pwsh >/dev/null 2>&1; then
    pwsh -File "tools/enforce-root-baseline.ps1"
elif command -v powershell >/dev/null 2>&1; then
    powershell -File "tools/enforce-root-baseline.ps1"
else
    echo "PowerShell not found - cannot validate root baseline"
    exit 1
fi

if git diff --cached --name-only | grep -q "^docs/contracts/"; then
    echo "Validating contract examples..."

    if command -v python3 >/dev/null 2>&1; then
        PY=python3
    elif command -v python >/dev/null 2>&1; then
        PY=python
    else
        echo "Python not found - cannot validate contracts"
        exit 1
    fi

    for file in docs/contracts/examples/market_data_*.json; do
        if [ -f "$file" ]; then
            echo "  Checking $file..."
            "$PY" tools/validate_contract.py market_data --file "$file"
        fi
    done

    for file in docs/contracts/examples/signal_*.json; do
        if [ -f "$file" ]; then
            echo "  Checking $file..."
            "$PY" tools/validate_contract.py signal --file "$file"
        fi
    done

    echo "All contract examples valid"
fi

exit 0
