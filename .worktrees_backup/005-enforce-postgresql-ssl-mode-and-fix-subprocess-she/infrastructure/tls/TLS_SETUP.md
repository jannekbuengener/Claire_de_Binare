# TLS/SSL Setup Guide

**Issue:** #103
**Status:** Implemented
**Last Updated:** 2025-12-28

---

## Overview

This guide documents the TLS/SSL implementation for Claire de Binare infrastructure.

### What's Protected

| Component | TLS Status | Port | Notes |
|-----------|------------|------|-------|
| Redis | ✅ Enabled | 6379 | TLS-only mode (port 0 disabled) |
| PostgreSQL | ✅ Enabled | 5432 | SSL required for network connections |
| Service-to-Service | ✅ Enabled | - | Via Redis/PostgreSQL TLS |

---

## Quick Start

### 1. Generate Certificates

```bash
# Navigate to infrastructure directory
cd infrastructure/tls

# Generate self-signed certificates
chmod +x generate_certs.sh
./generate_certs.sh ../../../.cdb_local/tls
```

This creates:
- `ca.crt` / `ca.key` — Certificate Authority
- `redis.crt` / `redis.key` — Redis server certificate
- `postgres.crt` / `postgres.key` — PostgreSQL server certificate
- `client.crt` / `client.key` — Client certificate for services
- `redis.dh` — Diffie-Hellman parameters

### 2. Start Stack with TLS

```powershell
# Windows PowerShell
.\infrastructure\scripts\stack_up.ps1 -TLS

# With all production overlays
.\infrastructure\scripts\stack_up.ps1 -Profile prod -TLS -NetworkIsolation
```

### 3. Verify TLS

```bash
# Check Redis TLS
docker exec cdb_redis redis-cli --tls \
    --cert /tls/client.crt \
    --key /tls/client.key \
    --cacert /tls/ca.crt \
    -a "$REDIS_PASSWORD" \
    INFO server | grep tcp_port

# Check PostgreSQL SSL
docker exec cdb_postgres psql -U claire_user -d claire_de_binare \
    -c "SHOW ssl;"
```

---

## Architecture

### Certificate Chain

```
CA (ca.crt)
├── Redis Server (redis.crt)
├── PostgreSQL Server (postgres.crt)
└── Client (client.crt) ← Used by all services
```

### Compose Overlay

The `tls.yml` overlay adds:

1. **Redis Configuration**
   - `--tls-port 6379` (TLS on main port)
   - `--port 0` (disable non-TLS)
   - Certificate mounting

2. **PostgreSQL Configuration**
   - SSL init script
   - `hostssl` in pg_hba.conf
   - Certificate mounting

3. **Service Environment**
   - `REDIS_TLS=true`
   - `POSTGRES_SSLMODE=verify-ca`
   - Certificate volume mounts

---

## Configuration Reference

### Environment Variables (Services)

```bash
# Redis TLS
REDIS_TLS=true
REDIS_CA_CERT=/tls/ca.crt
REDIS_CERT=/tls/client.crt      # Optional (mTLS)
REDIS_KEY=/tls/client.key       # Optional (mTLS)

# PostgreSQL SSL
POSTGRES_SSLMODE=verify-ca       # or verify-full
POSTGRES_SSLROOTCERT=/tls/ca.crt
POSTGRES_SSLCERT=/tls/client.crt # Optional
POSTGRES_SSLKEY=/tls/client.key  # Optional
```

### SSL Modes (PostgreSQL)

| Mode | Description | Recommended |
|------|-------------|-------------|
| `disable` | No SSL | ❌ Never |
| `allow` | Try SSL, fallback | ❌ No |
| `prefer` | Try SSL, fallback | ⚠️ Dev only |
| `require` | Require SSL, no verification | ⚠️ Internal only |
| `verify-ca` | Require SSL + CA verification | ✅ Production |
| `verify-full` | Above + hostname verification | ✅ External |

---

## Client Code Integration

### Redis (Python)

```python
from core.utils.redis_client import create_redis_client

# Automatic TLS based on REDIS_TLS env var
client = create_redis_client()

# Explicit TLS
client = create_redis_client(
    host="cdb_redis",
    use_tls=True,
    ssl_ca_certs="/tls/ca.crt"
)
```

### PostgreSQL (Python)

```python
from core.utils.postgres_client import create_postgres_connection

# Automatic SSL based on POSTGRES_SSLMODE env var
conn = create_postgres_connection()

# Explicit SSL
conn = create_postgres_connection(
    host="cdb_postgres",
    sslmode="verify-ca",
    sslrootcert="/tls/ca.crt"
)
```

---

## Certificate Management

### Development (Self-Signed)

- Valid for 365 days
- Regenerate with `generate_certs.sh`
- Stored in `../.cdb_local/tls/`

### Production (Recommended)

1. **Let's Encrypt** — For external-facing services
2. **HashiCorp Vault** — For internal PKI
3. **AWS ACM / GCP Certificate Manager** — Cloud environments

### Rotation

```bash
# 1. Generate new certificates
./generate_certs.sh ../../../.cdb_local/tls_new

# 2. Stop services
docker compose down

# 3. Replace certificates
mv ../.cdb_local/tls ../.cdb_local/tls_backup
mv ../.cdb_local/tls_new ../.cdb_local/tls

# 4. Restart with TLS
.\infrastructure\scripts\stack_up.ps1 -TLS
```

---

## Troubleshooting

### Redis Connection Refused

```
Error: Connection refused (TLS handshake failed)
```

**Fix:** Ensure `REDIS_TLS=true` is set and CA cert path is correct.

### PostgreSQL SSL Required

```
FATAL: no pg_hba.conf entry for host ... SSL off
```

**Fix:** Use `sslmode=require` or higher in connection string.

### Certificate Expired

```
Error: certificate has expired
```

**Fix:** Regenerate certificates with `generate_certs.sh`.

---

## Security Notes

1. **Self-signed certs are for development only**
   - Use proper CA for production
   - Consider automated rotation

2. **Protect private keys**
   - Keys have 600 permissions
   - Never commit to git
   - Use Docker secrets in production

3. **Verify connections**
   - Use `verify-ca` or `verify-full` for PostgreSQL
   - Enable mTLS for mutual authentication

---

## Files Reference

```
infrastructure/
├── tls/
│   ├── generate_certs.sh      # Certificate generator
│   ├── postgres_ssl_init.sh   # PostgreSQL SSL init script
│   └── TLS_SETUP.md           # This documentation
└── compose/
    └── tls.yml                # TLS overlay for docker-compose

../.cdb_local/tls/             # Generated certificates (gitignored)
    ├── ca.crt / ca.key
    ├── redis.crt / redis.key / redis.dh
    ├── postgres.crt / postgres.key
    └── client.crt / client.key

core/utils/
    ├── redis_client.py        # TLS-aware Redis client factory
    └── postgres_client.py     # SSL-aware PostgreSQL client factory
```

---

## See Also

- [DOCKER_STACK_RUNBOOK.md](../../DOCKER_STACK_RUNBOOK.md) — Stack operations
- [COMPOSE_LAYERS.md](../compose/COMPOSE_LAYERS.md) — Compose overlay architecture
- [LEGACY_FILES.md](../../LEGACY_FILES.md) — Migration from legacy setup
