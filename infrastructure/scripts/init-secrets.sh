#!/usr/bin/env bash
#
# Initialize secrets for Claire de Binare development environment (Linux/Mac)
#
# Creates the secrets directory at ~/Documents/.secrets/.cdb and generates
# secure random passwords for all required secrets.
#
# This script should be run ONCE when setting up a new development environment.
#
# Usage:
#   ./init-secrets.sh          # Create secrets (skip existing)
#   ./init-secrets.sh --force  # Overwrite existing secrets

set -euo pipefail

FORCE=false
if [[ "${1:-}" == "--force" ]]; then
    FORCE=true
fi

# Secrets directory path
SECRETS_PATH="${HOME}/Documents/.secrets/.cdb"

echo ""
echo "=== Claire de Binare - Secrets Initialization ==="
echo "Target: $SECRETS_PATH"

# Create directory if it doesn't exist
if [[ ! -d "$SECRETS_PATH" ]]; then
    mkdir -p "$SECRETS_PATH"
    echo "  [OK] Created secrets directory"
fi

# List of secrets to generate
secrets=(
    "REDIS_PASSWORD"
    "POSTGRES_PASSWORD"
    "GRAFANA_PASSWORD"
)

for secret in "${secrets[@]}"; do
    secret_path="${SECRETS_PATH}/${secret}"

    if [[ -f "$secret_path" ]] && [[ "$FORCE" == "false" ]]; then
        echo "  [SKIP] $secret exists (use --force to overwrite)"
        continue
    fi

    # Generate secure random password (24 bytes base64 = 32 characters)
    # Use openssl for cross-platform compatibility (Linux/Mac)
    password=$(openssl rand -base64 24 | tr -d '\n')

    # Write to file (no newline - critical for Docker secrets)
    printf "%s" "$password" > "$secret_path"

    echo "  [OK] Generated $secret"
done

# Set restrictive permissions (owner read/write only)
chmod 700 "$SECRETS_PATH"
chmod 600 "$SECRETS_PATH"/*

echo ""
echo "=== Secrets initialized successfully ==="
cat <<EOF

Next steps:
1. Copy environment template: cp .env.example .env
2. Update SECRETS_PATH in .env if needed (default: ~/Documents/.secrets/.cdb)
3. Run the stack: docker compose -f infrastructure/compose/dev.yml up -d
4. Access Grafana: http://localhost:3000 (admin / <GRAFANA_PASSWORD>)

To view a secret:
  cat $SECRETS_PATH/REDIS_PASSWORD

EOF
