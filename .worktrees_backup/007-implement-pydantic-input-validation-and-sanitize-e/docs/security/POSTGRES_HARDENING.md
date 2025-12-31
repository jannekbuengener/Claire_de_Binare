# PostgreSQL RBAC & Hardening Guide

**Issue:** #106
**Date:** 2025-12-28
**Status:** ✅ Documented (Implementation pending for production)

---

## Current State Analysis

### ✅ Already Implemented

| Feature | Status | Location |
|---------|--------|----------|
| SSL/TLS Encryption | ✅ Done | `infrastructure/compose/tls.yml` |
| Certificate-based Auth | ✅ Ready | `POSTGRES_SSLMODE=verify-ca` |
| Non-default User | ✅ Done | `claire_user` (not postgres) |
| Health Checks | ✅ Done | All compose files |
| Network Isolation | ✅ Done | Docker network `cdb_network` |

### ⏳ Pending Implementation

| Feature | Status | Priority |
|---------|--------|----------|
| Role-based Access Control (RBAC) | ❌ Pending | HIGH |
| Least-privilege Principle | ❌ Pending | HIGH |
| Connection Limits | ❌ Pending | MEDIUM |
| SSL Certificate Rotation | ❌ Pending | MEDIUM |

---

## 1. Role-Based Access Control (RBAC)

### Current Problem
All services use `claire_user` with full database access.

### Recommended Roles

```sql
-- Create roles for different access levels
CREATE ROLE cdb_readonly NOLOGIN;
CREATE ROLE cdb_readwrite NOLOGIN;
CREATE ROLE cdb_admin NOLOGIN;

-- Grant permissions to roles
GRANT SELECT ON ALL TABLES IN SCHEMA public TO cdb_readonly;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO cdb_readwrite;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cdb_admin;

-- Service-specific users
CREATE USER cdb_market PASSWORD 'xxx' IN ROLE cdb_readonly;       -- Read market data
CREATE USER cdb_signal PASSWORD 'xxx' IN ROLE cdb_readwrite;      -- Read/write signals
CREATE USER cdb_execution PASSWORD 'xxx' IN ROLE cdb_readwrite;   -- Read/write trades
CREATE USER cdb_risk PASSWORD 'xxx' IN ROLE cdb_readwrite;        -- Read/write risk data
CREATE USER cdb_db_writer PASSWORD 'xxx' IN ROLE cdb_readwrite;   -- Write all data
CREATE USER claire_admin PASSWORD 'xxx' IN ROLE cdb_admin;        -- Admin operations
```

### Service-Role Mapping

| Service | User | Role | Access |
|---------|------|------|--------|
| cdb_market | cdb_market | cdb_readonly | SELECT on market_data |
| cdb_signal | cdb_signal | cdb_readwrite | R/W on signals |
| cdb_execution | cdb_execution | cdb_readwrite | R/W on orders, trades |
| cdb_risk | cdb_risk | cdb_readwrite | R/W on risk tables |
| cdb_db_writer | cdb_db_writer | cdb_readwrite | R/W all tables |
| Admin CLI | claire_admin | cdb_admin | Full access |

---

## 2. Least-Privilege Principle

### Table-Level Permissions

```sql
-- Market service: Only read market data
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM cdb_market;
GRANT SELECT ON market_data, candles, tickers TO cdb_market;

-- Signal service: Read market data, write signals
GRANT SELECT ON market_data, candles TO cdb_signal;
GRANT SELECT, INSERT, UPDATE ON signals TO cdb_signal;

-- Execution service: Read signals, write orders/trades
GRANT SELECT ON signals TO cdb_execution;
GRANT SELECT, INSERT, UPDATE ON orders, trades TO cdb_execution;

-- Risk service: Read trades, write risk metrics
GRANT SELECT ON trades, orders TO cdb_risk;
GRANT SELECT, INSERT, UPDATE ON risk_metrics, portfolio_snapshots TO cdb_risk;

-- DB Writer: Write all operational tables
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO cdb_db_writer;
```

### Row-Level Security (Future)

For multi-tenant scenarios, consider PostgreSQL Row-Level Security:

```sql
-- Example: Each service sees only its own data
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY service_isolation ON audit_log
    USING (service_name = current_user);
```

---

## 3. Connection Limits

### PostgreSQL Configuration (`postgresql.conf`)

```conf
# Maximum connections (adjust based on service count)
max_connections = 100

# Per-user connection limits
# Set via ALTER USER

# Connection timeouts
tcp_keepalives_idle = 60
tcp_keepalives_interval = 10
tcp_keepalives_count = 3
```

### Per-User Limits

```sql
-- Limit connections per service user
ALTER USER cdb_market CONNECTION LIMIT 5;
ALTER USER cdb_signal CONNECTION LIMIT 10;
ALTER USER cdb_execution CONNECTION LIMIT 10;
ALTER USER cdb_risk CONNECTION LIMIT 5;
ALTER USER cdb_db_writer CONNECTION LIMIT 10;
ALTER USER claire_admin CONNECTION LIMIT 2;
```

### Docker Implementation

Add to `docker-compose.yml`:

```yaml
cdb_postgres:
  command:
    - "postgres"
    - "-c"
    - "max_connections=100"
    - "-c"
    - "log_connections=on"
    - "-c"
    - "log_disconnections=on"
```

---

## 4. SSL Certificate Rotation

### Current Setup

Certificates are stored in `.cdb_local/tls/`:
- `postgres.crt` - Server certificate
- `postgres.key` - Server private key
- `ca.crt` - CA certificate

### Rotation Procedure

```bash
#!/bin/bash
# Certificate rotation script (run monthly)

# 1. Generate new certificates
openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout postgres.key.new \
  -out postgres.crt.new \
  -subj "/CN=cdb_postgres"

# 2. Stop services gracefully
docker compose down

# 3. Backup old certificates
mv postgres.key postgres.key.backup
mv postgres.crt postgres.crt.backup

# 4. Install new certificates
mv postgres.key.new postgres.key
mv postgres.crt.new postgres.crt
chmod 600 postgres.key

# 5. Restart services
docker compose up -d

# 6. Verify connection
psql "sslmode=verify-ca sslrootcert=ca.crt" -c "SELECT 1"
```

### Automation

Add to crontab for monthly rotation:

```cron
0 3 1 * * /path/to/rotate_postgres_certs.sh >> /var/log/cert-rotation.log 2>&1
```

---

## 5. Additional Hardening

### Password Policy

```sql
-- Enforce password complexity (via extensions)
CREATE EXTENSION IF NOT EXISTS passwordcheck;

-- Set password expiry
ALTER USER cdb_execution VALID UNTIL '2026-01-01';
```

### Audit Logging

```conf
# postgresql.conf
log_statement = 'ddl'           # Log DDL statements
log_connections = on            # Log connections
log_disconnections = on         # Log disconnections
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
```

### Network Security

Already implemented via Docker:
- ✅ Internal network (`cdb_network`)
- ✅ No direct external exposure (ports bound to 127.0.0.1)
- ✅ Service-to-service communication only

---

## Implementation Checklist

### Phase 1: RBAC (Required for Production)
- [ ] Create SQL migration script for roles/users
- [ ] Update `.env.example` with per-service credentials
- [ ] Update docker-compose with service-specific users
- [ ] Test each service with limited permissions
- [ ] Document rollback procedure

### Phase 2: Connection Limits
- [ ] Add PostgreSQL config to docker-compose
- [ ] Set per-user connection limits
- [ ] Add monitoring for connection pool usage

### Phase 3: Certificate Rotation
- [ ] Create rotation script
- [ ] Schedule monthly rotation
- [ ] Add rotation to runbook

### Phase 4: Audit & Monitoring
- [ ] Enable PostgreSQL logging
- [ ] Forward logs to Loki
- [ ] Create Grafana dashboard for DB metrics

---

## Verification Commands

```bash
# Check current users
docker exec cdb_postgres psql -U claire_user -d claire_de_binare \
  -c "SELECT usename, usecreatedb, usesuper FROM pg_user;"

# Check SSL status
docker exec cdb_postgres psql -U claire_user -d claire_de_binare \
  -c "SHOW ssl;"

# Check connection limits
docker exec cdb_postgres psql -U claire_user -d claire_de_binare \
  -c "SELECT usename, useconnlimit FROM pg_user;"

# Check active connections
docker exec cdb_postgres psql -U claire_user -d claire_de_binare \
  -c "SELECT usename, count(*) FROM pg_stat_activity GROUP BY usename;"
```

---

## References

- [PostgreSQL RBAC Documentation](https://www.postgresql.org/docs/current/sql-grant.html)
- [PostgreSQL SSL](https://www.postgresql.org/docs/current/ssl-tcp.html)
- [Docker PostgreSQL Image](https://hub.docker.com/_/postgres)

---

**Next Review:** Before M9 Production
**Owner:** Security Team
**Issue:** #106
