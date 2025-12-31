#!/bin/bash
# PostgreSQL SSL Initialization Script
# Issue #103: TLS/SSL Implementation
#
# This script runs as part of PostgreSQL container initialization
# to configure SSL certificates and enable encrypted connections.

set -e

echo "Configuring PostgreSQL SSL..."

# Copy certificates to PostgreSQL data directory with correct permissions
cp /var/lib/postgresql/server.crt /var/lib/postgresql/data/server.crt
cp /var/lib/postgresql/server.key /var/lib/postgresql/data/server.key
cp /var/lib/postgresql/root.crt /var/lib/postgresql/data/root.crt

# Set correct ownership and permissions
chown postgres:postgres /var/lib/postgresql/data/server.crt
chown postgres:postgres /var/lib/postgresql/data/server.key
chown postgres:postgres /var/lib/postgresql/data/root.crt

chmod 600 /var/lib/postgresql/data/server.key
chmod 644 /var/lib/postgresql/data/server.crt
chmod 644 /var/lib/postgresql/data/root.crt

# Append SSL configuration to postgresql.conf
cat >> /var/lib/postgresql/data/postgresql.conf << EOF

# SSL Configuration (Issue #103)
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
ssl_ca_file = 'root.crt'
EOF

# Update pg_hba.conf to require SSL for remote connections
# Allow local connections without SSL, require SSL for network connections
cat > /var/lib/postgresql/data/pg_hba.conf << EOF
# PostgreSQL Client Authentication Configuration
# Issue #103: TLS/SSL Implementation

# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Local connections (Unix domain socket) - no SSL needed
local   all             all                                     trust

# IPv4 local connections - require SSL
hostssl all             all             0.0.0.0/0               scram-sha-256

# IPv6 local connections - require SSL
hostssl all             all             ::/0                    scram-sha-256

# Replication connections - require SSL
hostssl replication     all             0.0.0.0/0               scram-sha-256
hostssl replication     all             ::/0                    scram-sha-256
EOF

echo "PostgreSQL SSL configuration complete."
echo "  - SSL enabled: yes"
echo "  - Certificate: server.crt"
echo "  - Key: server.key"
echo "  - CA: root.crt"
echo "  - Remote connections: SSL required"
