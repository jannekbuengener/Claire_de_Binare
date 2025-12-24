# Legacy Stack Analysis

## Overview

Analysis of legacy files from quarantine directory: `Claire_de_Binare_Docs\_legacy_quarantine\files1_Tier1`

**Purpose**: Extract valuable configurations, identify improvements, document findings.

**Date**: 2025-12-24

---

## Key Findings

### 1. Paper Runner Dockerfile Found ✓

**File**: `Dockerfile_cdb_paper_runner`

**Significance**: Answers open question from FUTURE_SERVICES.md about paper runner implementation.

**Configuration**:
```dockerfile
FROM python:3.11-slim
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY service.py .
COPY email_alerter.py .

# Create logs directory
RUN mkdir -p /app/logs /app/logs/events

# Expose health endpoint port
EXPOSE 8004

# Run service
CMD ["python", "-u", "service.py"]
```

**Key Details**:
- Port: 8004 (already allocated in FUTURE_SERVICES.md)
- Main file: `service.py`
- Features: Email alerting (`email_alerter.py`)
- Log structure: `/app/logs` + `/app/logs/events`

**Action**: Can be used as template for paper_runner service integration.

---

### 2. Security Best Practices (Missing from Current Stack)

**Finding**: Legacy Dockerfiles use non-root users for security hardening.

**Example** (from `Dockerfile_signal_engine`):
```dockerfile
# Nicht-Root User
RUN useradd -m -u 1000 signaluser && \
    chown -R signaluser:signaluser /app
USER signaluser
```

**Pattern across services**:
- `signal_engine` → `signaluser`
- `risk_manager` → `riskuser`
- `execution_service` → `execuser` (assumed)
- `db_writer` → `writeruser` (assumed)

**Current Status**: 🔴 Current Dockerfiles in `services/*/Dockerfile` do NOT use non-root users.

**Recommendation**:
- Add non-root user pattern to all service Dockerfiles
- UID 1000 for consistency
- Service-specific usernames
- Priority: **High** (security hardening)

**Risk**: Running as root inside containers is a security anti-pattern.

---

### 3. Built-in Healthchecks (Better than Current Approach)

**Finding**: Legacy Dockerfiles have HEALTHCHECK instructions built-in.

**Example** (from `Dockerfile_risk_manager`):
```dockerfile
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1
```

**Benefits**:
- Healthcheck travels with image
- Consistent across environments
- No need for external healthcheck configuration
- Docker can manage container health natively

**Current Status**: 🟡 Healthchecks defined in `dev.yml` for some services, but not in Dockerfiles.

**Comparison**:

| Approach | Location | Pros | Cons |
|----------|----------|------|------|
| **Legacy** (in Dockerfile) | Image | Portable, self-contained | Requires curl in image |
| **Current** (in compose) | Stack config | Flexible, no extra deps | Not portable, config drift |

**Recommendation**:
- **Hybrid approach**: Define healthchecks in both Dockerfile AND compose
- Dockerfile: Basic health endpoint check
- Compose: Override with environment-specific checks if needed
- Priority: **Medium** (operational improvement)

---

### 4. Port Allocation Matches Current Stack

**Finding**: Legacy port assignments match current `dev.yml` allocations.

| Service | Legacy Port | Current Port | Status |
|---------|-------------|--------------|--------|
| signal_engine | 8001 | 8001 (cdb_core) | ✓ Match |
| risk_manager | 8002 | 8002 (cdb_risk) | ✓ Match |
| execution | 8003 | 8003 (cdb_execution) | ✓ Match (assumed) |
| paper_runner | 8004 | 8004 (allocated) | ✓ Match |

**Significance**: Current port allocation is consistent with legacy design. No conflicts.

---

### 5. Database Schema Available

**File**: `DATABASE_SCHEMA.sql`

**Contents**: Complete PostgreSQL schema for trading system.

**Tables**:
1. **signals** - Trading signals from signal engine
   - Fields: id, symbol, signal_type, price, confidence, timestamp, source, metadata
   - Indexes: symbol, timestamp (DESC), signal_type

2. **orders** - Validated orders from risk manager
   - (Not shown in excerpt, but exists)

3. **trades** - Executed trades
   - (Not shown in excerpt, but exists)

4. **positions** - Portfolio positions
   - (Not shown in excerpt, but exists)

5. **portfolio_snapshots** - Historical portfolio state
   - (Not shown in excerpt, but exists)

**Migration**: `002_orders_price_nullable.sql` (schema migration)

**Current Status**: 🔴 No schema documentation in current stack.

**Recommendation**:
- Copy `DATABASE_SCHEMA.sql` to `infrastructure/database/schema.sql`
- Add to DR backup procedures (already backs up data, but schema should be versioned)
- Document in DOCKER_STACK_RUNBOOK.md
- Priority: **High** (infrastructure documentation)

---

### 6. Service Code Archives

**Files**:
- `cdb_paper_runner.zip` (6 KB)
- `db_writer.zip` (5 KB)
- `execution_service.zip` (21 KB)
- `risk_manager.zip` (14 KB)
- `signal_engine.zip` (10 KB)

**Status**: Legacy implementation code archives.

**Current Status**: 🟢 Current services exist in `services/*/` directories with active code.

**Action**: No immediate action needed. Archives serve as backup/reference only.

---

### 7. WebSocket Service

**File**: `mexc_top5_ws.py` (6.8 KB)

**Status**: Legacy WebSocket implementation.

**Current Status**: 🟢 Root `Dockerfile` in current stack uses `mexc_top5_ws.py` (active).

**Comparison Needed**: Verify if quarantine version differs from active version.

**Action**: Compare versions to ensure no functionality was lost during migration.

---

### 8. Testing Infrastructure

**File**: `run-tests.ps1` (5 KB)

**Status**: Legacy test runner script.

**Current Status**: 🟢 Current `infrastructure/scripts/run-tests.ps1` exists (might be different).

**Action**: Compare scripts to see if any useful test patterns were lost.

---

### 9. System Health Check

**File**: `systemcheck.py` (15 KB)

**Status**: Legacy health monitoring script.

**Current Status**: 🟡 Current stack has `stack_doctor.ps1` but no Python systemcheck.

**Potential Value**: Python-based health checks might have different capabilities.

**Action**: Review `systemcheck.py` to see if it offers functionality not in `stack_doctor.ps1`.

---

## Recommendations by Priority

### High Priority

1. **Add Non-Root Users to Dockerfiles**
   - Security hardening
   - Follow legacy pattern: create service-specific users (UID 1000)
   - Apply to all service Dockerfiles

2. **Document Database Schema**
   - Copy `DATABASE_SCHEMA.sql` to `infrastructure/database/`
   - Add to Git for version control
   - Reference in DR procedures

3. **Create Paper Runner Service**
   - Use `Dockerfile_cdb_paper_runner` as template
   - Port 8004 already allocated
   - Implementation exists in `services/execution/paper_trading.py`

### Medium Priority

4. **Add Built-in Healthchecks to Dockerfiles**
   - Install curl in all service images
   - Add HEALTHCHECK instructions
   - Keep compose overrides for flexibility

5. **Compare WebSocket Implementations**
   - Verify `mexc_top5_ws.py` versions match
   - Ensure no functionality lost

6. **Review Legacy Test Infrastructure**
   - Compare `run-tests.ps1` versions
   - Extract any useful test patterns

### Low Priority

7. **Analyze systemcheck.py**
   - Identify unique capabilities vs. `stack_doctor.ps1`
   - Consider Python-based health monitoring

8. **Archive Legacy Code**
   - Service ZIPs are backups only
   - Keep in quarantine for reference
   - No immediate action needed

---

## Integration Actions

### Immediate (This Session)

- [x] Analyze legacy files
- [x] Document findings (this file)
- [x] Update FUTURE_SERVICES.md with paper_runner Dockerfile details
- [ ] Copy DATABASE_SCHEMA.sql to infrastructure/database/

### Next Session

- [ ] Add non-root users to all service Dockerfiles
- [ ] Add HEALTHCHECK instructions to Dockerfiles
- [ ] Implement paper_runner service using legacy Dockerfile
- [ ] Compare WebSocket implementations
- [ ] Compare test scripts

---

## Files Inventory

### Dockerfiles (5)
- `Dockerfile` - Generic/base (897 bytes)
- `Dockerfile_cdb_paper_runner` - Paper trading runner (355 bytes)
- `Dockerfile_db_writer` - Database writer (531 bytes)
- `Dockerfile_execution_service` - Order execution (694 bytes)
- `Dockerfile_risk_manager` - Risk management (474 bytes)
- `Dockerfile_signal_engine` - Signal processing (608 bytes)

### Code Archives (5)
- `cdb_paper_runner.zip` (6 KB)
- `db_writer.zip` (5 KB)
- `execution_service.zip` (21 KB)
- `risk_manager.zip` (14 KB)
- `signal_engine.zip` (10 KB)

### Database (2)
- `DATABASE_SCHEMA.sql` (11 KB)
- `002_orders_price_nullable.sql` (1 KB) - Migration

### Application (4)
- `mexc_top5_ws.py` (6.8 KB) - WebSocket service
- `requirements.txt` (405 bytes) - Python dependencies
- `systemcheck.py` (15 KB) - Health monitoring
- `run-tests.ps1` (5 KB) - Test runner

**Total**: 16 files, ~93 KB

---

## Security Implications

### Current Risk: Running as Root

All current service Dockerfiles run containers as root by default. This violates container security best practices.

**Attack Surface**:
- Container escape → root on host (if kernel vulnerability)
- Compromised service → full container access
- File permission issues with bind mounts

**Legacy Solution**: Non-root users (UID 1000) for each service.

**Mitigation Required**: Add user creation to all Dockerfiles.

---

## See Also

- `FUTURE_SERVICES.md` - Service integration roadmap
- `infrastructure/compose/COMPOSE_LAYERS.md` - Current stack architecture
- `DOCKER_STACK_RUNBOOK.md` - Operational procedures
- `services/*/Dockerfile` - Current service Dockerfiles
