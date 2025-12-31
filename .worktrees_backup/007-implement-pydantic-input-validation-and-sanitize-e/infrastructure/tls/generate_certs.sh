#!/bin/bash
# TLS Certificate Generator for Claire de Binare
# Issue #103: TLS/SSL Implementation
#
# Generates self-signed certificates for:
# - CA (Certificate Authority)
# - Redis Server
# - PostgreSQL Server
# - Client certificates for services
#
# Usage: ./generate_certs.sh [output_dir]
# Default output: ./certs/

set -euo pipefail

OUTPUT_DIR="${1:-./certs}"
DAYS_VALID=365
KEY_SIZE=4096
# Use -subj with proper escaping for Git Bash on Windows
# MSYS_NO_PATHCONV prevents path conversion
export MSYS_NO_PATHCONV=1
CA_SUBJECT="/C=DE/ST=Berlin/L=Berlin/O=ClairedeBinare/OU=Infrastructure/CN=CDB-CA"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Create output directory
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

log_info "Generating TLS certificates in: $(pwd)"

# ============================================
# 1. Generate CA (Certificate Authority)
# ============================================
log_info "Generating CA private key..."
openssl genrsa -out ca.key $KEY_SIZE 2>/dev/null

log_info "Generating CA certificate..."
openssl req -x509 -new -nodes \
    -key ca.key \
    -sha256 \
    -days $DAYS_VALID \
    -out ca.crt \
    -subj "$CA_SUBJECT"

# ============================================
# 2. Generate Redis Server Certificate
# ============================================
log_info "Generating Redis server certificate..."

# Redis private key
openssl genrsa -out redis.key $KEY_SIZE 2>/dev/null

# Redis CSR config
cat > redis.cnf << EOF
[req]
default_bits = $KEY_SIZE
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = req_ext

[dn]
C = DE
ST = Berlin
L = Berlin
O = ClairedeBinare
OU = Redis
CN = cdb_redis

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = cdb_redis
DNS.2 = localhost
DNS.3 = redis
IP.1 = 127.0.0.1
EOF

# Redis CSR
openssl req -new -key redis.key -out redis.csr -config redis.cnf

# Sign Redis certificate with CA
openssl x509 -req -in redis.csr \
    -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out redis.crt \
    -days $DAYS_VALID \
    -sha256 \
    -extensions req_ext \
    -extfile redis.cnf

# Generate DH parameters for Redis
log_info "Generating DH parameters for Redis (this may take a moment)..."
openssl dhparam -out redis.dh 2048 2>/dev/null

# ============================================
# 3. Generate PostgreSQL Server Certificate
# ============================================
log_info "Generating PostgreSQL server certificate..."

# PostgreSQL private key
openssl genrsa -out postgres.key $KEY_SIZE 2>/dev/null

# PostgreSQL CSR config
cat > postgres.cnf << EOF
[req]
default_bits = $KEY_SIZE
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = req_ext

[dn]
C = DE
ST = Berlin
L = Berlin
O = ClairedeBinare
OU = PostgreSQL
CN = cdb_postgres

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = cdb_postgres
DNS.2 = localhost
DNS.3 = postgres
IP.1 = 127.0.0.1
EOF

# PostgreSQL CSR
openssl req -new -key postgres.key -out postgres.csr -config postgres.cnf

# Sign PostgreSQL certificate with CA
openssl x509 -req -in postgres.csr \
    -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out postgres.crt \
    -days $DAYS_VALID \
    -sha256 \
    -extensions req_ext \
    -extfile postgres.cnf

# ============================================
# 4. Generate Client Certificate (for services)
# ============================================
log_info "Generating client certificate for services..."

# Client private key
openssl genrsa -out client.key $KEY_SIZE 2>/dev/null

# Client CSR config
cat > client.cnf << EOF
[req]
default_bits = $KEY_SIZE
prompt = no
default_md = sha256
distinguished_name = dn

[dn]
C = DE
ST = Berlin
L = Berlin
O = ClairedeBinare
OU = Services
CN = cdb-client
EOF

# Client CSR
openssl req -new -key client.key -out client.csr -config client.cnf

# Sign client certificate with CA
openssl x509 -req -in client.csr \
    -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out client.crt \
    -days $DAYS_VALID \
    -sha256

# ============================================
# 5. Set Permissions
# ============================================
log_info "Setting file permissions..."
chmod 600 *.key
chmod 644 *.crt *.dh 2>/dev/null || true

# Cleanup CSR and CNF files
rm -f *.csr *.cnf *.srl

# ============================================
# 6. Verify Certificates
# ============================================
log_info "Verifying certificates..."

echo ""
echo "=== CA Certificate ==="
openssl x509 -in ca.crt -noout -subject -dates

echo ""
echo "=== Redis Certificate ==="
openssl x509 -in redis.crt -noout -subject -dates
openssl verify -CAfile ca.crt redis.crt

echo ""
echo "=== PostgreSQL Certificate ==="
openssl x509 -in postgres.crt -noout -subject -dates
openssl verify -CAfile ca.crt postgres.crt

echo ""
echo "=== Client Certificate ==="
openssl x509 -in client.crt -noout -subject -dates
openssl verify -CAfile ca.crt client.crt

# ============================================
# Summary
# ============================================
echo ""
log_info "Certificate generation complete!"
echo ""
echo "Generated files:"
ls -la
echo ""
log_warn "IMPORTANT: These are self-signed certificates for development/testing."
log_warn "For production, use certificates from a trusted CA (e.g., Let's Encrypt)."
echo ""
log_info "Next steps:"
echo "  1. Mount certs into containers via docker-compose"
echo "  2. Configure Redis with --tls-* options"
echo "  3. Configure PostgreSQL with ssl = on"
echo "  4. Update service connection strings to use TLS"
